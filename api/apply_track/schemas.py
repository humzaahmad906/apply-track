"""The ResumeJSON contract.

This is the single shape that the LLM extraction step produces and that the
deterministic renderer consumes. Every section, item and bullet carries a
stable id so a variant can reference, reorder and toggle it.
"""

from __future__ import annotations

import uuid
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

SectionKind = Literal[
    "experience",
    "education",
    "projects",
    "skills",
    "certifications",
    "awards",
    "publications",
    "custom",
]

KNOWN_KINDS: set[str] = set(SectionKind.__args__)

# Order the renderer falls back to when a resume has no explicit ordering.
DEFAULT_KIND_ORDER: list[str] = [
    "experience",
    "projects",
    "education",
    "skills",
    "certifications",
    "awards",
    "publications",
    "custom",
]


def new_id() -> str:
    return uuid.uuid4().hex[:12]


class Base(BaseModel):
    # Extraction is fuzzy: drop unexpected keys rather than reject the payload.
    model_config = ConfigDict(extra="ignore")


class Link(Base):
    label: str = ""
    url: str = ""


class Basics(Base):
    name: str = ""
    headline: str = ""
    email: str = ""
    phone: str = ""
    location: str = ""
    links: list[Link] = Field(default_factory=list)
    summary: str = ""


class Bullet(Base):
    id: str = Field(default_factory=new_id)
    text: str = ""
    include: bool = True


class Item(Base):
    """One entry in a section.

    Field meaning shifts with the parent section kind, which keeps the schema
    flat enough for the model to fill reliably:

    experience  title=role      subtitle=company     bullets=achievements
    education   title=degree    subtitle=institution
    projects    title=project   subtitle=tech stack  bullets=highlights
    skills      title=group     tags=the skills
    """

    id: str = Field(default_factory=new_id)
    include: bool = True
    title: str = ""
    subtitle: str = ""
    location: str = ""
    start: str = ""
    end: str = ""
    current: bool = False
    url: str = ""
    description: str = ""
    bullets: list[Bullet] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)


class Section(Base):
    id: str = Field(default_factory=new_id)
    kind: SectionKind = "custom"
    title: str = ""
    include: bool = True
    items: list[Item] = Field(default_factory=list)

    @field_validator("kind", mode="before")
    @classmethod
    def coerce_kind(cls, v: object) -> str:
        """Map an unrecognised kind onto 'custom' instead of failing the parse."""
        if not isinstance(v, str):
            return "custom"
        norm = v.strip().lower().replace(" ", "_")
        aliases = {
            "work": "experience",
            "work_experience": "experience",
            "employment": "experience",
            "professional_experience": "experience",
            "project": "projects",
            "personal_projects": "projects",
            "capstone": "projects",
            "capstone_projects": "projects",
            "skill": "skills",
            "technical_skills": "skills",
            "certification": "certifications",
            "certs": "certifications",
            "award": "awards",
            "honors": "awards",
            "publication": "publications",
        }
        norm = aliases.get(norm, norm)
        return norm if norm in KNOWN_KINDS else "custom"


class ResumeJSON(Base):
    basics: Basics = Field(default_factory=Basics)
    sections: list[Section] = Field(default_factory=list)


def assign_ids(resume: ResumeJSON) -> ResumeJSON:
    """Give every node a fresh id. Run once, right after extraction."""
    for section in resume.sections:
        section.id = new_id()
        for item in section.items:
            item.id = new_id()
            for bullet in item.bullets:
                bullet.id = new_id()
    return resume


def resolve(resume: ResumeJSON) -> ResumeJSON:
    """Drop everything switched off. This is what the renderer receives."""
    sections: list[Section] = []
    for section in resume.sections:
        if not section.include:
            continue
        items = []
        for item in section.items:
            if not item.include:
                continue
            kept = item.model_copy(
                update={"bullets": [b for b in item.bullets if b.include]}
            )
            items.append(kept)
        if items:
            sections.append(section.model_copy(update={"items": items}))
    return resume.model_copy(update={"sections": sections})
