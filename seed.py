import json
import os
import sys
from dotenv import load_dotenv
from sqlalchemy.orm import Session
from database import engine, SessionLocal
from models import Base, Vehicle, Issue

load_dotenv()

def seed(json_path: str = "../eurovin-seeder/output/_all_issues.json"):
    print("Creating tables...")
    Base.metadata.create_all(bind=engine)

    if not os.path.exists(json_path):
        print(f"ERROR: Could not find {json_path}")
        print("Make sure the path to _all_issues.json is correct.")
        sys.exit(1)

    with open(json_path) as f:
        data = json.load(f)

    db: Session = SessionLocal()

    try:
        existing = db.query(Vehicle).count()
        if existing > 0:
            print(f"Database already has {existing} vehicles. Skipping seed.")
            print("To reseed, drop the tables first.")
            return

        print(f"Seeding {len(data)} entries...")
        vehicle_cache = {}
        total_issues = 0

        for entry in data:
            key = (entry["brand"], entry["model"], entry["generation"])

            if key not in vehicle_cache:
                vehicle = Vehicle(
                    brand=entry["brand"],
                    model=entry["model"],
                    generation=entry["generation"],
                    years=entry["years"]
                )
                db.add(vehicle)
                db.flush()
                vehicle_cache[key] = vehicle.id

            vehicle_id = vehicle_cache[key]

            for issue in entry.get("issues", []):
                db.add(Issue(
                    vehicle_id=vehicle_id,
                    system=entry["system"],
                    title=issue["title"],
                    description=issue["description"],
                    severity=issue["severity"],
                    affected_years=issue["affected_years"],
                    estimated_repair_cost=issue["estimated_repair_cost"]
                ))
                total_issues += 1

        db.commit()
        print(f"Seeded {len(vehicle_cache)} vehicles and {total_issues} issues successfully!")

    except Exception as e:
        db.rollback()
        print(f"Error: {e}")
        raise
    finally:
        db.close()

if __name__ == "__main__":
    path = sys.argv[1] if len(sys.argv) > 1 else "../eurovin-seeder/output/_all_issues.json"
    seed(path)
