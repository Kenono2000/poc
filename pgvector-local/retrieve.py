import argparse
import logging
import os
import psycopg2
from typing import List, Tuple, Optional
from dataclasses import dataclass
from dotenv import load_dotenv
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)
load_dotenv()
@dataclass
class Config:
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    DATABASE_URL: str = os.getenv("DATABASE_URL", "")
    EMBEDDING_MODEL: str = "text-embedding-3-large"
    EMBEDDING_DIMENSIONS: int = 1536
    LLM_MODEL: str = "gpt-4o"
    LLM_TEMPERATURE: float = 0.0
    DEFAULT_TOP_K: int = 3
    SIMILARITY_THRESHOLD: float = 0.0
    DB_TIMEOUT: int = 30
    def validate(self) -> None:
        if not self.OPENAI_API_KEY:
            raise ValueError("OPENAI_API_KEY is missing from .env file.")
        if not self.DATABASE_URL:
            raise ValueError("DATABASE_URL is missing from .env file.")
        logger.info("Configuration validated successfully.")
config = Config()
class RAGClient:
    def __init__(self, cfg: Config):
        cfg.validate()
        self.config = cfg
        logger.info("Initializing embedding and LLM models...")
        self._embeddings_client = OpenAIEmbeddings(
            model=cfg.EMBEDDING_MODEL,
            dimensions=cfg.EMBEDDING_DIMENSIONS,
            openai_api_key=cfg.OPENAI_API_KEY
        )
        self._llm_client = ChatOpenAI(
            model=cfg.LLM_MODEL,
            temperature=cfg.LLM_TEMPERATURE,
            openai_api_key=cfg.OPENAI_API_KEY
        )
        logger.info("✓ Models initialized successfully.")
    def embed_question(self, question: str) -> List[float]:
        try:
            return self._embeddings_client.embed_query(question)
        except Exception as e:
            logger.error(f"Failed to embed question: {e}")
            raise
    def search_documents(
        self,
        query_vector: List[float],
        top_k: int
    ) -> List[Tuple[str, str, float]]:
        query_sql = """
            SELECT content, 1 - (embedding <=> %s::vector) AS similarity
            FROM enterprise_documents
            WHERE 1 - (embedding <=> %s::vector) > 0.5
            ORDER BY similarity DESC
            LIMIT %s;
        """
        try:
            with psycopg2.connect(
                self.config.DATABASE_URL,
                connect_timeout=self.config.DB_TIMEOUT
            ) as conn:
                with conn.cursor() as cur:
                    vector_str = str(query_vector)
                    cur.execute(query_sql, (vector_str, vector_str, top_k))
                    return cur.fetchall()
        except psycopg2.Error as e:
            logger.error(f"Database query failed: {e}")
            raise
    def generate_answer(self, question: str, context: str) -> str:
        system_prompt = """
            You are a helpful assistant. Use the following pieces of retrieved context to answer the question.
            If you don't know the answer, just say that you don't know. Keep the answer concise.

            Context:
            {context}
        """
        try:
            chain = ChatPromptTemplate.from_messages([
                ("system", system_prompt),
                ("human", "{question}")
            ]) | self._llm_client
            response = chain.invoke({"context": context, "question": question})
            return response.content
        except Exception as e:
            logger.error(f"Failed to generate answer: {e}")
            raise
    def retrieve_and_generate(
        self,
        question: str,
        top_k: Optional[int] = None
    ) -> Optional[str]:
        top_k = top_k or self.config.DEFAULT_TOP_K
        print(f"\n👤 Question: {question}")
        try:
            vector = self.embed_question(question)
            results = self.search_documents(vector, top_k)
            if not results:
                print("❌ No matching documents found.")
                return None
            context_text = "\n\n".join([r[0] for r in results])
            answer = self.generate_answer(question, context_text)
            print("\n" + "=" * 45)
            print("RAG RESPONSE")
            print("=" * 45)
            print(answer)
            print("=" * 45 + "\n")
            return answer
        except Exception as e:
            logger.error(f"RAG pipeline failed: {e}")
            print(f"❌ Error: {e}")
            return None

    

def main():
    parser = argparse.ArgumentParser(
        description="Query RAG pipeline to retrieve context and generate answers."
    )
    parser.add_argument(
        "question",
        nargs="?",
        default="Abyssium Studio",
        help="User query to the RAG system"
    )
    parser.add_argument(
        "--top_k",
        type=int,
        default=None,
        help=f"Number of documents to retrieve (default: {config.DEFAULT_TOP_K})"
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable debug logging"
    )
    args = parser.parse_args()
    if args.verbose:
        logger.setLevel(logging.DEBUG)
        for handler in logger.handlers:
            handler.setLevel(logging.DEBUG)
    try:
        logger.info("Initializing RAG client...")
        rag_client = RAGClient(config)
        rag_client.retrieve_and_generate(
            question=args.question,
            top_k=args.top_k
        )
    except ValueError as e:
        logger.error(f"Configuration error: {e}")
        print(f"❌ Configuration Error: {e}")
        exit(1)
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        print(f"❌ Unexpected Error: {e}")
        exit(1)

if __name__ == "__main__":
    main()