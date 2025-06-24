import os
import httpx
import asyncio
from dotenv import load_dotenv
load_dotenv()

AZURE_OPENAI_ENDPOINT = os.environ.get("AZURE_OPENAI_ENDPOINT")
AZURE_OPENAI_KEY = os.environ.get("AZURE_OPENAI_KEY")
API_VERSION = os.environ.get("AZURE_OPENAI_API_VERSION", "preview")

HEADERS = {"api-key": AZURE_OPENAI_KEY, "Content-Type": "application/json"}

class AzureSoraService:
    @staticmethod
    async def create_video_job(prompt: str, duration: int, width: int = 480, height: int = 480):
        create_url = f"{AZURE_OPENAI_ENDPOINT}/openai/v1/video/generations/jobs?api-version={API_VERSION}"
        body = {
            "prompt": prompt,
            "width": width,
            "height": height,
            "n_seconds": duration,
            "model": "sora"
        }
        async with httpx.AsyncClient() as client:
            response = await client.post(create_url, headers=HEADERS, json=body)
            response.raise_for_status()
            return response.json()

    @staticmethod
    async def get_job_status(job_id: str):
        status_url = f"{AZURE_OPENAI_ENDPOINT}/openai/v1/video/generations/jobs/{job_id}?api-version={API_VERSION}"
        async with httpx.AsyncClient() as client:
            response = await client.get(status_url, headers=HEADERS)
            response.raise_for_status()
            return response.json()

    @staticmethod
    async def download_video(generation_id: str, output_path: str):
        video_url = f"{AZURE_OPENAI_ENDPOINT}/openai/v1/video/generations/{generation_id}/content/video?api-version={API_VERSION}"
        async with httpx.AsyncClient() as client:
            response = await client.get(video_url, headers=HEADERS)
            response.raise_for_status()
            with open(output_path, "wb") as f:
                f.write(response.content)
        return output_path
