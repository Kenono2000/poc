import os
import traceback
import psycopg2
from fastapi import FastAPI, Depends, HTTPException, Header
from pydantic import BaseModel, Field
from typing import List, Optional
from dotenv import load_dotenv
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
load_dotenv()
openai_api_key = os.getenv("OPENAI_API_KEY")
database_url = os.getenv("DATABASE_URL")
app = FastAPI(title="Enterprise Policy RAG Microservice", version="1.0.0")
class RAGResponse(BaseModel):
    answer: str = Field(description="Answer based on retrieved context.")
    citations: List[str] = Field(description="List of source document titles.")
    confidence_score: float = Field(description="Match score from 0.0 to 1.0.")
class QueryRequest(BaseModel):
    question: str
def log_error(stage: str, error: Exception) -> None:
    print(f"[ERROR] {stage}: {error}")
    traceback.print_exc()
def get_current_user_roles(authorization: Optional[str] = Header(None)) -> List[str]:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid token.")
    token = authorization.split("Bearer ")[1]
    roles = [role.strip() for role in token.split(",")]
    return roles
@app.post("/api/v1/ask", response_model=RAGResponse)
def ask_policy_question(
    request: QueryRequest,
    user_roles: List[str] = Depends(get_current_user_roles)
):
    try:
        embeddings_model = OpenAIEmbeddings(model="text-embedding-3-large", dimensions=1536, openai_api_key=openai_api_key)
        question_vector = embeddings_model.embed_query(request.question)
    except Exception as e:
        log_error("Embedding generation failed", e)
        raise HTTPException(status_code=500, detail=f"Embedding error: {str(e)}")
    try:
        conn = psycopg2.connect(database_url)
        cur = conn.cursor()
        sql_query = """
            SELECT content, title, 1 - (embedding <=> %s::vector) AS similarity
            FROM enterprise_documents
            WHERE allowed_roles ?| %s
            AND 1 - (embedding <=> %s::vector) > 0.5
            ORDER BY similarity DESC
            LIMIT 5;
        """
        cur.execute(sql_query, (str(question_vector), user_roles, str(question_vector)))
        rows = cur.fetchall()
    except Exception as e:
        log_error("Database retrieval failed", e)
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
    finally:
        if 'cur' in locals(): cur.close()
        if 'conn' in locals(): conn.close()
    if not rows:
        return RAGResponse(
            answer="No relevant or permitted information found.",
            citations=[],
            confidence_score=0.0
        )
    citations = list(set([row[1] for row in rows]))
    avg_similarity = float(sum([row[2] for row in rows]) / len(rows))
    formatted_context = "\n\n".join([f"Document: {row[1]}\nContent: {row[0]}" for row in rows])
    system_prompt = "You are an enterprise AI assistant. Answer the user's question using ONLY the provided Context. If the answer isn't in the context, say you don't know."
    prompt_template = ChatPromptTemplate.from_messages([
        ("system", system_prompt),
        ("human", "{context}\n\nQuestion: {question}")
    ])
    llm = ChatOpenAI(model="gpt-4o", temperature=0, openai_api_key=openai_api_key)
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
    except Exception as e:
        log_error("LLM synthesis failed", e)
        raise HTTPException(status_code=500, detail=f"LLM Error: {str(e)}")

# uvicorn api:app --reload