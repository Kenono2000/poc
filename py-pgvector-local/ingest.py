import argparse
import json
from pathlib import Path

import openai
import psycopg2
from langchain_core.documents import Document
from langchain_openai import OpenAIEmbeddings
from psycopg2.extras import execute_values
from utilities import (
    get_db_connection,
    get_documents,
    get_embedding_model,
    load_config,
    split_chunks,
)


def ingest_data(chunks: list[Document], embeddings_model: OpenAIEmbeddings, db_url: str):
    if not chunks:
        print("No chunks to ingest.")
        return
    chunk_texts = [chunk.page_content for chunk in chunks]
    chunk_titles = [Path(chunk.metadata.get("source", f"Chunk_{i+1}")).name for i, chunk in enumerate(chunks)]
    print(f"🚀 Generating embeddings for {len(chunk_texts)} chunks...")
    embeddings = embeddings_model.embed_documents(chunk_texts)
    print("  [✓] Embeddings generated.")
    default_roles = json.dumps(["GENERAL_USER"])
    data_to_insert = [
        (title, text, default_roles, str(embedding))
        for title, text, embedding in zip(chunk_titles, chunk_texts, embeddings)
    ]
    print("📦 Inserting into PostgreSQL...")
    try:
        with get_db_connection(db_url) as conn, conn.cursor() as cur:
            execute_values(
                cur,
                "INSERT INTO enterprise_documents (title, content, allowed_roles, embedding) VALUES %s",
                data_to_insert,
                template="(%s, %s, %s, %s::vector)",
                page_size=100
            )
        print(f"✅ Ingestion complete. Inserted {len(data_to_insert)} chunks.")
    except (psycopg2.Error, openai.OpenAIError) as e:
        print(f"❌ Database ingestion failed: {e}")

def main():
    parser = argparse.ArgumentParser(description="Ingest docs into pgvector.")
    parser.add_argument("paths", nargs='+', help="File or directory paths.")
    args = parser.parse_args()
    try:
        openai_api_key, database_url = load_config(str(Path(__file__).parent / ".env"))
    except ValueError as e:
        print(f"Error: {e}")
        return

    file_paths: list[str] = []
    for path in args.paths:
        p = Path(path)
        if p.is_dir():
            file_paths.extend(str(f) for f in p.rglob("*.pdf"))
            file_paths.extend(str(f) for f in p.rglob("*.md"))
        elif p.is_file() and p.suffix.lower() in {".pdf", ".md"}:
            file_paths.append(str(p))
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
