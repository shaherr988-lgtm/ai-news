from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from apps.models.digest import DailyDigest
from apps.core.db import get_db

router = APIRouter(prefix="/digests", tags=["digests"])
templates = Jinja2Templates(directory="apps/web/templates")


@router.get("")
def list_digests(request: Request, db: Session = Depends(get_db)):
    digests = db.query(DailyDigest).order_by(DailyDigest.digest_date.desc()).all()
    return templates.TemplateResponse(request, "digests_list.html", {"digests": digests})


@router.get("/{digest_date}")
def get_digest(request: Request, digest_date: date, db: Session = Depends(get_db)):
    digest = db.query(DailyDigest).filter_by(digest_date=digest_date).first()
    if digest is None:
        raise HTTPException(status_code=404, detail="لا يوجد ملخص لهذا التاريخ")
    return templates.TemplateResponse(request, "digest_detail.html", {"digest": digest})
