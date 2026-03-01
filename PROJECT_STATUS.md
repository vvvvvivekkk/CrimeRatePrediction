# Crime Rate Prediction System – India
## Project Status Report
**Last Updated:** 2026-02-26 · 12:44 IST

---

## ✅ What Has Been Done

### 1. Project Structure & Setup
- [x] Root project directory: `crime-rate-prediction/`
- [x] `requirements.txt` — all Python dependencies listed:
  - `fastapi`, `uvicorn[standard]`, `sqlalchemy`, `pandas`, `numpy`
  - `scikit-learn`, `xgboost`, `joblib`, `reportlab`, `jinja2`
  - `python-multipart`, `aiofiles` *(added to fix static file & form issues)*
- [x] `app/__init__.py` — added so `app/` is a proper Python package

---

### 2. Backend (FastAPI – `app/`)

| File | Status | Notes |
|------|--------|-------|
| `app/database.py` | ✅ Done | SQLite via SQLAlchemy; `get_db()` dependency |
| `app/models.py` | ✅ Done | `HistoricalCrimeData` + `PredictedCrimeData` ORM models |
| `app/schemas.py` | ✅ Done | Pydantic schemas (present) |
| `app/dataset_generator.py` | ✅ Done | 29 states × 15 years synthetic data with realistic trends |
| `app/preprocessing.py` | ✅ Done | Loads data, scales features, train/test split |
| `app/ml_model.py` | ✅ Fixed | Trains LR + Random Forest + XGBoost; saves best model as `model.pkl`; **fixed deprecated `squared=False` RMSE bug** (now uses `np.sqrt(mse)`) |
| `app/forecasting.py` | ✅ Rewritten | **Fixed**: uses last-known year per state as seed; scoped DELETE (single-state vs bulk); reproducible noise with `np.random.seed(42)` |
| `app/report_generator.py` | ✅ Done | PDF via `reportlab` — historical summary + forecast table |
| `app/main.py` | ✅ Rewritten | **Fixed critical bug**: ORM objects now serialized to dicts before returning JSON; URL-decoded state name in PDF route; proper `JSONResponse` for errors |

#### API Endpoints Available

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/` | GET | Landing page (index.html) |
| `/dashboard` | GET | Dashboard page |
| `/generate-data` | GET | Generates synthetic data → SQLite |
| `/train` | GET | Trains 3 ML models, saves best |
| `/predict?state=&years=` | GET | Runs forecast, saves to DB |
| `/export-csv` | GET | Streams CSV download |
| `/report/{state}` | GET | Generates & downloads PDF report |
| `/api/data/historical` | GET | Returns all historical data as JSON |
| `/api/data/predicted` | GET | Returns all predicted data as JSON |

---

### 3. Frontend – Templates

| File | Status | Notes |
|------|--------|-------|
| `templates/index.html` | ✅ Done | Premium landing page; 3-step workflow cards; model metrics panel; animated blobs, hero title |
| `templates/dashboard.html` | ✅ Done | Navbar, sidebar filters, KPI widgets, map container, 3 chart rows, predictions table |

---

### 4. Frontend – CSS (`static/css/style.css`)
- [x] Full dark-theme design system with CSS custom properties
- [x] Buttons (primary, success, secondary, outline, danger)
- [x] Status messages, toast notifications, spinner/loader
- [x] Animations: `fadeUp`, `floatBlob`, `shimmer`, `pulse-ring`, `gradientShift`
- [x] Sidebar layout, form controls, widget cards
- [x] Chart cards, map card, data table, risk level badges
- [x] Leaflet popup dark theme overrides
- [x] Responsive breakpoints (1280px, 900px, 540px)

---

### 5. Frontend – Dashboard JS (`static/js/dashboard.js`)
- [x] **App state management** (`State` object)
- [x] **Leaflet choropleth map** — loads GeoJSON (tries local file first, then GitHub CDN fallback); color-codes states by crime level
- [x] **Fallback circle markers** if GeoJSON fails — `STATE_COORDS` for all 29 states
- [x] **Trend Line Chart** (Chart.js) — historical + forecast overlay with gradient fill
- [x] **Top-10 Bar Chart** — horizontal bars for highest-risk states
- [x] **Risk Distribution Doughnut** — High / Medium / Low breakdown
- [x] **Feature Correlation Radar Chart** — normalized feature values per state
- [x] **KPI Widgets** — top risk state, highest rate, avg rate, low-risk count
- [x] **Predictions Table** — sortable, filtered by selected state, color-coded badges
- [x] **Generate Forecast button** — calls `/predict`, reloads, refreshes all charts
- [x] **PDF Report download** — opens `/report/{state}` in new tab
- [x] **State filter** — `<select>` populated from API; triggers chart refresh
- [x] **Forecast horizon selector** — 5 or 10 years
- [x] **Toast notifications** — info, success, error, warning

---

## 🔴 What Still Needs to Be Done

### P1 – Critical (Must Fix Before Running)

- [ ] **Install dependencies** — `pip install -r requirements.txt` must complete:
  ```bash
  cd c:\Users\Admin\Desktop\crime\crime-rate-prediction
  pip install -r requirements.txt
  ```

- [ ] **Start the server** and confirm no import errors:
  ```bash
  uvicorn app.main:app --reload --port 8000
  ```

- [ ] **End-to-end test** — in the browser at `http://localhost:8000`:
  1. Click **Generate** → confirms SQLite populated (435 rows)
  2. Click **Train** → confirms `model.pkl` created in project root
  3. Click **Open Dashboard →**
  4. Click **🔮 Generate Forecast** → all charts and map render
  5. Select a state → click **Download PDF Report** → PDF opens

---

### P2 – Important (Missing or Broken Features)

- [ ] **`app/preprocessing.py` — verify variable names** are consistent with `ml_model.py`
  - `ml_model.py` unpacks as `X_train, X_test, y_train, y_test, scaler, features`
  - Confirm `preprocessing.py` returns exactly this tuple in that order

- [ ] **GeoJSON state name matching** — the CDN GeoJSON uses `NAME_1` property; some names differ from our DB:

  | DB Name | GeoJSON NAME_1 |
  |---------|---------------|
  | Odisha | Orissa |
  | Uttarakhand | Uttaranchal |
  | Telangana | *(may be missing — carved from AP after 2014)* |

  → Add a name-alias map in `dashboard.js` `updateMapLayer()` function

- [ ] **`app/schemas.py` — wire Pydantic schemas** into API response_model for auto-validation

- [ ] **Auto-trigger forecast on first dashboard load** — if `predicted_crime_data` table is empty,
  automatically run a 5-year forecast so charts aren't blank for first-time users

---

### P3 – Enhancements (Nice to Have)

- [ ] Year slider on the choropleth map — animate through forecast years
- [ ] Progress bar / live log during model training (can take 5–15 sec)
- [ ] `/api/data/historical?state=<name>` — add optional filter to reduce payload size
- [ ] `/export-predictions-csv` — export predicted data as CSV
- [ ] Error pages — `404.html` / `500.html` templates
- [ ] `/health` endpoint — returns DB record counts for quick diagnostics
- [ ] PDF report improvement — embed matplotlib mini-charts in the PDF
- [ ] Update `README.md` with full setup + usage instructions

---

## 🚀 Quick Start

```bash
# Step 1 — Install
cd c:\Users\Admin\Desktop\crime\crime-rate-prediction
pip install -r requirements.txt

# Step 2 — Run
uvicorn app.main:app --reload --port 8000

# Step 3 — Open browser
#   Landing : http://localhost:8000
#   Dashboard: http://localhost:8000/dashboard
```

**Workflow order (in browser):**
| Step | Action | Result |
|------|--------|--------|
| 1 | Click **Generate** | 435 rows inserted into SQLite |
| 2 | Click **Train** | `model.pkl` saved, metrics shown |
| 3 | Click **Open Dashboard →** | Dashboard opens |
| 4 | Click **🔮 Generate Forecast** | Charts, map, table populate |
| 5 | Select state → **Download PDF** | PDF report downloaded |

---

## 📁 Final Project File Tree

```
crime-rate-prediction/
│
├── app/
│   ├── __init__.py              ✅ added
│   ├── database.py              ✅ SQLite + SQLAlchemy
│   ├── models.py                ✅ ORM models
│   ├── schemas.py               ✅ Pydantic schemas
│   ├── dataset_generator.py     ✅ 29 states × 15 years
│   ├── preprocessing.py         ✅ (verify variable names – P2)
│   ├── ml_model.py              ✅ fixed (RMSE bug)
│   ├── forecasting.py           ✅ rewritten
│   ├── report_generator.py      ✅ PDF via reportlab
│   └── main.py                  ✅ rewritten (JSON serialization)
│
├── static/
│   ├── css/
│   │   └── style.css            ✅ 1217 lines, full dark theme
│   └── js/
│       └── dashboard.js         ✅ 773 lines, all charts + map
│
├── templates/
│   ├── index.html               ✅ 252 lines, landing page
│   └── dashboard.html           ✅ 220 lines, full dashboard
│
├── requirements.txt             ✅ updated (12 packages)
├── PROJECT_STATUS.md            ✅ this file
└── README.md                    ⚠️  needs update
```

---

## 🐛 Bugs Fixed in This Session

| Bug | File | Fix |
|-----|------|-----|
| `mean_squared_error(squared=False)` deprecated in new sklearn | `ml_model.py` | Changed to `np.sqrt(mean_squared_error(...))` |
| SQLAlchemy ORM objects returned directly as JSON (crashes) | `main.py` | Added `_hist_to_dict()` / `_pred_to_dict()` helpers |
| All forecast states always wiped when forecasting one state | `forecasting.py` | Scoped DELETE to `state_name + year.in_(...)` |
| `app/` missing `__init__.py` (import failures on some systems) | `app/__init__.py` | Created empty file |
| `uvicorn` missing `standard` extras (no websocket/static file support) | `requirements.txt` | Changed to `uvicorn[standard]` |
| `python-multipart` missing (FastAPI form/file handling broken) | `requirements.txt` | Added |
| `aiofiles` missing (StaticFiles would fail) | `requirements.txt` | Added |
