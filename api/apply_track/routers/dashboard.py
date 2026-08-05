"""The one endpoint the home page needs."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlmodel import Session

from ..dashboard import DashboardPayload, build
from ..db import get_session

router = APIRouter(prefix="/api", tags=["dashboard"])


@router.get("/dashboard", response_model=DashboardPayload)
def dashboard(session: Session = Depends(get_session)) -> DashboardPayload:
    return build(session)
