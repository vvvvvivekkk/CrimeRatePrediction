"""
forecasting.py – Recursive, time-aware crime rate forecasting.

Strategy:
  1. For each state, use the last N years of historical data to seed lag/rolling features.
  2. At each future step, use the model to predict the next year's crime rate.
  3. Feed that prediction back as crime_lag1/lag2/rolling3 for subsequent steps
     (recursive / "chained" forecasting — no random noise injected).
  4. Project socioeconomic features using data-driven trends (not magic constants).
"""
from __future__ import annotations

import os
import joblib
import numpy as np
import pandas as pd
from sqlalchemy.orm import Session

from app.models import PredictedCrimeData, HistoricalCrimeData
from app.ml_model import MODEL_PATH
from app.preprocessing import FEATURES


def classify_crime_level(rate: float) -> str:
    if rate < 150:
        return "Low"
    elif rate <= 300:
        return "Medium"
    else:
        return "High"


def _compute_trend(series: pd.Series, col: str) -> float:
    """Linear trend per year for a state time-series column."""
    if len(series) < 2:
        return 0.0
    x = np.arange(len(series), dtype=float)
    # Simple OLS slope
    x_mean = x.mean()
    y_mean = series.mean()
    slope = ((x - x_mean) * (series.values - y_mean)).sum() / max(((x - x_mean) ** 2).sum(), 1e-9)
    return float(np.clip(slope, -20.0, 20.0))


def forecast_crime_rates(
    db: Session,
    target_state: str | None = None,
    years_to_predict: int = 5,
) -> dict:
    """
    Recursively forecast crime rates for `years_to_predict` years.

    Parameters
    ----------
    target_state : str | None  – single state name or None for all states
    years_to_predict : int      – 1–10
    """
    # ── Load model ─────────────────────────────────────────────────────────────
    if not os.path.exists(MODEL_PATH):
        return {"error": "Model not found. Please train the model first."}

    try:
        saved     = joblib.load(MODEL_PATH)
        model     = saved["model"]
        scaler    = saved["scaler"]
        features  = saved["features"]
    except Exception as e:
        return {"error": f"Failed to load model: {str(e)}"}

    # ── Fetch historical data ───────────────────────────────────────────────────
    query = db.query(HistoricalCrimeData)
    if target_state:
        query = query.filter(HistoricalCrimeData.state_name == target_state)

    hist_df = pd.read_sql(query.statement, db.bind)

    if hist_df.empty:
        msg = (f"No historical data for '{target_state}'." if target_state
               else "No historical data. Please generate/load the dataset first.")
        return {"error": msg}

    hist_df = hist_df.sort_values(["state_name", "year"])
    max_hist_year = int(hist_df["year"].max())

    # ── Per-state recursive forecasting ────────────────────────────────────────
    predictions_to_save: list[PredictedCrimeData] = []
    response_data: list[dict] = []

    for state, sdf in hist_df.groupby("state_name"):
        sdf = sdf.sort_values("year").reset_index(drop=True)

        # Compute per-feature linear trends from historical data
        socio_trends = {
            col: _compute_trend(sdf[col], col)
            for col in [
                "population", "unemployment_rate", "literacy_rate",
                "urbanization_rate", "police_strength_per_100k",
            ]
        }

        # Seed values: last known row
        seed = sdf.iloc[-1].to_dict()
        last_year     = int(seed["year"])
        last_cr       = float(seed["crime_rate_per_100k"])

        # Seed the rolling window (up to last 3 years of actual crime rate)
        hist_crimes   = list(sdf["crime_rate_per_100k"].values)
        min_hist_year = int(sdf["year"].min())

        def get_lag(n: int) -> float:
            """Get crime rate n years before the CURRENT prediction step."""
            idx = len(hist_crimes) - n
            return float(hist_crimes[idx]) if idx >= 0 else last_cr

        def rolling3_of(window: list[float]) -> float:
            tail = window[-3:] if len(window) >= 3 else window
            return float(np.mean(tail))

        curr_features = dict(seed)

        for step in range(1, years_to_predict + 1):
            future_year = last_year + step

            # Project socioeconomic features by trend
            curr_features["year"] = future_year
            curr_features["year_trend"] = future_year - min_hist_year
            for col, trend in socio_trends.items():
                curr_features[col] = max(
                    1.0,
                    float(curr_features[col]) + trend
                )
            # Reasonable caps
            curr_features["literacy_rate"]     = min(99.0, curr_features["literacy_rate"])
            curr_features["urbanization_rate"]  = min(95.0, curr_features["urbanization_rate"])
            curr_features["unemployment_rate"]  = max(1.5,  curr_features["unemployment_rate"])
            curr_features["police_strength_per_100k"] = max(50.0, curr_features["police_strength_per_100k"])

            # Temporal lag features – use running hist_crimes list
            lag1 = get_lag(1)
            lag2 = get_lag(2)
            r3   = rolling3_of(hist_crimes[-3:] if len(hist_crimes) >= 3 else hist_crimes)

            curr_features["crime_lag1"] = lag1
            curr_features["crime_lag2"] = lag2
            curr_features["rolling3"]   = r3

            # Build feature row in correct order
            row_dict = {f: curr_features.get(f, 0.0) for f in features}
            X_row = pd.DataFrame([row_dict])[features]
            X_scaled = scaler.transform(X_row)

            predicted_rate = float(model.predict(X_scaled)[0])
            # Clip to plausible crime rate range
            predicted_rate = float(np.clip(predicted_rate, 30.0, 800.0))
            predicted_rate = round(predicted_rate, 2)
            crime_lvl      = classify_crime_level(predicted_rate)

            # Push this prediction into the running history for next step's lags
            hist_crimes.append(predicted_rate)

            response_data.append({
                "state_name":           state,
                "year":                 future_year,
                "predicted_crime_rate": predicted_rate,
                "crime_level":          crime_lvl,
            })

            predictions_to_save.append(PredictedCrimeData(
                state_name=state,
                year=future_year,
                predicted_crime_rate=predicted_rate,
                crime_level=crime_lvl,
            ))

    # ── Persist ─────────────────────────────────────────────────────────────────
    years_being_saved = list({r["year"] for r in response_data})
    if target_state:
        (db.query(PredictedCrimeData)
         .filter(
             PredictedCrimeData.state_name == target_state,
             PredictedCrimeData.year.in_(years_being_saved),
         )
         .delete(synchronize_session=False))
    else:
        db.query(PredictedCrimeData).delete()

    db.add_all(predictions_to_save)
    db.commit()

    return {
        "message": f"Forecasted {years_to_predict} year(s) for "
                   f"{len(set(r['state_name'] for r in response_data))} state(s).",
        "data": response_data,
    }
