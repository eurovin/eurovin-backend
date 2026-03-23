from sqlalchemy import Column, Integer, String, Text, ForeignKey
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()

class Vehicle(Base):
    __tablename__ = "vehicles"
    id         = Column(Integer, primary_key=True, index=True)
    brand      = Column(String(100), index=True)
    model      = Column(String(100), index=True)
    generation = Column(String(100))
    years      = Column(String(50))
    issues     = relationship("Issue", back_populates="vehicle")

class Issue(Base):
    __tablename__ = "issues"
    id                   = Column(Integer, primary_key=True, index=True)
    vehicle_id           = Column(Integer, ForeignKey("vehicles.id"))
    system               = Column(String(50), index=True)
    title                = Column(String(200))
    description          = Column(Text)
    severity             = Column(String(20))
    affected_years       = Column(String(50))
    estimated_repair_cost = Column(String(100))
    vehicle              = relationship("Vehicle", back_populates="issues")
