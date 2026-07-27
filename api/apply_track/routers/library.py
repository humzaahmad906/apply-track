"""Reusable items -- capstone projects, roles, skill groups.

Saves retyping the same capstone into every variant.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlmodel import Session, select

from ..db import get_session
from ..models import LibraryItem
from ..schemas import Item, new_id

router = APIRouter(prefix="/api/library", tags=["library"])


class LibraryIn(BaseModel):
    label: str
    section_kind: str = "projects"
    data: Item


class LibraryOut(BaseModel):
    id: int
    label: str
    section_kind: str
    data: dict[str, Any]
    created_at: datetime


@router.post("", response_model=LibraryOut, status_code=201)
def create(payload: LibraryIn, session: Session = Depends(get_session)) -> LibraryOut:
    row = LibraryItem(
        label=payload.label.strip() or payload.data.title or "Untitled",
        section_kind=payload.section_kind,
        data=payload.data.model_dump(),
    )
    session.add(row)
    session.commit()
    session.refresh(row)
    return LibraryOut(**row.model_dump())


@router.get("", response_model=list[LibraryOut])
def list_all(session: Session = Depends(get_session)) -> list[LibraryOut]:
    rows = session.exec(
        select(LibraryItem).order_by(LibraryItem.created_at.desc())
    ).all()
    return [LibraryOut(**r.model_dump()) for r in rows]


@router.get("/{item_id}/instance", response_model=Item)
def instance(item_id: int, session: Session = Depends(get_session)) -> Item:
    """A copy of the stored item with fresh ids, ready to drop into a variant."""
    row = session.get(LibraryItem, item_id)
    if row is None:
        raise HTTPException(404, "Library item not found.")
    item = Item.model_validate(row.data or {})
    item.id = new_id()
    item.include = True
    for bullet in item.bullets:
        bullet.id = new_id()
        bullet.include = True
    return item


@router.delete("/{item_id}", status_code=204)
def delete(item_id: int, session: Session = Depends(get_session)) -> None:
    row = session.get(LibraryItem, item_id)
    if row is None:
        raise HTTPException(404, "Library item not found.")
    session.delete(row)
    session.commit()
