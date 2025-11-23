from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_chroma import Chroma
from dotenv import load_dotenv
from langchain.tools import tool
from pathlib import Path
from tools.analyzer_tools.pdf_loader import extract_pdf_content
import os
import hashlib

load_dotenv()

def load_document(file_path: str, extracted_content: str) -> Document:
    """Create a Document object from extracted PDF content."""
    try:
        doc = Document(
            page_content=extracted_content,
            metadata={
                "source": file_path,
                "extraction_method": "gemini-2.5-flash"
            }
        )
        return doc
    except Exception as e:
        print(f"Error loading document: {e}")
        raise

        
def split_text(documents: list[Document], chunk_size=1000, chunk_overlap=200) -> list[Document]:
    """Split documents into smaller chunks."""
    try:
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            separators=["\n## ", "\n### ", "\n\n", "\n", " ", ""],
            add_start_index=True
        )
        splits = text_splitter.split_documents(documents=documents)
        return splits
    except Exception as e:
        print(f"Error splitting text: {e}")
        raise


def create_vector_store(collection_name: str) -> Chroma:
    """Create or load a Chroma vector store."""
    embeddings = GoogleGenerativeAIEmbeddings(
        model="models/gemini-embedding-001",
        google_api_key=os.getenv("GOOGLE_API_KEY")
    )
    vector_store = Chroma(
        collection_name=collection_name,
        embedding_function=embeddings,
        persist_directory="./data/chroma_langchain_db",
    )
    return vector_store


def store_documents(splits: list[Document], vector_store: Chroma) -> list[str]:
    """Add document chunks to the vector store."""
    ids = vector_store.add_documents(documents=splits)
    return ids


def setup_for_rag(
    file_path: str,
    collection_name: str,
    chunk_size=1000,
    chunk_overlap=200,
    use_cache=True
) -> Chroma:
    """Setup RAG pipeline: extract PDF, chunk, and store in vector database."""
    try:
        pdf_path_obj = Path(file_path)
    
        pdf_hash = hashlib.md5(pdf_path_obj.read_bytes()).hexdigest()
        cache_dir = Path("./cache")
        cache_dir.mkdir(exist_ok=True)
        cache_file = cache_dir / f"{pdf_path_obj.stem}_{pdf_hash}.txt"
        
        if use_cache and cache_file.exists():
            print(f"Loading cached content from {cache_file}")
            extracted_content = cache_file.read_text(encoding="utf-8")
        else:
            print(f"Extracting content from {file_path} using Gemini...")
            extracted_content = extract_pdf_content.invoke({"file_path": file_path})
            
            if extracted_content.startswith("Error"):
                raise ValueError(f"Failed to extract PDF: {extracted_content}")
            
            if use_cache:
                cache_file.write_text(extracted_content, encoding="utf-8")
                print(f"Cached content to {cache_file}")
        
        doc = load_document(file_path, extracted_content)  
        
        splits = split_text([doc], chunk_size, chunk_overlap)
        print(f"Created {len(splits)} chunks")
        
        vector_store = create_vector_store(collection_name)
        ids = store_documents(splits, vector_store)
        print(f"Stored {len(ids)} document chunks in vector store")
        
        return vector_store
        
    except Exception as e:
        print(f"Failed to setup vector store for RAG: {e}")
        raise


def create_retrieve_context_tool(vector_store: Chroma):
    """Factory function to create a retrieve_context tool with access to vector_store."""
    
    @tool(response_format="content_and_artifact")
    def retrieve_context(query: str):
        """Retrieve information to help answer a query."""
        retrieved_docs = vector_store.similarity_search(query, k=2)
        serialized = "\n\n".join(
            f"Source: {doc.metadata}\nContent: {doc.page_content}"
            for doc in retrieved_docs
        )
        return serialized, retrieved_docs
    
    return retrieve_context