from fastapi import FastAPI, Depends, Query, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from sqlalchemy import func
from pydantic import BaseModel, field_validator
from typing import Optional
from database import get_db
from models import Vehicle, Issue
import re

app = FastAPI(title="EuroVin API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

class IssueOut(BaseModel):
    model_config = {"from_attributes": True}
    id: int
    system: str
    title: str
    description: str
    severity: str
    affected_years: str
    estimated_repair_cost: str
    prevalence: Optional[str] = "COMMON"
    risk_factors: Optional[str] = ""

    @field_validator("prevalence", mode="before")
    @classmethod
    def default_prevalence(cls, v):
        return v or "COMMON"

    @field_validator("risk_factors", mode="before")
    @classmethod
    def default_risk_factors(cls, v):
        return v or ""

class IssuesResponse(BaseModel):
    brand: str
    model: str
    year: int
    engine: str
    issues: list[IssueOut]

@app.get("/health")
def health():
    return {"status": "ok", "version": "1.0.0"}

@app.get("/issues", response_model=IssuesResponse)
def get_issues(
    brand:  str = Query(...),
    model:  str = Query(...),
    year:   int = Query(...),
    engine: str = Query(""),
    db: Session = Depends(get_db)
):
    vehicles = db.query(Vehicle).filter(
        func.lower(Vehicle.brand) == func.lower(brand),
        func.lower(Vehicle.model) == func.lower(model)
    ).all()

    if not vehicles:
        vehicles = db.query(Vehicle).filter(
            func.lower(Vehicle.brand) == func.lower(brand),
            func.lower(Vehicle.model).contains(func.lower(model))
        ).all()

    if not vehicles:
        raise HTTPException(status_code=404,
            detail=f"No data found for {brand} {model}. Check back as we expand our database.")

    best_vehicle = _best_match(vehicles, year)
    all_issues = db.query(Issue).filter(Issue.vehicle_id == best_vehicle.id).all()
    issues = [i for i in all_issues if _issue_applies(i.affected_years, year)]

    return IssuesResponse(
        brand=best_vehicle.brand,
        model=best_vehicle.model,
        year=year,
        engine=engine,
        issues=[IssueOut.model_validate(i) for i in issues]
    )

@app.get("/brands")
def get_brands(db: Session = Depends(get_db)):
    brands = db.query(Vehicle.brand).distinct().order_by(Vehicle.brand).all()
    return {"brands": [b[0] for b in brands]}

@app.get("/models")
def get_models(brand: str = Query(...), db: Session = Depends(get_db)):
    models = db.query(Vehicle.model, Vehicle.generation, Vehicle.years)\
        .filter(func.lower(Vehicle.brand) == func.lower(brand))\
        .distinct().order_by(Vehicle.model).all()
    return {"models": [{"model": m[0], "generation": m[1], "years": m[2]} for m in models]}

def _best_match(vehicles, year):
    for v in vehicles:
        try:
            parts = v.years.replace("present", "2026").split("-")
            start = int(parts[0].strip())
            end = int(parts[1].strip()) if len(parts) > 1 else 2026
            if start <= year <= end:
                return v
        except Exception:
            continue
    return vehicles[-1]

def _issue_applies(affected_years: str, year: int) -> bool:
    if not affected_years:
        return True
    text = affected_years.lower()
    if "all" in text:
        return True
    text = re.split(r'[;(]', text)[0]
    text = text.replace("present", "2026")
    years_found = [int(y) for y in re.findall(r'\b(19[0-9]{2}|20[0-3][0-9])\b', text)]
    if not years_found:
        return True
    if len(years_found) == 1:
        return year == years_found[0]
    for i in range(0, len(years_found) - 1, 2):
        if years_found[i] <= year <= years_found[i + 1]:
            return True
    return False
