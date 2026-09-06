from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import JSONResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from apps.agent.embedding_factory import get_embedding_provider
from apps.agent.factory import get_llm_provider
from apps.core.config import get_settings
from apps.rag.prompts import RAG_SYSTEM_PROMPT, build_rag_prompt
from apps.rag.retrieval import retrieve_top_k
from apps.web.deps import get_db

router = APIRouter(prefix="/chat", tags=["chat"])
templates = Jinja2Templates(directory="apps/web/templates")


@router.get("")
def chat_page(request: Request):
    return templates.TemplateResponse(request, "chat.html", {})


@router.post("/ask")
def ask(question: str = Form(...), db: Session = Depends(get_db)):
    settings = get_settings()
    embedding_provider = get_embedding_provider(settings)
    llm_provider = get_llm_provider(settings)

    retrieved = retrieve_top_k(db, embedding_provider, question, k=settings.rag_top_k)
    if not retrieved:
        return JSONResponse(
            {
                "answer": "ما فيه محتوى مفهرس بعد — شغّل الـ pipeline اليومي أول مرة قبل ما تسأل.",
                "sources": [],
            }
        )

    prompt = build_rag_prompt(question, retrieved)
    answer = llm_provider.generate(RAG_SYSTEM_PROMPT, prompt, max_tokens=800)

    sources = [
        {"title": r.article.title, "url": r.article.url, "score": round(r.score, 3)}
        for r in retrieved
    ]
    return JSONResponse({"answer": answer, "sources": sources})
