"""
REST API routes for the LadderLab PLC simulator.
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from .database import get_session
from .models import Program, ExecutionLog
from engine.tags import get_all_tags

router = APIRouter()

# ---------------------------------------------------------------------------
# Program management
# ---------------------------------------------------------------------------

@router.get("/api/programs")
async def list_programs(session: AsyncSession = Depends(get_session)):
    """Return all saved programs (without the full content)."""
    result = await session.execute(
        select(Program).order_by(Program.updated_at.desc())
    )
    programs = result.scalars().all()
    return [
        {
            "id": p.id,
            "name": p.name,
            "description": p.description,
            "created_at": p.created_at.isoformat(),
            "updated_at": p.updated_at.isoformat() if p.updated_at else None,
        }
        for p in programs
    ]


@router.get("/api/programs/{program_id}")
async def get_program(program_id: int, session: AsyncSession = Depends(get_session)):
    """Return a single program including its full content."""
    result = await session.execute(select(Program).filter_by(id=program_id))
    program = result.scalar_one_or_none()
    if not program:
        raise HTTPException(status_code=404, detail="Program not found")
    return {
        "id": program.id,
        "name": program.name,
        "description": program.description,
        "content": program.content,
    }


@router.get("/api/program")
async def get_current_program(session: AsyncSession = Depends(get_session)):
    """Return the most recently saved program."""
    result = await session.execute(
        select(Program).order_by(Program.id.desc()).limit(1)
    )
    program = result.scalar_one_or_none()
    if not program:
        raise HTTPException(status_code=404, detail="No program loaded")
    return {"name": program.name, "content": program.content}


@router.post("/api/program")
async def load_program(payload: dict, session: AsyncSession = Depends(get_session)):
    """
    Load a Ladder program (JSON) and store it in the database.
    The payload can be the raw Ladder JSON (with "rungs") or a wrapper
    with optional "name", "description", and "content".
    """
    # Extract name and content from the payload
    name = payload.get("name", "Unnamed program")
    description = payload.get("description", "")
    content = payload.get("content") or payload   # direct rungs if no wrapper

    # Upsert: update existing program with the same name, or create new
    result = await session.execute(select(Program).filter_by(name=name))
    program = result.scalar_one_or_none()
    if program:
        program.content = content
        program.description = description
    else:
        program = Program(name=name, description=description, content=content)
        session.add(program)

    await session.commit()

    # Update the scan engine with the new program
    import backend.routes as routes_module
    scan_engine = routes_module.scan_engine
    if scan_engine:
        scan_engine.load_program(content)

    return {"status": "ok", "name": program.name, "id": program.id}


@router.delete("/api/programs/{program_id}")
async def delete_program(program_id: int, session: AsyncSession = Depends(get_session)):
    """Delete a saved program by its ID."""
    result = await session.execute(select(Program).filter_by(id=program_id))
    program = result.scalar_one_or_none()
    if not program:
        raise HTTPException(status_code=404, detail="Program not found")

    await session.delete(program)
    await session.commit()
    return {"status": "ok", "deleted_id": program_id}


# ---------------------------------------------------------------------------
# Event log (combining database + live alarm manager)
# ---------------------------------------------------------------------------

@router.get("/api/events")
async def get_events(session: AsyncSession = Depends(get_session)):
    """Return recent events from the database and the live alarm manager."""
    # Database events
    result = await session.execute(
        select(ExecutionLog).order_by(ExecutionLog.id.desc()).limit(50)
    )
    db_events = result.scalars().all()

    # Live events from the alarm manager (still in memory)
    import backend.routes as routes_module
    scan_engine = routes_module.scan_engine
    live_events = scan_engine.alarm_manager.get_recent(50) if scan_engine else []

    # Convert ORM objects to dictionaries
    db_dicts = [
        {
            "timestamp": e.timestamp.isoformat(),
            "type": e.event_type,
            "severity": e.severity,
            "message": e.message,
        }
        for e in db_events
    ]

    # Merge and sort by timestamp descending
    all_events = sorted(
        db_dicts + live_events,
        key=lambda x: x["timestamp"],
        reverse=True
    )
    return all_events[:50]


# ---------------------------------------------------------------------------
# Force digital input
# ---------------------------------------------------------------------------

@router.post("/api/inputs/{tag}")
async def force_input(tag: str, value: bool = Query(...)):
    """Force a digital input to a specific value."""
    import backend.routes as routes_module
    scan_engine = routes_module.scan_engine
    if scan_engine:
        scan_engine.force_input(tag, value)
    return {"status": "ok", "tag": tag, "value": value}


# ---------------------------------------------------------------------------
# Tags snapshot (for dashboard refresh)
# ---------------------------------------------------------------------------

@router.get("/api/tags")
async def get_tags():
    """Return the current state of all tags."""
    return get_all_tags()