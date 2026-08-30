import os
from pathlib import Path
from typing import List, Optional, Tuple
from dotenv import load_dotenv
from langchain_community.document_loaders import PyPDFLoader, UnstructuredMarkdownLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain_core.documents import Document
import psycopg2

def load_config(env_path: Optional[str] = None) -> Tuple[str, str]:
    if env_path is None:
        env_path = str(Path(__file__).parent / ".env")
    load_dotenv(env_path)
    openai_api_key = os.getenv("OPENAI_API_KEY", "")
    database_url = os.getenv("DATABASE_URL", "")
    if not openai_api_key:
        raise ValueError("OPENAI_API_KEY missing from .env.")
    if not database_url:
        raise ValueError("DATABASE_URL missing from .env.")
    return openai_api_key, database_url

def get_documents(file_paths: List[str]) -> List[Document]:
    print(f"📄 Loading {len(file_paths)} document(s)...")
    documents = []
    for file_path in file_paths:
        try:
            suffix = Path(file_path).suffix.lower()
            if suffix == ".pdf":
                loader = PyPDFLoader(file_path)
            elif suffix == ".md":
                loader = UnstructuredMarkdownLoader(file_path)
            else:
                print(f"⚠️ Skipping unsupported file: {file_path}")
                continue
            documents.extend(loader.load())
            print(f"  [✓] Loaded {file_path}")
        except Exception as e:
            print(f"❌ Failed to load {file_path}: {e}")
    return documents

def split_chunks(
    documents: List[Document],
    chunk_size: int = 2000,
    chunk_overlap: int = 200,
    separators: Optional[List[str]] = None
) -> List[Document]:
    if separators is None:
        separators = ["\n\n", "\n", " ", ""]
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        separators=separators
    )
    chunks = text_splitter.split_documents(documents)
    print(f"✂️ Created {len(chunks)} text chunks.")
    return chunks

def get_embedding_model(api_key: str) -> OpenAIEmbeddings:
    return OpenAIEmbeddings(
        model="text-embedding-3-large",
        dimensions=1536,
        openai_api_key=api_key
    )

def get_llm(api_key: str, model: str = "gpt-4o", temperature: float = 0.0) -> ChatOpenAI:
    return ChatOpenAI(model=model, temperature=temperature, openai_api_key=api_key)

def get_db_connection(database_url: str, timeout: int = 30):
    return psycopg2.connect(database_url, connect_timeout=timeout)
