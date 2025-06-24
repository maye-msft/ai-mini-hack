from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from app.api import video
import os

app = FastAPI(title="Azure OpenAI Sora Video Generation API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(video.router, prefix="/api")

# Mount static files at root
app.mount("/", StaticFiles(directory="app/static", html=True), name="static")

@app.get("/")
def root():
    return {"message": "Azure OpenAI Sora Video Generation API"}

@app.get("/api/docs", include_in_schema=False)
def custom_swagger_ui():
    # Serve the custom Swagger UI HTML from the doc directory
    return FileResponse(os.path.join(os.path.dirname(__file__), "../doc/swagger.html"))
