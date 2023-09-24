import json
import os

import uvicorn
from bson import json_util
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.encoders import jsonable_encoder
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from langchain.callbacks import get_openai_callback
from langchain.callbacks.tracers import ConsoleCallbackHandler
from langchain.chains import RetrievalQAWithSourcesChain
from langchain.chat_models import ChatOpenAI
from langchain.embeddings.openai import OpenAIEmbeddings
from langchain.prompts import PromptTemplate
from pydantic import BaseModel

from mongo_repository import MongoRepository


class PromptRequest(BaseModel):
    prompt: str
    temperature: float = 0.2


app = FastAPI()

origins = [
    "http://localhost",
    "http://localhost:5173",
    "http://localhost:5174",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

load_dotenv(verbose=True)


def get_qa_chain(temperature: float):
    OpenAIEmbeddings(
        openai_api_key=os.getenv("OPENAI_API_KEY"))
    instance = MongoRepository().vector_store

    tech_template = """You are the GDS Bot your goals is to provide answers and summaries to the provided questions based only on the context that has been provided. Please give as much detail and information as possible. I would rather you were verbose than too brief. In scenarios when listing a number of different examples please, use a number list and provide as much details as possible for each example. If the context does not answer the question then just respond and say the context does not provide enough information to answer the question.
    
    {summaries}
    
    Q: {question}
    A: """
    PROMPT = PromptTemplate(
        template=tech_template, input_variables=["summaries", "question"]
    )

    return RetrievalQAWithSourcesChain.from_chain_type(llm=ChatOpenAI(
        model_name=os.getenv("OPENAI_MODEL", "gpt-3.5-turbo-16k"),
        temperature=temperature,
        openai_api_key=os.getenv("OPENAI_API_KEY"),
        verbose=True
    ),
        chain_type="stuff",
        retriever=instance.as_retriever(
            search_kwargs={"k": 4}),
        chain_type_kwargs={"prompt": PROMPT},
        return_source_documents=True,
        verbose=True,
    )


@app.post('/api/completions')
def my_api(request: PromptRequest):
    query: str = request.prompt
    # process the input string here
    qa = get_qa_chain(request.temperature)
    with get_openai_callback() as cb:
        output = qa({"question": query},
                    callbacks=[ConsoleCallbackHandler()])

    print(cb)

    all_source_documents = []

    for source_document in output['source_documents']:
        all_source_documents.append({
            '_id': str(source_document.metadata['_id']),
            "page_content": source_document.page_content,
            "metadata": {
                "source": source_document.metadata['source'],
                "sitemap": source_document.metadata['sitemap'],
                "page_type": source_document.metadata['page_type'],
                "loc": source_document.metadata['loc'],
                "lastmod": source_document.metadata['lastmod'],
                "priority": source_document.metadata['priority']
            }
        }
        )

    output['source_documents'] = all_source_documents
    output['stats'] = {
        "total_tokens": cb.total_tokens,
        "prompt_tokens": cb.prompt_tokens,
        "completion_tokens": cb.completion_tokens,
        "successful_requests": cb.successful_requests,
        "total_cost": cb.total_cost
    }

    return JSONResponse(
        content=jsonable_encoder(json.loads(json_util.dumps(output))))


if __name__ == '__main__':
    uvicorn.run(app, port=5001)
