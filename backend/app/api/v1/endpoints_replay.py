import os
from typing import Optional, Any
from pydantic import BaseModel, Field
from fastapi import APIRouter, HTTPException, UploadFile, File
from app.services.replay_service import replay_engine

router = APIRouter()


class ReplayControlRequest(BaseModel):
    action: str = Field(..., description="play, pause, seek, seek_pct, step, speed, load, unload")
    value: Optional[Any] = Field(default=None, description="Action parameter (e.g. frame index, speed multiplier, filename)")


@router.get("/replay/status")
def get_replay_status():
    """Returns the current trace replay status, active trace, and timeline cursor."""
    return replay_engine.get_status()


@router.post("/replay/control")
def control_replay(payload: ReplayControlRequest):
    """Executes playback actions (play, pause, seek, step, speed, load, unload)."""
    action = payload.action.lower()

    if action == "play":
        replay_engine.play()
    elif action == "pause":
        replay_engine.pause()
    elif action == "seek":
        if payload.value is None:
            raise HTTPException(status_code=400, detail="Missing value for seek")
        replay_engine.seek(int(payload.value))
    elif action == "seek_pct":
        if payload.value is None:
            raise HTTPException(status_code=400, detail="Missing value for seek_pct")
        replay_engine.seek_pct(float(payload.value))
    elif action == "step":
        step_val = int(payload.value) if payload.value is not None else 1
        replay_engine.step(step_val)
    elif action == "speed":
        if payload.value is None:
            raise HTTPException(status_code=400, detail="Missing value for speed")
        replay_engine.set_speed(float(payload.value))
    elif action == "load":
        if not payload.value:
            raise HTTPException(status_code=400, detail="Missing filename for load")
        try:
            return replay_engine.load_trace(str(payload.value))
        except FileNotFoundError as e:
            raise HTTPException(status_code=404, detail=str(e))
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to load trace: {str(e)}")
    elif action == "unload":
        replay_engine.unload_trace()
    else:
        raise HTTPException(status_code=400, detail=f"Unsupported action: {action}")

    return replay_engine.get_status()


@router.get("/replay/traces")
def list_traces():
    """Lists all available storage benchmark traces."""
    return replay_engine.list_available_traces()


@router.post("/replay/upload")
async def upload_trace(file: UploadFile = File(...)):
    """Uploads a new CSV or JSON storage trace to the traces library."""
    if not file.filename.endswith(".csv") and not file.filename.endswith(".json"):
        raise HTTPException(status_code=400, detail="Only .csv and .json traces are supported")

    dest_path = os.path.join(replay_engine.traces_dir, file.filename)
    try:
        content = await file.read()
        with open(dest_path, "wb") as f:
            f.write(content)
        # Attempt to load newly uploaded trace
        status = replay_engine.load_trace(file.filename)
        return {
            "message": f"Successfully uploaded and loaded trace: {file.filename}",
            "status": status
        }
    except Exception as e:
        if os.path.exists(dest_path):
            os.remove(dest_path)
        raise HTTPException(status_code=400, detail=f"Invalid trace format: {str(e)}")
