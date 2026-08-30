from langchain_community.document_loaders import DirectoryLoader, JSONLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.documents import Document
from langchain_openai import OpenAIEmbeddings
from langchain_chroma import Chroma
from langchain_community.document_loaders import PyPDFLoader
from chromadb import HttpClient
# from langchain_redis import RedisVectorStore
# import openai
# from langchain_ollama import OllamaEmbeddings, ChatOllama
# from langchain_community.embeddings import VolcanoEmbeddings
from dotenv import load_dotenv
# from langchain_openai import ChatOpenAI
import os
import shutil
# from langchain_community.embeddings.openai import OpenAIEmbeddings
load_dotenv()

import config

CHROMA_PATH = config.CHROMA_DIR_PATH
DATA_PATH = 'data'


def main():
    generate_data_source()


def generate_data_source():
    documents = load_documents()
    chunks = split_text(documents)
    save_to_chroma(chunks)


def load_documents():
    documents = []
    # Define a jq_schema to extract data from JSON files
    jq_schema = '.'  # Modify this based on your JSON structure

    for root, dirs, files in os.walk(DATA_PATH):
        for filename in files:
            file_path = os.path.join(root, filename)
            if filename.endswith('.json'):
                # Use JSONLoader for JSON files with the specified jq_schema
                loader = JSONLoader(file_path, jq_schema, text_content=False)
                json_docs = loader.load()
                for doc in json_docs:
                    # If page_content is a list, join it into a string
                    if isinstance(doc.page_content, list):
                        doc.page_content = ' '.join(doc.page_content)
                    documents.append(doc)
            elif filename.endswith('.pdf'):
                print("**********")
                print(file_path)
                # Use DirectoryLoader for other file types like PDFs
                loader = PyPDFLoader(
                    file_path = file_path,
                    # headers = None
                    # password = None,
                    mode = "page",
                    pages_delimiter = "\n\x0c"
                )
                documents.extend(loader.load())
            else:
                print(f"Unsupported file type: {filename}")

    print('TOTAL_DOCUMENTS:', len(documents))
    for doc in documents:
        print(f'Document source: {doc.metadata.get("source", "N/A")}')
        print(f'Document content preview: {doc.page_content[:200]}...')

    return documents


def split_text(documents: list[Document]):
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000,
        chunk_overlap=200,
        length_function=len,
        add_start_index=True
    )
    chunks = text_splitter.split_documents(documents)
    print(f'Split {len(documents)} documents into {len(chunks)} chunks.')

    if len(chunks):
        for index, chunk in enumerate(chunks):
            # Access the chunk using the index
            document = chunks[index]  # Or simply use `chunk`

            # Print the content and metadata of the document
            print(f'Document {index + 1} Page Content:', document.page_content)
            print(f'Document {index + 1} Meta Data:', document.metadata)

    return chunks


def save_to_chroma(chunks: list[Document]):
    # clear out the database first
    if os.path.exists(CHROMA_PATH):
        shutil.rmtree(CHROMA_PATH)

    embedding_fn = OpenAIEmbeddings(
        model=config.EMBEDDING_MODEL,
        openai_api_key=config.LLM_API_KEY,
        openai_api_base=config.LLM_BASE_URL
    )
    for i in range(0, len(chunks), 64):
        chunk = chunks[i:i+64]
        db = Chroma.from_documents(chunk, embedding_fn,
                                collection_name = config.CHROMA_COLLECTION_NAME,
                                persist_directory=CHROMA_PATH)

    print(f'Saved {len(chunks)} chunks to {CHROMA_PATH}.')


main()