"""
dataset_generator.py – Synthetic historical crime data for 29 Indian states.

Generates 15 years (2010–2024) with:
- Population growth ~1–2% annually
- Literacy growth steady
- Unemployment realistic fluctuation
- Crime rate in realistic range 120–350 per 100k
- Formula: crime_rate = (0.4*unemployment) + (0.2*urbanization) - (0.3*literacy) - (0.2*police_strength) + noise
- State-level base multipliers for variation
- Gaussian noise, no extreme spikes
"""
from __future__ import annotations

import numpy as np
from sqlalchemy.orm import Session

from app.models import HistoricalCrimeData

# 29 Indian states per spec (no Delhi/UTs)
STATES = [
    "Andhra Pradesh", "Telangana", "Tamil Nadu", "Karnataka",
    "Kerala", "Maharashtra", "Gujarat", "Rajasthan", "Uttar Pradesh",
    "Madhya Pradesh", "Bihar", "West Bengal", "Odisha", "Punjab",
    "Haryana", "Himachal Pradesh", "Uttarakhand", "Jharkhand",
    "Chhattisgarh", "Assam", "Tripura", "Meghalaya", "Manipur",
    "Mizoram", "Nagaland", "Sikkim", "Goa", "Arunachal Pradesh",
]

YEARS = list(range(2010, 2025))  # 2010 to 2024 (15 years)

# State-level base multipliers (relative to national avg) for realistic variation.
# Crime rate base ~180; multiplier 0.85–1.25 keeps final rate in 120–350 range.
STATE_CRIME_MULTIPLIERS = {
    "Andhra Pradesh": 1.02, "Telangana": 1.05, "Tamil Nadu": 1.08, "Karnataka": 1.06,
    "Kerala": 1.12, "Maharashtra": 1.04, "Gujarat": 0.88, "Rajasthan": 1.10,
    "Uttar Pradesh": 1.00, "Madhya Pradesh": 1.18, "Bihar": 0.92, "West Bengal": 1.02,
    "Odisha": 1.04, "Punjab": 1.00, "Haryana": 1.08, "Himachal Pradesh": 0.92,
    "Uttarakhand": 0.98, "Jharkhand": 1.02, "Chhattisgarh": 1.12,
    "Assam": 0.98, "Tripura": 0.95, "Meghalaya": 0.88, "Manipur": 0.82,
    "Mizoram": 0.88, "Nagaland": 0.80, "Sikkim": 0.85, "Goa": 1.05,
    "Arunachal Pradesh": 0.90,
}


def generate_synthetic_data(db: Session) -> dict:
    """
    Generate synthetic historical data for 29 states (2010–2024).
    Uses spec formula with realistic ranges and state multipliers.
    """
    if db.query(HistoricalCrimeData).first():
        return {"message": "Data already exists in database. Use /reset-data to clear and reload."}

    rng = np.random.default_rng(42)
    records = []

    for state in STATES:
        mult = STATE_CRIME_MULTIPLIERS.get(state, 1.0)
        # Base population in millions (realistic for Indian states)
        base_pop_m = 1.5 + (hash(state) % 200) / 10.0  # 1.5–21 M range
        base_pop = int(base_pop_m * 1_000_000)

        # Base socioeconomic (2010 levels) – realistic ranges
        literacy = 60.0 + (hash(state) % 350) / 10.0   # 60–95
        literacy = float(np.clip(literacy, 62.0, 94.0))
        urbanization = 15.0 + (hash(state) % 450) / 10.0  # 15–60
        urbanization = float(np.clip(urbanization, 18.0, 62.0))
        unemployment = 3.0 + (hash(state) % 70) / 10.0   # 3–10
        unemployment = float(np.clip(unemployment, 3.0, 9.5))
        police = 80.0 + (hash(state) % 170)               # 80–250
        police = float(np.clip(police, 90.0, 250.0))

        prev_crime = None
        for i, year in enumerate(YEARS):
            year_factor = i  # 0..14

            # Population: 1–2% annual growth
            growth = 1.0 + 0.01 + rng.uniform(0, 0.01)  # ~1–2%
            base_pop = int(base_pop * growth)
            base_pop = max(base_pop, 500_000)

            # Literacy: steady increase (~0.4–0.6% per year)
            literacy = min(98.0, literacy + 0.5 + rng.normal(0, 0.1))
            literacy = round(float(literacy), 2)

            # Urbanization: gradual increase
            urbanization = min(92.0, urbanization + 0.6 + rng.normal(0, 0.15))
            urbanization = round(float(urbanization), 2)

            # Unemployment: realistic fluctuation (no extreme spikes)
            unemployment = unemployment + rng.normal(0, 0.35)
            unemployment = float(np.clip(unemployment, 2.0, 11.0))
            unemployment = round(unemployment, 2)

            # Police strength: slight increase over time
            police = police + 0.5 + rng.normal(0, 1.0)
            police = float(np.clip(police, 60.0, 320.0))
            police = round(police, 2)

            # Spec formula (scaled to get rate in 120–350): 
            # crime_rate = (0.4*unemployment) + (0.2*urbanization) - (0.3*literacy) - (0.2*police_strength) + noise
            # Scale factors to land in ~150–250 before multiplier and noise
            structural = (
                0.4 * unemployment * 12.0
                + 0.2 * urbanization * 2.0
                - 0.3 * (literacy / 100.0) * 80.0
                - 0.2 * (police / 100.0) * 8.0
            )
            base_rate = 200.0 + structural
            # Mean-revert with previous year for smooth series
            if prev_crime is not None:
                base_rate = 0.7 * prev_crime + 0.3 * base_rate
            # State multiplier
            base_rate *= mult
            # Gaussian noise (no spikes)
            noise = rng.normal(0, 8.0)
            crime_rate = base_rate + noise
            crime_rate = float(np.clip(crime_rate, 120.0, 350.0))
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
