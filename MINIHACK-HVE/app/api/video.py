from fastapi import APIRouter, HTTPException
from app.models.video import VideoGenerationRequest, VideoGenerationResponse
from app.services.azure_sora import AzureSoraService
import os
import uuid
import logging
from fastapi.responses import FileResponse

router = APIRouter()

logger = logging.getLogger("api.video")

@router.post("/generate", response_model=VideoGenerationResponse)
async def generate_video(request: VideoGenerationRequest):
    try:
        job = await AzureSoraService.create_video_job(
            prompt=request.prompt,
            duration=request.duration,
            width=request.width,
            height=request.height
        )
        return VideoGenerationResponse(job_id=job["id"], status=job["status"])
    except Exception as e:
        logger.error(f"Error in /generate: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/status/{job_id}", response_model=VideoGenerationResponse)
async def get_status(job_id: str):
    try:
        status = await AzureSoraService.get_job_status(job_id)
        resp = VideoGenerationResponse(
            job_id=job_id,
            status=status.get("status"),
        )
        if status.get("status") == "succeeded":
            generations = status.get("generations", [])
            if generations:
                resp.video_url = f"/api/video/{generations[0]['id']}"
        return resp
    except Exception as e:
        logger.error(f"Error in /status/{{job_id}}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/video/{generation_id}")
async def get_video(generation_id: str):
    try:
        output_path = os.path.join("app/storage", f"{generation_id}.mp4")
        if not os.path.exists(output_path):
            await AzureSoraService.download_video(generation_id, output_path)
        return FileResponse(output_path, media_type="video/mp4")
    except Exception as e:
        logger.error(f"Error in /video/{{generation_id}}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
