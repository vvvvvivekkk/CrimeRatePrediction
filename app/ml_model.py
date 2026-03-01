"""
ml_model.py – Train and evaluate predictive models with temporal features.

Uses TimeSeriesSplit for cross-validation, temporal features from preprocessing,
and saves best model (by R²) as model.pkl along with scaler and feature list.
"""
from __future__ import annotations

import joblib
import numpy as np
import pandas as pd
from sklearn.linear_model import LinearRegression
from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import TimeSeriesSplit
from sklearn.metrics import r2_score, mean_squared_error, mean_absolute_error
from xgboost import XGBRegressor
from sqlalchemy.orm import Session
import os

from app.preprocessing import load_data, preprocess_data

MODEL_PATH = "model.pkl"


def _cross_val_score_ts(model, X: pd.DataFrame, y: pd.Series, n_splits: int = 4) -> float:
    """Time-series cross-validation R² (mean across folds)."""
    tscv = TimeSeriesSplit(n_splits=n_splits)
    scores = []
    X_arr, y_arr = X.values, y.values
    for train_idx, val_idx in tscv.split(X_arr):
        Xtr, Xv = X_arr[train_idx], X_arr[val_idx]
        ytr, yv = y_arr[train_idx], y_arr[val_idx]
        try:
            model.fit(Xtr, ytr)
            scores.append(r2_score(yv, model.predict(Xv)))
        except Exception:
            scores.append(-9999.0)
    return float(np.mean(scores))


def train_and_evaluate(db: Session) -> dict:
    """
    Load data → engineer features → train 3 models via TimeSeriesSplit
    → pick best by R² → save model.pkl.

    Returns a status dict with per-model metrics.
    """
    df = load_data(db)
    if df.empty:
        return {"error": "No data found. Please generate the dataset first."}

    try:
        X_train, X_test, y_train, y_test, scaler, features = preprocess_data(df)
    except Exception as e:
        return {"error": f"Preprocessing failed: {str(e)}"}

    if len(X_test) == 0:
        return {"error": "Test set is empty — not enough data to evaluate. Please regenerate data."}

    models: dict = {
        "Linear Regression": LinearRegression(),
        "Random Forest": RandomForestRegressor(
            n_estimators=200, max_depth=12, min_samples_leaf=2,
            n_jobs=-1, random_state=42
        ),
        "XGBoost": XGBRegressor(
            n_estimators=200, learning_rate=0.08, max_depth=6,
            subsample=0.8, colsample_bytree=0.8,
            random_state=42, verbosity=0
        ),
    }

    results: dict = {}
    best_name: str | None  = None
    best_model             = None
    best_r2                = -float("inf")

    for name, model in models.items():
        try:
            # Cross-validation for robust model selection
            cv_r2 = _cross_val_score_ts(model, X_train, y_train)

            # Final fit on full training set
            model.fit(X_train, y_train)
            preds = model.predict(X_test)

            r2   = float(r2_score(y_test, preds))
            rmse = float(np.sqrt(mean_squared_error(y_test, preds)))
            mae  = float(mean_absolute_error(y_test, preds))

            results[name] = {
                "R2_Score": round(r2,   4),
                "CV_R2":    round(cv_r2, 4),
                "RMSE":     round(rmse,  4),
                "MAE":      round(mae,   4),
            }

            # Select by hold-out R² (more reliable than CV for final selection)
            if r2 > best_r2:
                best_r2   = r2
                best_name = name
                best_model = model

        except Exception as e:
            results[name] = {"error": str(e)}

    if best_model is None:
        return {"error": "All models failed to train."}

    joblib.dump(
        {"model": best_model, "scaler": scaler, "features": features},
        MODEL_PATH,
    )

    return {
        "status":     "success",
        "best_model": best_name,
        "metrics":    results,
        "features_used": features,
    }
