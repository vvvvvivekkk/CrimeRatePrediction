"""
forecasting.py – Recursive, time-aware crime rate forecasting.

- Adds forecast uncertainty noise (σ=3)
- Mild regression toward state historical mean to prevent unrealistic exponential drop
- Forecasts kept stable in [80, 450]
- Optional 95% confidence interval: ± 1.96 * RMSE (from model_metrics.json when available)
"""
from __future__ import annotations

import json
import os
import joblib
import numpy as np
import pandas as pd
from sqlalchemy.orm import Session

from app.models import PredictedCrimeData, HistoricalCrimeData
from app.ml_model import MODEL_PATH, METRICS_PATH
from app.preprocessing import FEATURES


def classify_crime_level(rate: float) -> str:
    if rate < 150:
        return "Low"
    elif rate <= 300:
        return "Medium"
    else:
        return "High"


def _get_rmse_for_confidence() -> float | None:
    """Load RMSE from model_metrics.json for optional confidence interval."""
    if not os.path.isfile(METRICS_PATH):
        return None
    try:
        with open(METRICS_PATH) as f:
            m = json.load(f)
        return m.get("rmse")
    except Exception:
        return None


def _compute_trend(series: pd.Series, col: str) -> float:
    """Linear trend per year for a state time-series column."""
    if len(series) < 2:
        return 0.0
    x = np.arange(len(series), dtype=float)
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
    Adds uncertainty noise, regression toward historical mean, and optional confidence interval.
    """
    if not os.path.exists(MODEL_PATH):
        return {"error": "Model not found. Please train the model first."}

    try:
        saved = joblib.load(MODEL_PATH)
        model = saved["model"]
        scaler = saved["scaler"]
        features = saved["features"]
    except Exception as e:
        return {"error": f"Failed to load model: {str(e)}"}

    rmse = _get_rmse_for_confidence()
    rng = np.random.default_rng(42)

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

    predictions_to_save: list[PredictedCrimeData] = []
    response_data: list[dict] = []

    for state, sdf in hist_df.groupby("state_name"):
        sdf = sdf.sort_values("year").reset_index(drop=True)
        hist_crime = sdf["crime_rate_per_100k"].values
        state_historical_mean = float(np.mean(hist_crime))
        state_historical_std = float(np.std(hist_crime)) if len(hist_crime) > 1 else 10.0

        socio_trends = {
            col: _compute_trend(sdf[col], col)
            for col in [
                "population", "unemployment_rate", "literacy_rate",
                "urbanization_rate", "police_strength_per_100k",
            ]
        }

        seed = sdf.iloc[-1].to_dict()
        last_year = int(seed["year"])
        last_cr = float(seed["crime_rate_per_100k"])
        hist_crimes = list(sdf["crime_rate_per_100k"].values)
        min_hist_year = int(sdf["year"].min())

        def get_lag(n: int) -> float:
            idx = len(hist_crimes) - n
            return float(hist_crimes[idx]) if idx >= 0 else last_cr

        def rolling3_of(window: list[float]) -> float:
            tail = window[-3:] if len(window) >= 3 else window
            return float(np.mean(tail))

        curr_features = dict(seed)

        for step in range(1, years_to_predict + 1):
            future_year = last_year + step

            curr_features["year"] = future_year
            curr_features["year_trend"] = future_year - min_hist_year
            for col, trend in socio_trends.items():
                curr_features[col] = max(1.0, float(curr_features[col]) + trend)
            curr_features["literacy_rate"] = min(99.0, curr_features["literacy_rate"])
            curr_features["urbanization_rate"] = min(95.0, curr_features["urbanization_rate"])
            curr_features["unemployment_rate"] = max(1.5, curr_features["unemployment_rate"])
            curr_features["police_strength_per_100k"] = max(50.0, curr_features["police_strength_per_100k"])

            lag1 = get_lag(1)
            lag2 = get_lag(2)
            r3 = rolling3_of(hist_crimes[-3:] if len(hist_crimes) >= 3 else hist_crimes)
            curr_features["crime_lag1"] = lag1
            curr_features["crime_lag2"] = lag2
            curr_features["rolling3"] = r3

            row_dict = {f: curr_features.get(f, 0.0) for f in features}
            X_row = pd.DataFrame([row_dict])[features]
            X_scaled = scaler.transform(X_row)

            predicted_rate = float(model.predict(X_scaled)[0])
            # Forecast uncertainty noise
            predicted_rate += float(rng.normal(0, 3.0))
            # Mild regression toward state historical mean (prevent unrealistic exponential drop)
            alpha = 0.92  # weight on raw prediction
            predicted_rate = alpha * predicted_rate + (1 - alpha) * state_historical_mean
            # Keep forecast stable in [80, 450]
            predicted_rate = float(np.clip(predicted_rate, 80.0, 450.0))
            predicted_rate = round(predicted_rate, 2)
            crime_lvl = classify_crime_level(predicted_rate)

            hist_crimes.append(predicted_rate)

            row_out = {
                "state_name": state,
                "year": future_year,
                "predicted_crime_rate": predicted_rate,
                "crime_level": crime_lvl,
            }
            if rmse is not None and rmse > 0:
                half_width = 1.96 * rmse
                row_out["confidence_lower"] = round(max(80, predicted_rate - half_width), 2)
                row_out["confidence_upper"] = round(min(450, predicted_rate + half_width), 2)
            response_data.append(row_out)

            predictions_to_save.append(PredictedCrimeData(
                state_name=state,
                year=future_year,
                predicted_crime_rate=predicted_rate,
                crime_level=crime_lvl,
            ))

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
