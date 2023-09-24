import os
import re
import shutil
from datetime import datetime
from typing import Any

from bs4 import BeautifulSoup
from langchain.document_loaders import SitemapLoader
from langchain.schema import Document
from langchain.text_splitter import RecursiveCharacterTextSplitter
from unidecode import unidecode

from mongo_repository import MongoRepository
from tokens_utils import TokenUtils

file_being_processed = None


def meta_function(meta: dict, _content: Any) -> dict:
    print(meta["loc"])
    if isinstance(_content, BeautifulSoup):
        main = _content.find('main')

        is_main_not_none = main is not None
        classes_in_main = main.get('class', []) if is_main_not_none else []
        is_class_in_main = len(classes_in_main) > 0

        if is_main_not_none and is_class_in_main:
            print('Main class: ' + str(classes_in_main))
            metadata = {"sitemap": file_being_processed,
                        "page_type": classes_in_main[0],
                        "source": meta["loc"],
                        **meta}
            return metadata

        print('No main class found')
        metadata = {"sitemap": file_being_processed,
                    "source": meta["loc"],
                    **meta}
        return metadata
    else:
        print('Content is not a BeautifulSoup object')
        metadata = {"sitemap": file_being_processed,
                    "source": meta["loc"],
                    **meta}
        return metadata


def clean_string(text: str):
    """
    This function takes in a string and performs a series of text cleaning operations.

    Args:
        text (str): The text to be cleaned. This is expected to be a string.

    Returns:
        cleaned_text (str): The cleaned text after all the cleaning operations
        have been performed.
    """
    # Replacement of newline characters:
    text = text.replace("\n", " ")

    # Stripping and reducing multiple spaces to single:
    cleaned_text = re.sub(r"\s+", " ", text.strip())

    # Removing backslashes:
    cleaned_text = cleaned_text.replace("\\", "")

    # Replacing hash characters:
    cleaned_text = cleaned_text.replace("#", " ")

    # Eliminating consecutive non-alphanumeric characters:
    # This regex identifies consecutive non-alphanumeric characters (i.e., not
    # a word character [a-zA-Z0-9_] and not a whitespace) in the string
    # and replaces each group of such characters with a single occurrence of
    # that character.
    # For example, "!!! hello !!!" would become "! hello !".
    cleaned_text = re.sub(r"([^\w\s])\1*", r"\1", cleaned_text)

    return cleaned_text


def remove_elements(html: BeautifulSoup):
    for i in html.find_all('img'):
        i.decompose()

    for i in html.find_all('nav'):
        i.decompose()

    for i in html.find_all('header'):
        i.decompose()

    # Delete any elements with class "dont-print"
    for i in html.find_all(class_="dont-print"):
        i.decompose()

    for i in html.find_all(class_="meta-data"):
        i.decompose()

    for i in html.find_all(class_="metadata-logo-wrapper"):
        i.decompose()

    for i in html.find_all(class_="gem-c-related-navigation"):
        i.decompose()

    for i in html.find_all('button'):
        if 'Get emails about this page' in i.get_text():
            i.decompose()
        if 'Print this page' in i.get_text():
            i.decompose()

    return html


def sanitise_html(content: BeautifulSoup) -> str:
    print('Removing nav and header elements')
    if 'Sorry, there have been too many attempts to access this page' in content.get_text():
        print('Too many requests, skipping')
        return ''
    else:
        ## TODO Should it skip withdrawn pages
        main = content.find('main')

        if main is None:
            print('No main element found')
            return ""
        else:
            print('Main element found')
            if len(main.get('class', [])) > 0 and 'publication' in main['class']:
                print(
                    'Publications page, skipping as the content is nested in PDFs (html-publication is fine)')
                return ''

            print("Not a publication page, continuing")
            sanitised_html = remove_elements(main)
            cleaned = str(clean_string(sanitised_html.get_text()))
            return unidecode(cleaned)


grand_total_tokens = 0
grand_total_cost = 0
vector_store = MongoRepository().vector_store

for filename in os.listdir("to_do_sitemaps"):
    file_being_processed = filename
    f = os.path.join("to_do_sitemaps", filename)
    if os.path.isfile(f) and f.endswith('.xml'):
        print(filename)
        sitemap_loader = SitemapLoader(web_path=f,
                                       is_local=True,
                                       parsing_function=sanitise_html,
                                       meta_function=meta_function,
                                       )

        sitemap_loader.requests_per_second = 1

        docs = sitemap_loader.load()

        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=3000,
            chunk_overlap=0,
            length_function=len,
        )

        documents: list[Document] = text_splitter.split_documents(docs)

        tokens_utils = TokenUtils()

        total_tokens = 0

        doc: Document
        for doc in documents:
            total_tokens += tokens_utils.calculate_token_length(doc.page_content)

        print('Number of documents: ' + str(len(documents)))
        vector_store.add_documents(documents)

        total_cost = tokens_utils.calculate_embedding_token_cost(total_tokens)
        grand_total_tokens += total_tokens
        grand_total_cost += total_cost
        shutil.move(f, 'done_sitemaps/' + filename)

        print('----------------------------------------------------')
        print('Number of documents: ' + str(len(documents)))
        print('Total tokens: ' + str(total_tokens))
        print('Total cost: $' + str(total_cost))
        print('Finished sitemap: ' + f + ' @ ' + str(datetime.now()))
        print('----------------------------------------------------')

print('Grand total tokens: ' + str(grand_total_tokens))
print('Grand total cost: $' + str(grand_total_cost))
print('----------------------------------------------------')
