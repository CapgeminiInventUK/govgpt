import os

from dotenv import load_dotenv, find_dotenv
from langchain.embeddings import OpenAIEmbeddings
from langchain.vectorstores import MongoDBAtlasVectorSearch
from pymongo import MongoClient

load_dotenv(verbose=True, dotenv_path=find_dotenv())


class MongoRepository:

    def __init__(self):
        openai_embeddings = OpenAIEmbeddings(openai_api_key=os.getenv("OPENAI_API_KEY"))
        client = MongoClient(os.getenv("MONGODB_ATLAS_CLUSTER_URI"))

        db_name = os.getenv("MONGODB_DB_NAME", "govgpt")
        embeddings_collection_name = os.getenv(
            "MONGODB_COLLECTION_NAME", "embeddings")

        self.embeddings_collection = client[db_name][embeddings_collection_name]
        self.embeddings_key = os.getenv(
            "MONGODB_FIELD_NAME",  "embedding")
        self.embeddings_index_name = os.getenv(
            "MONGODB_INDEX_NAME", "vector_search")

        self.vector_store = MongoDBAtlasVectorSearch(
            collection=self.embeddings_collection,
            index_name=self.embeddings_index_name,
            embedding=openai_embeddings,
            embedding_key=self.embeddings_key,
        )
