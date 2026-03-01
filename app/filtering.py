"""
filtering.py – Shared query-filtering utilities.

Provides reusable helpers that apply state / year filters to
SQLAlchemy queries, keeping all filter logic in one place so
every endpoint stays consistent.
"""
from __future__ import annotations
from typing import List, Optional
from sqlalchemy.orm import Query

from app.models import HistoricalCrimeData, PredictedCrimeData


# ── Historical data ────────────────────────────────────────────────────────────

def filter_historical(
    query: Query,
    state: Optional[str] = None,
    states: Optional[List[str]] = None,
    start_year: Optional[int] = None,
    end_year: Optional[int] = None,
) -> Query:
    """Apply state and year filters to a HistoricalCrimeData query."""
    if state and state.lower() not in ("all", ""):
        query = query.filter(HistoricalCrimeData.state_name == state)
    elif states:
        clean = [s.strip() for s in states if s.strip()]
        if clean:
            query = query.filter(HistoricalCrimeData.state_name.in_(clean))
    if start_year:
        query = query.filter(HistoricalCrimeData.year >= start_year)
    if end_year:
        query = query.filter(HistoricalCrimeData.year <= end_year)
    return query


# ── Predicted data ─────────────────────────────────────────────────────────────

def filter_predicted(
    query: Query,
    state: Optional[str] = None,
    states: Optional[List[str]] = None,
    start_year: Optional[int] = None,
    end_year: Optional[int] = None,
) -> Query:
    """Apply state and year filters to a PredictedCrimeData query."""
    if state and state.lower() not in ("all", ""):
        query = query.filter(PredictedCrimeData.state_name == state)
    elif states:
        clean = [s.strip() for s in states if s.strip()]
        if clean:
            query = query.filter(PredictedCrimeData.state_name.in_(clean))
    if start_year:
        query = query.filter(PredictedCrimeData.year >= start_year)
    if end_year:
        query = query.filter(PredictedCrimeData.year <= end_year)
    return query


# ── CSV helpers ─────────────────────────────────────────────────────────────────

def parse_states_param(states_param: Optional[str]) -> Optional[List[str]]:
    """
    Parse a comma-separated states query param into a list.
    Example:  'Telangana,Karnataka' → ['Telangana', 'Karnataka']
    """
    if not states_param:
        return None
    parts = [s.strip() for s in states_param.split(",") if s.strip()]
    return parts if parts else None
