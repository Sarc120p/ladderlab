from sqlalchemy import Column, Integer, String, DateTime, Text, JSON, func
from .database import Base

class Program(Base):
    __tablename__ = "programs"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), unique=True, nullable=False)
    description = Column(Text, nullable=True)
    content = Column(JSON, nullable=False)          # the Ladder JSON
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

class ExecutionLog(Base):
    __tablename__ = "execution_log"

    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime(timezone=True), nullable=False)
    event_type = Column(String(50), nullable=False)   # "alarm", "start", "stop", etc.
    severity = Column(String(20), nullable=True)       # "info", "warning", "critical"
    message = Column(Text, nullable=False)