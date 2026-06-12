"""
Pydantic models for request/response validation in the LadderLab API.
"""
from pydantic import BaseModel


class ForceInputRequest(BaseModel):
    """Request body for forcing a digital input."""
    tag: str
    value: bool


class LoadProgramRequest(BaseModel):
    """Request body for loading a new Ladder program."""
    rungs: list[dict]


class TagResponse(BaseModel):
    """Generic response for a single tag."""
    tag: str
    value: bool


class ProgramResponse(BaseModel):
    """Response for the currently loaded program."""
    rungs: list[dict]


class EventResponse(BaseModel):
    """Response for an event log entry."""
    timestamp: str
    type: str
    message: str