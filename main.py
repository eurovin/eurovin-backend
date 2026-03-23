from fastapi import FastAPI, Depends, Query, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import Optional
from pydantic import BaseModel
from database import get_db
from models import Vehicle, Issue
import os

app = FastAPI(title="EuroVin API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Response models ───────────────────────────────────────────────────────────

class IssueOut(BaseModel):
    id: int
    system: str
    title: str
    description: str
    severity: str
    affected_years: str
    estimated_repair_cost: str

    class Config:
        from_attributes = True

class IssuesResponse(BaseModel):
    brand: str
    model: str
    year: int
    engine: str
    issues: list[IssueOut]

# ── Endpoints ─────────────────────────────────────────────────────────────────

@app.get("/health")
def health():
    return {"status": "ok", "version": "1.0.0"}

@app.get("/issues", response_model=IssuesResponse)
def get_issues(
    brand:  str = Query(..., description="Vehicle brand e.g. BMW"),
    model:  str = Query(..., description="Vehicle model e.g. 3 Series"),
    year:   int = Query(..., description="Model year e.g. 2013"),
    engine: str = Query("", description="Engine code e.g. N55"),
    db: Session = Depends(get_db)
):
    # Find the best matching vehicle
    # First try exact brand + model match, then find the generation whose year range contains the target year
    vehicles = db.query(Vehicle).filter(
        func.lower(Vehicle.brand) == func.lower(brand),
        func.lower(Vehicle.model) == func.lower(model)
    ).all()

    if not vehicles:
        # Try partial model match
        vehicles = db.query(Vehicle).filter(
            func.lower(Vehicle.brand) == func.lower(brand),
            func.lower(Vehicle.model).contains(func.lower(model))
        ).all()

    if not vehicles:
        raise HTTPException(
            status_code=404,
            detail=f"No data found for {brand} {model}. Check back as we expand our database."
        )

    # Pick the vehicle whose year range best matches the requested year
    best_vehicle = _best_match(vehicles, year)

    # Fetch all issues for this vehicle
    issues = db.query(Issue).filter(Issue.vehicle_id == best_vehicle.id).all()

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

# ── Helpers ───────────────────────────────────────────────────────────────────

def _best_match(vehicles: list, year: int) -> Vehicle:
    """Pick the vehicle generation whose year range best contains the target year."""
    for v in vehicles:
        try:
            parts = v.years.replace("present", "2026").split("-")
            start = int(parts[0].strip())
            end   = int(parts[1].strip()) if len(parts) > 1 else 2026
            if start <= year <= end:
                return v
        except Exception:
            continue
    # Fallback: return the most recent generation
    return vehicles[-1]
