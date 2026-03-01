from pydantic import BaseModel
from typing import Optional

class HistoricalCrimeBase(BaseModel):
    state_name: str
    year: int
    population: int
    unemployment_rate: float
    literacy_rate: float
    urbanization_rate: float
    police_strength_per_100k: float
    crime_rate_per_100k: float

class HistoricalCrimeCreate(HistoricalCrimeBase):
    pass

class HistoricalCrime(HistoricalCrimeBase):
    id: int

    class Config:
        orm_mode = True
        from_attributes = True

class PredictedCrimeBase(BaseModel):
    state_name: str
    year: int
    predicted_crime_rate: float
    crime_level: str

class PredictedCrimeCreate(PredictedCrimeBase):
    pass

class PredictedCrime(PredictedCrimeBase):
    id: int

    class Config:
        orm_mode = True
        from_attributes = True
