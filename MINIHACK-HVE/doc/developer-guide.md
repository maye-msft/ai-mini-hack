# Developer Documentation - Azure OpenAI Sora Video Generator

## Overview

This document provides comprehensive technical information for developers working on the Azure OpenAI Sora Video Generator application. The application is built using FastAPI for the backend, vanilla JavaScript for the frontend, and integrates with Azure OpenAI's Sora model for video generation.

## Architecture

### Technology Stack

- **Backend**: FastAPI (Python)
- **Frontend**: Vanilla JavaScript, HTML5, CSS3
- **AI Service**: Azure OpenAI Sora
- **Storage**: Local file system
- **API Documentation**: OpenAPI/Swagger

### System Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Web Browser   │    │   FastAPI App   │    │  Azure OpenAI   │
│                 │    │                 │    │     Sora        │
│  Frontend JS    │◄──►│  /api/generate  │◄──►│                 │
│  HTML/CSS       │    │  /api/status    │    │  Video Gen API  │
│                 │    │  /api/download  │    │                 │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                                │
                                ▼
                       ┌─────────────────┐
                       │  Local Storage  │
                       │  (app/storage)  │
                       └─────────────────┘
```

### Project Structure Deep Dive

```
app/
├── main.py                 # Application entry point and configuration
├── api/
│   └── video.py           # REST API endpoints for video operations
├── models/
│   └── video.py           # Pydantic models for request/response validation
├── services/
│   └── azure_sora.py      # Azure OpenAI integration service
├── static/                # Static web assets
│   ├── index.html         # Single-page application UI
│   ├── main.js            # Frontend application logic
│   └── style.css          # Application styling
└── storage/               # Generated video file storage
```

## Backend Components

### FastAPI Application (`app/main.py`)

The main application file configures:
- FastAPI instance with CORS middleware
- API router inclusion
- Static file serving
- Custom Swagger UI endpoint

Key configurations:
- CORS enabled for all origins (development setup)
- Static files mounted at root path
- API routes prefixed with `/api`

### API Layer (`app/api/video.py`)

#### Endpoints

**POST /api/generate**
- Accepts video generation requests
- Validates input using Pydantic models
- Initiates Azure Sora video generation
- Returns job ID for status tracking

**GET /api/status/{job_id}**
- Checks status of video generation job
- Returns current status and video URL when complete
- Handles job not found scenarios

**GET /api/download/{file_id}**
- Serves generated video files
- Validates file existence
- Returns video file with appropriate headers

#### Error Handling

All endpoints implement comprehensive error handling:
- Input validation errors (422)
- Service unavailable errors (503)
- Internal server errors (500)
- File not found errors (404)

### Data Models (`app/models/video.py`)

**VideoGenerationRequest**
```python
class VideoGenerationRequest(BaseModel):
    prompt: str
    duration: Optional[int] = 10
    width: Optional[int] = 1920
    height: Optional[int] = 1080
```

**VideoGenerationResponse**
```python
class VideoGenerationResponse(BaseModel):
    job_id: str
    status: str
    video_url: Optional[str] = None
    error: Optional[str] = None
```

### Azure Sora Service (`app/services/azure_sora.py`)

#### Core Methods

**create_video_job()**
- Sends generation request to Azure OpenAI
- Manages API authentication
- Handles rate limiting and retries
- Returns job information

**get_job_status()**
- Polls Azure OpenAI for job status
- Downloads completed videos
- Manages file storage
- Updates job tracking

**download_video()**
- Retrieves video from Azure OpenAI
- Saves to local storage
- Generates unique filenames
- Returns local file path

#### Configuration

Required environment variables:
```env
AZURE_OPENAI_API_KEY=your_api_key
AZURE_OPENAI_ENDPOINT=your_endpoint
AZURE_OPENAI_API_VERSION=2024-02-15-preview
```

## Frontend Components

### HTML Structure (`app/static/index.html`)

- Semantic HTML5 structure
- Responsive form design
- Video display container
- Status feedback elements

### JavaScript Logic (`app/static/main.js`)

#### Key Functions

**submitVideoRequest()**
- Collects form data
- Sends POST request to /api/generate
- Initiates status polling
- Handles submission errors

**pollJobStatus()**
- Polls /api/status endpoint
- Updates UI with progress
- Handles completion and errors
- Manages polling intervals

**displayVideo()**
- Creates video element
- Sets video source
- Adds download functionality
- Updates UI state

#### State Management

- Form validation and user feedback
- Progress indication during generation
- Error message display
- Video playback controls

### Styling (`app/static/style.css`)

- Mobile-first responsive design
- Clean, modern interface
- Accessible color scheme
- Loading and status indicators

## Development Setup

### Environment Setup

1. **Python Environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # macOS/Linux
   pip install -r requirements.txt
   ```

2. **Environment Variables**
   ```bash
   cp .env.example .env
   # Edit .env with your Azure credentials
   ```

3. **Development Server**
   ```bash
   uvicorn app.main:app --reload --log-level debug
   ```

### Testing

#### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=app tests/

# Run specific test file
pytest tests/test_api_video.py

# Run with verbose output
pytest -v
```

#### Test Structure

```
tests/
├── test_api_video.py              # API endpoint tests
├── test_api_video_integration.py  # Integration tests
└── conftest.py                    # Test configuration (if needed)
```

#### Writing Tests

Example test structure:
```python
import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_generate_video():
    response = client.post("/api/generate", json={
        "prompt": "A cat playing with a ball"
    })
    assert response.status_code == 200
    assert "job_id" in response.json()
```

### Code Quality

#### Linting and Formatting

```bash
# Install development tools
pip install black flake8 isort

# Format code
black app/ tests/

# Sort imports
isort app/ tests/

# Check linting
flake8 app/ tests/
```

#### Pre-commit Hooks

```bash
pip install pre-commit
pre-commit install
```

## API Integration

### Azure OpenAI Sora Integration

#### Authentication

```python
headers = {
    "Authorization": f"Bearer {api_key}",
    "Content-Type": "application/json"
}
```

#### Video Generation Request

```python
payload = {
    "model": "sora",
    "prompt": prompt,
    "duration": duration,
    "size": f"{width}x{height}"
}

response = await httpx.post(
    f"{endpoint}/openai/deployments/{deployment}/videos/generations",
    headers=headers,
    json=payload
)
```

#### Status Polling

```python
status_response = await httpx.get(
    f"{endpoint}/openai/deployments/{deployment}/videos/generations/{job_id}",
    headers=headers
)
```

### Error Handling

#### Common Error Scenarios

1. **Rate Limiting**
   - Implement exponential backoff
   - Respect rate limit headers
   - Queue requests when necessary

2. **Authentication Errors**
   - Validate API key format
   - Handle token expiration
   - Provide clear error messages

3. **Generation Failures**
   - Parse Azure error responses
   - Provide user-friendly messages
   - Implement retry logic

## Deployment

### Production Configuration

1. **Environment Variables**
   ```env
   AZURE_OPENAI_API_KEY=prod_key
   AZURE_OPENAI_ENDPOINT=prod_endpoint
   ENVIRONMENT=production
   LOG_LEVEL=info
   ```

2. **Security Considerations**
   - Remove CORS wildcard
   - Implement rate limiting
   - Add input sanitization
   - Set up proper logging

3. **Performance Optimization**
   - Configure uvicorn workers
   - Implement caching
   - Optimize file serving
   - Monitor resource usage

### Docker Deployment

```dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY app/ ./app/
COPY doc/ ./doc/

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### Health Checks

```python
@app.get("/health")
def health_check():
    return {"status": "healthy", "timestamp": datetime.utcnow()}
```

## Monitoring and Logging

### Logging Configuration

```python
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger("azure_sora_app")
```

### Key Metrics to Monitor

- Video generation success rate
- Average generation time
- API response times
- Error rates by endpoint
- Storage usage

### Debugging Tips

1. **Enable Debug Logging**
   ```bash
   LOG_LEVEL=debug uvicorn app.main:app --reload
   ```

2. **Check Azure API Responses**
   - Log request/response payloads
   - Monitor API quota usage
   - Track generation job states

3. **Frontend Debugging**
   - Use browser developer tools
   - Check network requests
   - Monitor console errors

## Security Considerations

### Input Validation

- Sanitize user prompts
- Validate file uploads
- Limit request sizes
- Implement rate limiting

### API Security

- Secure API key storage
- Implement HTTPS only
- Add request signing
- Monitor for abuse

### Content Safety

- Filter inappropriate prompts
- Implement content moderation
- Log generation requests
- Respect usage policies

## Performance Optimization

### Backend Optimizations

- Async request handling
- Connection pooling
- Response caching
- Database indexing (if implemented)

### Frontend Optimizations

- Minimize JavaScript bundle
- Optimize image assets
- Implement lazy loading
- Cache static resources

### Azure API Optimization

- Batch requests when possible
- Implement smart retry logic
- Monitor quota usage
- Optimize prompt engineering

## Contributing

### Development Workflow

1. Fork the repository
2. Create feature branch: `git checkout -b feature/new-feature`
3. Write tests for new functionality
4. Implement changes
5. Run tests: `pytest`
6. Update documentation
7. Submit pull request

### Code Style Guidelines

- Follow PEP 8 for Python code
- Use meaningful variable names
- Write docstrings for functions
- Keep functions focused and small
- Add type hints where appropriate

### Git Conventions

- Use conventional commit messages
- Keep commits atomic
- Write clear commit descriptions
- Reference issues in commits

## Troubleshooting

### Common Development Issues

1. **Import Errors**
   - Check virtual environment activation
   - Verify package installation
   - Check Python path

2. **API Connection Issues**
   - Verify environment variables
   - Check network connectivity
   - Validate API credentials

3. **Frontend Issues**
   - Clear browser cache
   - Check browser console
   - Verify API endpoints

### Production Issues

1. **Performance Problems**
   - Monitor resource usage
   - Check database queries
   - Profile slow endpoints

2. **Video Generation Failures**
   - Check Azure API status
   - Verify quota limits
   - Review error logs

## Resources

### Documentation Links

- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [Azure OpenAI Documentation](https://docs.microsoft.com/en-us/azure/cognitive-services/openai/)
- [Pydantic Documentation](https://pydantic-docs.helpmanual.io/)

### Useful Tools

- **API Testing**: Postman, curl, httpie
- **Database**: DB Browser for SQLite
- **Monitoring**: Prometheus, Grafana
- **Logging**: ELK Stack, Fluentd

---

*This documentation is maintained by the development team. Please keep it updated with any significant changes to the codebase.*
