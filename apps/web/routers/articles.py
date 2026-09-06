from fastapi import APIRouter, Depends, Query, Request
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session, joinedload

from apps.models.article import Article
from apps.models.source import Source
from apps.web.deps import get_db

router = APIRouter(prefix="/articles", tags=["articles"])
templates = Jinja2Templates(directory="apps/web/templates")


@router.get("")
def list_articles(
    request: Request,
    source_id: int | None = Query(default=None),
    db: Session = Depends(get_db),
):
    query = db.query(Article).options(joinedload(Article.source)).order_by(Article.published_at.desc())
    if source_id is not None:
        query = query.filter(Article.source_id == source_id)
    articles = query.limit(200).all()
    sources = db.query(Source).order_by(Source.name).all()

    return templates.TemplateResponse(
        request,
        "articles_list.html",
        {"articles": articles, "sources": sources, "selected_source_id": source_id},
    )
