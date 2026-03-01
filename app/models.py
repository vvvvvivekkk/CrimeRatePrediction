from sqlalchemy import Column, Integer, String, Float
from app.database import Base

class HistoricalCrimeData(Base):
    __tablename__ = "historical_crime_data"

    id = Column(Integer, primary_key=True, index=True)
    state_name = Column(String, index=True)
    year = Column(Integer)
    population = Column(Integer)
    unemployment_rate = Column(Float)
    literacy_rate = Column(Float)
    urbanization_rate = Column(Float)
    police_strength_per_100k = Column(Float)
    crime_rate_per_100k = Column(Float)


class PredictedCrimeData(Base):
    __tablename__ = "predicted_crime_data"

    id = Column(Integer, primary_key=True, index=True)
    state_name = Column(String, index=True)
    year = Column(Integer)
    predicted_crime_rate = Column(Float)
    crime_level = Column(String)  # Low, Medium, High
