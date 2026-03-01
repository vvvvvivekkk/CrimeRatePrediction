    # Crime Rate Prediction System – India

    A full-stack web application built with **FastAPI**, **SQLite**, and **Scikit-learn / XGBoost** that forecasts crime rates across 29 Indian states using synthetic historical data.

    ---

    ## ✨ Features

    | Feature | Description |
    |---------|-------------|
    | 📦 Data Generation | 29 states × 15 years (2010–2024) synthetic dataset with realistic socioeconomic trends |
    | 🤖 ML Training | Linear Regression, Random Forest, XGBoost — best model (by R²) saved as `model.pkl` |
    | 🔮 Forecasting | 5- or 10-year crime rate predictions per state |
    | 🗺️ Choropleth Map | Leaflet.js interactive India state map, colour-coded by risk level |
    | 📊 Charts | Trend line (historical + dashed forecast), Top-5 bar, Risk doughnut, Feature importance, Crime growth % (Chart.js) |
    | 📄 PDF Reports | Per-state report with historical summary and forecast table |
    | 📥 CSV Exports | Download historical or predicted data as CSV |

    ---

    ## 🔧 Prerequisites

    - Python 3.9+
    - pip

    ---

    ## ⚡ Quick Start

    ```bash
    # 1 – Clone / navigate to the project root
    cd crime-rate-prediction

    # 2 – (Recommended) create a virtual environment
    python -m venv venv
    source venv/bin/activate        # Windows: venv\Scripts\activate

    # 3 – Install dependencies
    pip install -r requirements.txt

    # 4 – Start the development server
    uvicorn app.main:app --reload --port 8000
    ```

    Open your browser at **http://localhost:8000**

    ---

    ## 🖥️ Usage Workflow

    | Step | Action | Where | Result |
    |------|--------|--------|--------|
    | 1 | Click **Generate** | Home page | 435 rows inserted into SQLite |
    | 2 | Click **Train** | Home page | `model.pkl` saved; metrics shown |
    | 3 | Click **Open Dashboard →** | Home page | Dashboard opens |
    | 4 | *(auto)* or click **🔮 Generate Forecast** | Dashboard | All charts and map populate |
    | 5 | Select state → **Download PDF Report** | Dashboard | PDF downloaded |

    > **Tip:** The dashboard auto-generates a 5-year forecast if the predictions table is empty — no manual click required after training.

    ---

    ## 🌐 API Reference

    | Method | Endpoint | Description |
    |--------|----------|-------------|
    | `GET` | `/` | Landing page |
    | `GET` | `/dashboard` | Dashboard page |
    | `GET` | `/generate-data` | Generate synthetic dataset (29 states × 15 years) → SQLite |
    | `GET` | `/train` | Train 3 ML models, save best as `model.pkl` |
    | `GET` | `/predict?state=&years=` | Run forecast (all states if `state` omitted) |
    | `GET` | `/export-csv` | Download historical data as CSV |
    | `GET` | `/export-predictions-csv` | Download predicted data as CSV |
    | `GET` | `/report/{state}` | Download PDF report for a state |
    | `GET` | `/api/data/historical` | JSON — all historical records |
    | `GET` | `/api/data/predicted` | JSON — all predicted records |
    | `GET` | `/api/feature-importance` | JSON — feature importance from trained model (RF/XGB) |
    | `GET` | `/health` | JSON — DB record counts + model status |
    | `GET` | `/docs` | FastAPI interactive docs (Swagger UI) |

    ---

    ## 🤖 ML Details

    - **Features:** Population, Unemployment Rate, Literacy Rate, Urbanization Rate, Police Strength per 100k
    - **Target:** Crime Rate per 100k population
    - **Models:** Linear Regression · Random Forest · XGBoost
    - **Train/Test Split:** 2010–2020 train | 2021–2024 test (time-based)
    - **Evaluation:** R² Score, RMSE, MAE — best model auto-selected

    ---

    ## 📁 Project Structure

    ```
    crime-rate-prediction/
    │
    ├── app/
    │   ├── __init__.py
    │   ├── database.py          # SQLite via SQLAlchemy
    │   ├── models.py            # ORM models
    │   ├── schemas.py           # Pydantic schemas
    │   ├── dataset_generator.py # Synthetic data (29 states × 15 years)
    │   ├── preprocessing.py     # Feature scaling, train/test split
    │   ├── ml_model.py          # Train LR + RF + XGBoost, save best
    │   ├── forecasting.py       # Future crime rate predictions
    │   ├── report_generator.py  # PDF reports via reportlab
    │   └── main.py              # FastAPI routes
    │
    ├── static/
    │   ├── css/style.css        # Full dark-theme design system
    │   └── js/dashboard.js      # Leaflet map + Chart.js charts
    │
    ├── templates/
    │   ├── index.html           # Landing page
    │   └── dashboard.html       # Analytics dashboard
    │
    ├── requirements.txt
    └── README.md
    ```
