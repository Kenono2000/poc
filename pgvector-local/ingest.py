import os
import argparse
import psycopg2
from psycopg2.extras import execute_values
import json
from dotenv import load_dotenv
from langchain_community.document_loaders import PyPDFLoader, UnstructuredMarkdownLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_openai import OpenAIEmbeddings
from langchain_core.documents import Document
from typing import List
def load_config():
    load_dotenv()
    openai_api_key = os.getenv("OPENAI_API_KEY")
    database_url = os.getenv("DATABASE_URL")
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
            if file_path.endswith(".pdf"):
                loader = PyPDFLoader(file_path)
            elif file_path.endswith(".md"):
                loader = UnstructuredMarkdownLoader(file_path)
            else:
                print(f"⚠️ Skipping unsupported file: {file_path}")
                continue
            documents.extend(loader.load())
            print(f"  [✓] Loaded {file_path}")
        except Exception as e:
            print(f"❌ Failed to load {file_path}: {e}")
    return documents
def split_chunks(documents: List[Document]) -> List[Document]:
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=2000,
        chunk_overlap=200,
        separators=["\n\n", "\n", " ", ""]
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
def ingest_data(chunks: List[Document], embeddings_model: OpenAIEmbeddings, db_url: str):
    if not chunks:
        print("No chunks to ingest.")
        return
    chunk_texts = [chunk.page_content for chunk in chunks]
    chunk_titles = [os.path.basename(c.metadata.get("source", f"Chunk_{i+1}")) for i, c in enumerate(chunks)]
    print(f"🚀 Generating embeddings for {len(chunk_texts)} chunks...")
    embeddings = embeddings_model.embed_documents(chunk_texts)
    print("  [✓] Embeddings generated.")
    default_roles = json.dumps(["GENERAL_USER"])
    data_to_insert = list(zip(chunk_titles, chunk_texts, [default_roles] * len(chunk_texts), [str(e) for e in embeddings]))
    print("📦 Inserting into PostgreSQL...")
    try:
        with psycopg2.connect(db_url) as conn:
            with conn.cursor() as cur:
                execute_values(
                    cur,
                    "INSERT INTO enterprise_documents (title, content, allowed_roles, embedding) VALUES %s",
                    data_to_insert,
                    template="(%s, %s, %s, %s::vector)",
                    page_size=100
                )
        print(f"✅ Ingestion complete. Inserted {len(data_to_insert)} chunks.")
    except Exception as e:
        print(f"❌ Database ingestion failed: {e}")
def main():
    parser = argparse.ArgumentParser(description="Ingest docs into pgvector.")
    parser.add_argument("paths", nargs='+', help="File or directory paths.")
    args = parser.parse_args()
    try:
        openai_api_key, database_url = load_config()
    except ValueError as e:
        print(f"Error: {e}")
        return
    file_paths = []
    for path in args.paths:
        if os.path.isdir(path):
            for root, _, files in os.walk(path):
                for file in files:
                    if file.endswith((".pdf", ".md")):
                        file_paths.append(os.path.join(root, file))
        elif os.path.isfile(path) and path.endswith((".pdf", ".md")):
            file_paths.append(path)
        else:
            print(f"⚠️ Skipping: {path}")
    if not file_paths:
        print("No valid files found.")
        return
    documents = get_documents(file_paths)
    chunks = split_chunks(documents)
    embeddings_model = get_embedding_model(openai_api_key)
    ingest_data(chunks, embeddings_model, database_url)
if __name__ == "__main__":
    main()