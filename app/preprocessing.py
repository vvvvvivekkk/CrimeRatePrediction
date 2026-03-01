"""
preprocessing.py – Feature engineering with temporal crime features.

Adds lag and rolling features that make predictions time-aware:
  crime_lag1  : crime rate from previous year (per state)
  crime_lag2  : crime rate from 2 years ago
  rolling3    : 3-year rolling average
  year_trend  : linear year index (0 = 2010)

Uses TimeSeriesSplit for proper temporal cross-validation.
"""
from __future__ import annotations

import pandas as pd
import numpy as np
from sklearn.preprocessing import StandardScaler
from sqlalchemy.orm import Session

from app.models import HistoricalCrimeData


FEATURES = [
    "population",
    "unemployment_rate",
    "literacy_rate",
    "urbanization_rate",
    "police_strength_per_100k",
    "year_trend",
    "crime_lag1",
    "crime_lag2",
    "rolling3",
]
TARGET = "crime_rate_per_100k"


def load_data(db: Session) -> pd.DataFrame:
    """Load all historical records from the DB."""
    query = db.query(HistoricalCrimeData).statement
    df = pd.read_sql(query, db.bind)
    return df


def _add_temporal_features(df: pd.DataFrame) -> pd.DataFrame:
    """Add lag and rolling average features grouped by state."""
    df = df.sort_values(["state_name", "year"]).copy()

    grp = df.groupby("state_name")["crime_rate_per_100k"]
    df["crime_lag1"]  = grp.shift(1)
    df["crime_lag2"]  = grp.shift(2)
    df["rolling3"]    = grp.transform(
        lambda s: s.shift(1).rolling(window=3, min_periods=1).mean()
    )
    df["year_trend"]  = df["year"] - df["year"].min()

    # Fill remaining NaN in temporal cols with column median (for years 1-2)
    for col in ("crime_lag1", "crime_lag2", "rolling3"):
        df[col] = df[col].fillna(df[TARGET])

    return df


def preprocess_data(df: pd.DataFrame):
    """
    Full preprocessing pipeline.

    Returns
    -------
    X_train, X_test, y_train, y_test, scaler, feature_names
    """
    df = _add_temporal_features(df)

    # Drop rows still missing target
    df = df.dropna(subset=[TARGET])

    # Handle missing feature values
    df[FEATURES] = df[FEATURES].fillna(df[FEATURES].median())

    # Clip outliers (IQR per feature)
    for col in FEATURES:
        q1, q3 = df[col].quantile(0.25), df[col].quantile(0.75)
        iqr = q3 - q1
        df[col] = df[col].clip(q1 - 2.5 * iqr, q3 + 2.5 * iqr)

    # Temporal train/test split: train on 2010-2020, test on 2021-2024
    train_df = df[df["year"] <= 2020].copy()
    test_df  = df[df["year"] >= 2021].copy()

    X_train = train_df[FEATURES]
    y_train = train_df[TARGET]
    X_test  = test_df[FEATURES]
    y_test  = test_df[TARGET]

    scaler = StandardScaler()
    X_train_scaled = pd.DataFrame(
        scaler.fit_transform(X_train), columns=FEATURES, index=X_train.index
    )
    X_test_scaled = pd.DataFrame(
        scaler.transform(X_test), columns=FEATURES, index=X_test.index
    )

    return X_train_scaled, X_test_scaled, y_train, y_test, scaler, FEATURES
