from __future__ import annotations

import io
import csv
import os
from typing import List, Optional

from fastapi import FastAPI, Depends, Query, Request
from fastapi.responses import HTMLResponse, FileResponse, JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.database import engine, Base, get_db
from app.models import HistoricalCrimeData, PredictedCrimeData
from app.dataset_generator import generate_synthetic_data
from app.real_dataset_loader import reset_and_reload
from app.ml_model import train_and_evaluate, MODEL_PATH, get_feature_importance
from app.forecasting import forecast_crime_rates
from app.report_generator import generate_pdf_report
from app.filtering import filter_historical, filter_predicted, parse_states_param

# Ensure tables exist
Base.metadata.create_all(bind=engine)

app = FastAPI(title="Crime Rate Prediction System – India", version="2.0")
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")


# ── Row serializers ────────────────────────────────────────────────────────────

def _hist_to_dict(row: HistoricalCrimeData) -> dict:
    return {
        "id": row.id,
        "state_name": row.state_name,
        "year": row.year,
        "population": row.population,
        "unemployment_rate": row.unemployment_rate,
        "literacy_rate": row.literacy_rate,
        "urbanization_rate": row.urbanization_rate,
        "police_strength_per_100k": row.police_strength_per_100k,
        "crime_rate_per_100k": row.crime_rate_per_100k,
    }


def _pred_to_dict(row: PredictedCrimeData) -> dict:
    return {
        "id": row.id,
        "state_name": row.state_name,
        "year": row.year,
        "predicted_crime_rate": row.predicted_crime_rate,
        "crime_level": row.crime_level,
    }


# ── Pages ──────────────────────────────────────────────────────────────────────

@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@app.get("/dashboard", response_class=HTMLResponse)
async def get_dashboard(request: Request):
    return templates.TemplateResponse("dashboard.html", {"request": request})


# ── Data pipeline ──────────────────────────────────────────────────────────────

@app.get("/generate-data")
async def api_generate_data(db: Session = Depends(get_db)):
    """Generate synthetic historical data (29 states × 15 years) and store in SQLite."""
    return generate_synthetic_data(db)


@app.get("/reset-data")
async def api_reset_data(db: Session = Depends(get_db)):
    """Clear all data and reload fresh NCRB-calibrated records."""
    return reset_and_reload(db)


@app.get("/train")
async def api_train_model(db: Session = Depends(get_db)):
    """Train LR + RF + XGBoost with temporal features. Save best model."""
    return train_and_evaluate(db)


@app.get("/predict")
async def api_predict(
    state: Optional[str] = Query(None, description="Single state name"),
    states: Optional[str] = Query(None, description="Comma-separated state names"),
    years: int = Query(5, ge=1, le=10, description="Years to forecast"),
    db: Session = Depends(get_db),
):
    """
    Generate crime rate forecasts.

    - `/predict?years=5` → all states
    - `/predict?state=Maharashtra&years=5`
    - `/predict?states=Maharashtra,Kerala&years=10`
    """
    if states:
        state_list = parse_states_param(states)
        results = []
        errors = []
        for s in (state_list or []):
            r = forecast_crime_rates(db, target_state=s, years_to_predict=years)
            if "error" in r:
                errors.append(f"{s}: {r['error']}")
            else:
                results.extend(r.get("data", []))
        if errors and not results:
            return JSONResponse({"error": "; ".join(errors)}, status_code=400)
        return {"message": f"Forecasted {years} year(s) for {len(state_list or [])} state(s).", "data": results}

    return forecast_crime_rates(db, target_state=state, years_to_predict=years)


# ── Health ─────────────────────────────────────────────────────────────────────

@app.get("/health")
async def api_health(db: Session = Depends(get_db)):
    hist_count = db.query(HistoricalCrimeData).count()
    pred_count = db.query(PredictedCrimeData).count()
    model_ok   = os.path.exists(MODEL_PATH)
    states_predicted = (
        db.query(PredictedCrimeData.state_name).distinct().count()
        if pred_count > 0 else 0
    )
    return {
        "status": "ok",
        "historical_count": hist_count,
        "predicted_count": pred_count,
        "states_with_predictions": states_predicted,
        "model_exists": model_ok,
    }


# ── Filtered API data ──────────────────────────────────────────────────────────

@app.get("/api/data/historical")
async def api_get_historical(
    state: Optional[str] = Query(None),
    states: Optional[str] = Query(None),
    start_year: Optional[int] = Query(None),
    end_year: Optional[int] = Query(None),
    db: Session = Depends(get_db),
):
    """Return historical data with optional state/year filters."""
    q = db.query(HistoricalCrimeData)
    q = filter_historical(
        q,
        state=state,
        states=parse_states_param(states),
        start_year=start_year,
        end_year=end_year,
    )
    return [_hist_to_dict(r) for r in q.all()]


@app.get("/api/data/predicted")
async def api_get_predicted(
    state: Optional[str] = Query(None),
    states: Optional[str] = Query(None),
    start_year: Optional[int] = Query(None),
    end_year: Optional[int] = Query(None),
    db: Session = Depends(get_db),
):
    """Return predicted data with optional state/year filters."""
    q = db.query(PredictedCrimeData)
    q = filter_predicted(
        q,
        state=state,
        states=parse_states_param(states),
        start_year=start_year,
        end_year=end_year,
    )
    return [_pred_to_dict(r) for r in q.all()]


@app.get("/api/states")
async def api_get_states(db: Session = Depends(get_db)):
    """Return sorted list of all states that have historical data."""
    rows = db.query(HistoricalCrimeData.state_name).distinct().order_by(HistoricalCrimeData.state_name).all()
    return [r[0] for r in rows]


@app.get("/api/feature-importance")
async def api_feature_importance():
    """Return feature importance from the trained model (RF/XGB). None if not available."""
    imp = get_feature_importance()
    if imp is None:
        return {"feature_importance": None, "message": "Model not trained or Linear Regression (no importance)."}
    return {"feature_importance": imp}


# ── CSV exports ────────────────────────────────────────────────────────────────

@app.get("/export-csv")
async def api_export_csv(
    state: Optional[str] = Query(None),
    states: Optional[str] = Query(None),
    start_year: Optional[int] = Query(None),
    end_year: Optional[int] = Query(None),
    db: Session = Depends(get_db),
):
    q = db.query(HistoricalCrimeData)
    q = filter_historical(q, state=state, states=parse_states_param(states),
                          start_year=start_year, end_year=end_year)
    records = q.all()
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["id", "state_name", "year", "population",
                     "unemployment_rate", "literacy_rate", "urbanization_rate",
                     "police_strength_per_100k", "crime_rate_per_100k"])
    for r in records:
        writer.writerow([r.id, r.state_name, r.year, r.population,
                         r.unemployment_rate, r.literacy_rate,
                         r.urbanization_rate, r.police_strength_per_100k,
                         r.crime_rate_per_100k])
    output.seek(0)
    return StreamingResponse(
        output, media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=historical_crime_data.csv"})


@app.get("/export-predictions-csv")
async def api_export_predictions_csv(
    state: Optional[str] = Query(None),
    states: Optional[str] = Query(None),
    start_year: Optional[int] = Query(None),
    end_year: Optional[int] = Query(None),
    db: Session = Depends(get_db),
):
    q = db.query(PredictedCrimeData)
    q = filter_predicted(q, state=state, states=parse_states_param(states),
                         start_year=start_year, end_year=end_year)
    records = q.all()
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["id", "state_name", "year", "predicted_crime_rate", "crime_level"])
    for r in records:
        writer.writerow([r.id, r.state_name, r.year, r.predicted_crime_rate, r.crime_level])
    output.seek(0)
    return StreamingResponse(
        output, media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=predicted_crime_data.csv"})


# ── PDF Report ─────────────────────────────────────────────────────────────────

@app.get("/report/{state}")
async def api_report(state: str, db: Session = Depends(get_db)):
    from urllib.parse import unquote
    state_decoded = unquote(state)
    file_path = generate_pdf_report(state_decoded, db)
    if not file_path or not os.path.exists(file_path):
        return JSONResponse({"error": "Report could not be generated"}, status_code=404)
    return FileResponse(
        path=file_path,
        filename=f"crime_report_{state_decoded.replace(' ', '_')}.pdf",
        media_type="application/pdf",
    )
