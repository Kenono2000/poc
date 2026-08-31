import sys
from pathlib import Path

import openai
import psycopg2

sys.path.insert(0, str(Path(__file__).parent.parent / "py-libraries"))

from fastapi import Depends, FastAPI, Header, HTTPException
from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field
from utilities import (
    get_db_connection,
    get_embedding_model,
    get_llm,
    load_config,
    log_error,
)

openai_api_key, database_url = load_config(str(Path(__file__).parent / ".env"))
app = FastAPI(title="Enterprise Policy RAG Microservice", version="1.0.0")

class RAGResponse(BaseModel):
    answer: str = Field(description="Answer based on retrieved context.")
    citations: list[str] = Field(description="List of source document titles.")
    confidence_score: float = Field(description="Match score from 0.0 to 1.0.")

class QueryRequest(BaseModel):
    question: str

def get_current_user_roles(authorization: str | None = Header(None)) -> list[str]:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid token.")
    token = authorization.split("Bearer ")[1]
    roles = [role.strip() for role in token.split(",")]
    return roles

_current_user_roles_dep = Depends(get_current_user_roles)

@app.post("/api/v1/ask", response_model=RAGResponse)
def ask_policy_question(
    request: QueryRequest,
    user_roles: list[str] = _current_user_roles_dep
):
    try:
        embeddings_model = get_embedding_model(openai_api_key)
        question_vector = embeddings_model.embed_query(request.question)
    except (openai.OpenAIError, ValueError) as e:
        log_error("Embedding generation failed", e)
        raise HTTPException(status_code=500, detail=f"Embedding error: {e!s}")

    try:
        with get_db_connection(database_url) as conn, conn.cursor() as cur:
            sql_query = """
                WITH ranked AS (
                    SELECT
                        content,
                        title,
                        1 - (embedding <=> %s::vector) AS similarity
                    FROM enterprise_documents
                    WHERE allowed_roles ?| %s
                    AND 1 - (embedding <=> %s::vector) > 0.5
                )
                SELECT content, title, similarity
                FROM ranked
                ORDER BY similarity DESC
                LIMIT 5;
            """
            cur.execute(sql_query, (str(question_vector), user_roles, str(question_vector)))
            rows = cur.fetchall()
    except (psycopg2.Error, ValueError) as e:
        log_error("Database retrieval failed", e)
        raise HTTPException(status_code=500, detail=f"Database error: {e!s}")

    if not rows:
        return RAGResponse(
            answer="No relevant or permitted information found.",
            citations=[],
            confidence_score=0.0
        )

    citations = list({row[1] for row in rows})
    avg_similarity = float(sum(row[2] for row in rows) / len(rows))
    formatted_context = "\n\n".join(f"Document: {row[1]}\nContent: {row[0]}" for row in rows)
    system_prompt = "You are an enterprise AI assistant. Answer the user's question using ONLY the provided Context. If the answer isn't in the context, say you don't know."
    prompt_template = ChatPromptTemplate.from_messages([
        ("system", system_prompt),
        ("human", "{context}\n\nQuestion: {question}")
    ])
    llm = get_llm(openai_api_key)
    structured_llm = llm.with_structured_output(RAGResponse)
    chain = prompt_template | structured_llm

    try:
        response = chain.invoke({
            "context": formatted_context,
            "question": request.question
        })
        response.citations = citations
        response.confidence_score = round(avg_similarity, 2)
        return response
    except (openai.OpenAIError, ValueError) as e:
        log_error("LLM synthesis failed", e)
        raise HTTPException(status_code=500, detail=f"LLM Error: {e!s}")

# uvicorn api:app --reload