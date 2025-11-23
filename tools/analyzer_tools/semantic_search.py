from langchain_core.documents import Document
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_chroma import Chroma
from dotenv import load_dotenv
from typing import List
from langchain_core.documents import Document
from langchain_core.runnables import chain
import os

load_dotenv()

def load_document(file_path: str):
    try:
        loader = PyPDFLoader(file_path)
        docs = loader.load()
        return docs
    except Exception as e:
        print("Error loading document.", e)

        
def split_text(documents: list[Document],chunk_size=1000, chunk_overlap=200):
    try:
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size, chunk_overlap=chunk_size, add_start_index=True
        )
        splits = text_splitter.split_documents(documents=documents)
        return splits
    except Exception as e:
        print("Error splitting text.", e)

def create_vector_store(collection_name:str):
    embeddings = GoogleGenerativeAIEmbeddings(model="models/gemini-embedding-001", google_api_key=os.getenv("GOOGLE_API_KEY"))
    vector_store = Chroma(
        collection_name=collection_name,
        embedding_function=embeddings,
        persist_directory="./data/chroma_langchain_db",
    )

def store_documents(splits, vector_store):
    ids = vector_store.add_documents(documents=splits)
    return ids
    


@chain
def retriever(query: str, vector_store) -> List[Document]:
    return vector_store.similarity_search(query, k=1)
    