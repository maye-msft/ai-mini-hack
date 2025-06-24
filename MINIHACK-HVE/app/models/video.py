from pydantic import BaseModel
from typing import Optional

class VideoGenerationRequest(BaseModel):
    prompt: str
    duration: int
    width: Optional[int] = 480
    height: Optional[int] = 480

class VideoGenerationResponse(BaseModel):
    job_id: str
    status: str
    video_url: Optional[str] = None
    error: Optional[str] = None
