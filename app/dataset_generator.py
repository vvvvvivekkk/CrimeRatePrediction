import pandas as pd
import numpy as np
from sqlalchemy.orm import Session
from app.models import HistoricalCrimeData

# List of 29 Indian States
STATES = [
    "Andhra Pradesh", "Telangana", "Tamil Nadu", "Karnataka",
    "Kerala", "Maharashtra", "Gujarat", "Rajasthan", "Uttar Pradesh",
    "Madhya Pradesh", "Bihar", "West Bengal", "Odisha", "Punjab",
    "Haryana", "Himachal Pradesh", "Uttarakhand", "Jharkhand",
    "Chhattisgarh", "Assam", "Tripura", "Meghalaya", "Manipur",
    "Mizoram", "Nagaland", "Sikkim", "Goa", "Arunachal Pradesh"
]

YEARS = list(range(2010, 2025))  # 2010 to 2024 (15 years)

def generate_synthetic_data(db: Session):
    # Check if data already exists
    if db.query(HistoricalCrimeData).first():
        return {"message": "Data already exists in database."}

    records = []
    
    # Base values for states to create some variation
    state_base_stats = {}
    for state in STATES:
        state_base_stats[state] = {
            "population": np.random.randint(1_000_000, 200_000_000),
            "unemployment": np.random.uniform(3.0, 10.0),
            "literacy": np.random.uniform(60.0, 95.0),
            "urbanization": np.random.uniform(20.0, 60.0),
            "police": np.random.uniform(100.0, 250.0)
        }

    for year in YEARS:
        for state in STATES:
            base = state_base_stats[state]
            
            # Trends over years
            year_factor = year - 2010
            
            pop = int(base["population"] * (1 + 0.015 * year_factor)) # 1.5% pop growth
            literacy = min(99.0, base["literacy"] + (0.5 * year_factor)) # Literacy increases
            unemployment = max(2.0, base["unemployment"] + np.random.normal(0, 0.5)) # Fluctuates
            urbanization = min(90.0, base["urbanization"] + (1.0 * year_factor)) # Increasing urbanization
            police = max(50.0, base["police"] + np.random.normal(1, 2)) # Slight increase/fluctuation

            # Crime rate formula
            # crime_rate = (0.4 * unemployment) + (0.2 * urbanization) - (0.3 * literacy) - (0.2 * police_strength) + random noise
            noise = np.random.normal(0, 10)
            crime_rate = (0.4 * unemployment * 10) + (0.2 * urbanization * 5) - (0.3 * literacy * 2) - (0.2 * police) + 200 + noise
            crime_rate = max(10.0, crime_rate) # Ensure positive

            record = HistoricalCrimeData(
                state_name=state,
                year=year,
                population=pop,
                unemployment_rate=round(unemployment, 2),
                literacy_rate=round(literacy, 2),
                urbanization_rate=round(urbanization, 2),
                police_strength_per_100k=round(police, 2),
                crime_rate_per_100k=round(crime_rate, 2)
            )
            records.append(record)

            # Update base for next year's starting point (fluctuating variables)
            state_base_stats[state]["unemployment"] = unemployment
            state_base_stats[state]["police"] = police

    db.add_all(records)
    db.commit()

    return {"message": f"Successfully generated {len(records)} records for 29 states."}
