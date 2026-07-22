"""Pydantic request/response models for templates and clause library endpoints."""

from __future__ import annotations

from pydantic import BaseModel, Field


class ContractTemplate(BaseModel):
    id: str
    org_id: str
    name: str
    description: str = ""
    category: str = ""
    content_text: str = ""
    created_by_user_id: str | None = None
    created_at: str
    updated_at: str


class TemplateCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    description: str = ""
    category: str = ""
    content_text: str = ""


class TemplateUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = None
    category: str | None = None
    content_text: str | None = None


class TemplateListResponse(BaseModel):
    items: list[ContractTemplate]
    total: int
    page: int
    page_size: int


class Clause(BaseModel):
    id: str
    org_id: str
    title: str
    content_text: str
    category: str = ""
    risk_level: str | None = None
    risk_annotation: str = ""
    created_by_user_id: str | None = None
    created_at: str
    updated_at: str


class ClauseCreate(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    content_text: str = Field(min_length=1)
    category: str = ""
    risk_level: str | None = None
    risk_annotation: str = ""


class ClauseUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=200)
    content_text: str | None = None
    category: str | None = None
    risk_level: str | None = None
    risk_annotation: str | None = None


class ClauseListResponse(BaseModel):
    items: list[Clause]
    total: int
    page: int
    page_size: int
