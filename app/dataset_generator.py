"""
dataset_generator.py – Synthetic historical crime data for 29 Indian states.

Generates 15 years (2010–2024) with:
- No hard lower bound clamp; only floor at 80 for realism
- Gaussian noise (σ=5), state base multiplier (0.8–1.2), yearly shock (-3 to 3)
- Mild economic volatility in unemployment
- Logical correlation: +unemployment, +urbanization, -literacy, -police_strength
- Slightly randomized yearly coefficients to avoid perfectly smooth patterns
"""
from __future__ import annotations

import numpy as np
from sqlalchemy.orm import Session

from app.models import HistoricalCrimeData

STATES = [
    "Andhra Pradesh", "Telangana", "Tamil Nadu", "Karnataka",
    "Kerala", "Maharashtra", "Gujarat", "Rajasthan", "Uttar Pradesh",
    "Madhya Pradesh", "Bihar", "West Bengal", "Odisha", "Punjab",
    "Haryana", "Himachal Pradesh", "Uttarakhand", "Jharkhand",
    "Chhattisgarh", "Assam", "Tripura", "Meghalaya", "Manipur",
    "Mizoram", "Nagaland", "Sikkim", "Goa", "Arunachal Pradesh",
]

YEARS = list(range(2010, 2025))  # 2010 to 2024 (15 years)


def generate_synthetic_data(db: Session) -> dict:
    """
    Generate synthetic historical data for 29 states (2010–2024).
    No hard upper/lower clamp except crime_rate >= 80.
    """
    if db.query(HistoricalCrimeData).first():
        return {"message": "Data already exists in database. Use /reset-data to clear and reload."}

    rng = np.random.default_rng(42)
    records = []

    for state in STATES:
        # State base multiplier: random in [0.8, 1.2] for cross-state variation
        base_multiplier = float(rng.uniform(0.8, 1.2))

        base_pop_m = 1.5 + (hash(state) % 200) / 10.0
        base_pop = int(base_pop_m * 1_000_000)

        literacy = 60.0 + (hash(state) % 350) / 10.0
        literacy = float(np.clip(literacy, 62.0, 94.0))
        urbanization = 15.0 + (hash(state) % 450) / 10.0
        urbanization = float(np.clip(urbanization, 18.0, 62.0))
        unemployment = 3.0 + (hash(state) % 70) / 10.0
        unemployment = float(np.clip(unemployment, 3.0, 9.5))
        police = 80.0 + (hash(state) % 170)
        police = float(np.clip(police, 90.0, 250.0))

        prev_crime = None
        for i, year in enumerate(YEARS):
            # Yearly shock factor: random in [-3, 3]
            yearly_shock = float(rng.uniform(-3.0, 3.0))

            # Slightly randomized coefficients (avoid perfectly smooth formula)
            coef_unemp = 0.35 + rng.uniform(-0.05, 0.1)
            coef_urban = 0.18 + rng.uniform(-0.03, 0.05)
            coef_lit = -0.28 + rng.uniform(-0.05, 0.05)
            coef_police = -0.18 + rng.uniform(-0.04, 0.04)

            # Population: 1–2% annual growth
            growth = 1.0 + 0.01 + rng.uniform(0, 0.01)
            base_pop = int(base_pop * growth)
            base_pop = max(base_pop, 500_000)

            # Literacy: steady increase
            literacy = min(98.0, literacy + 0.5 + rng.normal(0, 0.1))
            literacy = round(float(literacy), 2)

            # Urbanization: gradual increase
            urbanization = min(92.0, urbanization + 0.6 + rng.normal(0, 0.15))
            urbanization = round(float(urbanization), 2)

            # Unemployment: mild economic volatility
            unemployment = unemployment + np.random.normal(0, 0.4)
            unemployment = float(np.clip(unemployment, 2.0, 11.0))
            unemployment = round(unemployment, 2)

            # Police strength: slight increase over time
            police = police + 0.5 + rng.normal(0, 1.0)
            police = float(np.clip(police, 60.0, 320.0))
            police = round(police, 2)

            # Logical correlation: +unemployment, +urbanization, -literacy, -police
            structural = (
                coef_unemp * unemployment * 10.0
                + coef_urban * urbanization * 2.0
                + coef_lit * (literacy / 100.0) * 70.0
                + coef_police * (police / 100.0) * 6.0
            )
            base_rate = 180.0 + structural

            # Mean-revert with previous year (mild)
            if prev_crime is not None:
                base_rate = 0.75 * prev_crime + 0.25 * base_rate

            # State base multiplier
            base_rate *= base_multiplier
            # Yearly shock
            base_rate += yearly_shock
            # Gaussian noise (σ=5)
            noise = np.random.normal(0, 5.0)
            crime_rate = base_rate + noise
            # Only floor: ensure crime never drops below 80 (no hard upper clamp)
            crime_rate = max(80.0, float(crime_rate))
            crime_rate = round(crime_rate, 2)
            prev_crime = crime_rate

            records.append(HistoricalCrimeData(
                state_name=state,
                year=year,
                population=base_pop,
                unemployment_rate=unemployment,
                literacy_rate=literacy,
                urbanization_rate=urbanization,
                police_strength_per_100k=police,
                crime_rate_per_100k=crime_rate,
            ))

    db.add_all(records)
    db.commit()
    return {"message": f"Successfully generated {len(records)} records for {len(STATES)} states (2010–2024)."}
