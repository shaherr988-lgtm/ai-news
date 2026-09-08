from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from apps.core.enums import SourceType
from apps.models.source import Source
from apps.core.db import get_db

router = APIRouter(prefix="/sources", tags=["sources"])
templates = Jinja2Templates(directory="apps/web/templates")


@router.get("")
def list_sources(request: Request, db: Session = Depends(get_db)):
    sources = db.query(Source).order_by(Source.source_type, Source.name).all()
    return templates.TemplateResponse(
        request, "sources_list.html", {"sources": sources, "source_types": list(SourceType)}
    )


@router.post("")
def create_source(
    name: str = Form(...),
    source_type: SourceType = Form(...),
    url: str = Form(...),
    rss_url: str = Form(""),
    db: Session = Depends(get_db),
):
    db.add(
        Source(
            name=name.strip(),
            source_type=source_type,
            url=url.strip(),
            rss_url=rss_url.strip() or None,
        )
    )
    db.commit()
    return RedirectResponse(url="/sources", status_code=303)


@router.post("/{source_id}/toggle")
def toggle_active(source_id: int, db: Session = Depends(get_db)):
    source = db.get(Source, source_id)
    if source:
        source.is_active = not source.is_active
        db.commit()
    return RedirectResponse(url="/sources", status_code=303)
