"""Pydantic response models for analytics endpoints."""

from __future__ import annotations

from pydantic import BaseModel


class RiskTrendPoint(BaseModel):
    date: str
    critical: int = 0
    high: int = 0
    medium: int = 0
    low: int = 0
    info: int = 0


class EfficiencyMetrics(BaseModel):
    avg_review_seconds: float
    total_reviews: int
    completed_reviews: int
    completion_rate: float
    period_days: int


class WorkloadItem(BaseModel):
    assignee_name: str
    open_count: int
    completed_count: int
    overdue_count: int


class CategoryBreakdown(BaseModel):
    category: str
    count: int
    percentage: float


class AnalyticsOverview(BaseModel):
    total_reviews: int
    avg_review_seconds: float
    open_risks: int
    completion_rate: float
    reviews_this_week: int
    reviews_this_month: int
