# API Reference - Azure OpenAI Sora Video Generator

## Overview

The Azure OpenAI Sora Video Generator provides a REST API for programmatic video generation. This document provides detailed information about all available endpoints, request/response formats, and error handling.

## Base URL

```
http://localhost:8000/api
```

## Authentication

Currently, the API does not require authentication for local development. In production environments, implement appropriate authentication mechanisms.

## Content Type

All API endpoints accept and return JSON data unless otherwise specified.

```
Content-Type: application/json
```

## Rate Limiting

The API inherits rate limiting from the underlying Azure OpenAI service. Monitor your Azure quota and implement client-side rate limiting as needed.

## Endpoints

### Generate Video

Creates a new video generation job.

**Endpoint:** `POST /api/generate`

**Request Body:**

```json
{
  "prompt": "string",
  "duration": "integer (optional)",
  "width": "integer (optional)", 
  "height": "integer (optional)"
}
```

**Parameters:**

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| prompt | string | Yes | - | Natural language description of the video to generate |
| duration | integer | No | 10 | Video duration in seconds (1-60) |
| width | integer | No | 1920 | Video width in pixels |
| height | integer | No | 1080 | Video height in pixels |

**Example Request:**

```bash
curl -X POST "http://localhost:8000/api/generate" \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "A golden retriever playing in a sunny park",
    "duration": 15,
    "width": 1920,
    "height": 1080
  }'
```

**Response:**

```json
{
  "job_id": "01jyg74z6ee6e9y23ceq2fmwc4",
  "status": "queued"
}
```

**Response Fields:**

| Field | Type | Description |
|-------|------|-------------|
| job_id | string | Unique identifier for the generation job |
| status | string | Current job status: "queued", "processing", "completed", "failed" |

**Status Codes:**

- `200 OK` - Request successful
- `400 Bad Request` - Invalid request parameters
- `422 Unprocessable Entity` - Validation error
- `500 Internal Server Error` - Server error

---

### Check Job Status

Retrieves the current status of a video generation job.

**Endpoint:** `GET /api/status/{job_id}`

**Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| job_id | string | Yes | Job ID returned from generate endpoint |

**Example Request:**

```bash
curl -X GET "http://localhost:8000/api/status/01jyg74z6ee6e9y23ceq2fmwc4"
```

**Response (In Progress):**

```json
{
  "job_id": "01jyg74z6ee6e9y23ceq2fmwc4",
  "status": "processing"
}
```

**Response (Completed):**

```json
{
  "job_id": "01jyg74z6ee6e9y23ceq2fmwc4",
  "status": "completed",
  "video_url": "/api/download/gen_01jyg74z6ee6e9y23ceq2fmwc4"
}
```

**Response (Failed):**

```json
{
  "job_id": "01jyg74z6ee6e9y23ceq2fmwc4",
  "status": "failed",
  "error": "Content policy violation detected"
}
```

**Response Fields:**

| Field | Type | Description |
|-------|------|-------------|
| job_id | string | Job identifier |
| status | string | Current status: "queued", "processing", "completed", "failed" |
| video_url | string | Download URL (only when status is "completed") |
| error | string | Error message (only when status is "failed") |

**Status Codes:**

- `200 OK` - Request successful
- `404 Not Found` - Job ID not found
- `500 Internal Server Error` - Server error

---

### Download Video

Downloads a generated video file.

**Endpoint:** `GET /api/download/{file_id}`

**Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| file_id | string | Yes | File identifier from the video_url |

**Example Request:**

```bash
curl -X GET "http://localhost:8000/api/download/gen_01jyg74z6ee6e9y23ceq2fmwc4" \
  --output video.mp4
```

**Response:**

Returns the video file as binary data with appropriate headers:

```
Content-Type: video/mp4
Content-Disposition: attachment; filename="gen_01jyg74z6ee6e9y23ceq2fmwc4.mp4"
```

**Status Codes:**

- `200 OK` - File download successful
- `404 Not Found` - File not found
- `500 Internal Server Error` - Server error

---

## Data Models

### VideoGenerationRequest

```json
{
  "prompt": "string",
  "duration": "integer",
  "width": "integer",
  "height": "integer"
}
```

**Validation Rules:**

- `prompt`: Required, non-empty string, max 1000 characters
- `duration`: Optional, integer between 1 and 60
- `width`: Optional, integer between 256 and 4096
- `height`: Optional, integer between 256 and 4096

### VideoGenerationResponse

```json
{
  "job_id": "string",
  "status": "string",
  "video_url": "string",
  "error": "string"
}
```

**Field Descriptions:**

- `job_id`: Always present, unique job identifier
- `status`: Always present, current job status
- `video_url`: Present only when status is "completed"
- `error`: Present only when status is "failed"

## Status Values

| Status | Description |
|--------|-------------|
| queued | Job is waiting to be processed |
| processing | Video generation is in progress |
| completed | Video has been generated successfully |
| failed | Video generation failed |

## Error Handling

### Error Response Format

All error responses follow this format:

```json
{
  "detail": "Error description"
}
```

### Common Error Codes

**400 Bad Request**

```json
{
  "detail": "Invalid prompt: prompt cannot be empty"
}
```

**422 Unprocessable Entity**

```json
{
  "detail": [
    {
      "loc": ["body", "duration"],
      "msg": "ensure this value is greater than or equal to 1",
      "type": "value_error.number.not_ge",
      "ctx": {"limit_value": 1}
    }
  ]
}
```

**404 Not Found**

```json
{
  "detail": "Job not found"
}
```

**500 Internal Server Error**

```json
{
  "detail": "Azure OpenAI service is currently unavailable"
}
```

## Usage Examples

### JavaScript/Frontend Integration

```javascript
// Generate video
async function generateVideo(prompt, duration = 10) {
  try {
    const response = await fetch('/api/generate', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        prompt: prompt,
        duration: duration
      })
    });
    
    const data = await response.json();
    
    if (response.ok) {
      return data.job_id;
    } else {
      throw new Error(data.detail);
    }
  } catch (error) {
    console.error('Error generating video:', error);
    throw error;
  }
}

// Poll for status
async function pollJobStatus(jobId) {
  const response = await fetch(`/api/status/${jobId}`);
  const data = await response.json();
  
  if (response.ok) {
    return data;
  } else {
    throw new Error(data.detail);
  }
}

// Usage example
async function createVideo() {
  try {
    const jobId = await generateVideo("A cat playing with a ball");
    
    // Poll for completion
    let status = await pollJobStatus(jobId);
    
    while (status.status === 'queued' || status.status === 'processing') {
      await new Promise(resolve => setTimeout(resolve, 2000)); // Wait 2 seconds
      status = await pollJobStatus(jobId);
    }
    
    if (status.status === 'completed') {
      console.log('Video ready:', status.video_url);
    } else {
      console.error('Generation failed:', status.error);
    }
  } catch (error) {
    console.error('Error:', error);
  }
}
```

### Python Integration

```python
import httpx
import asyncio
import time

class VideoGeneratorClient:
    def __init__(self, base_url="http://localhost:8000/api"):
        self.base_url = base_url
        self.client = httpx.AsyncClient()
    
    async def generate_video(self, prompt, duration=10, width=1920, height=1080):
        """Generate a video from a prompt."""
        response = await self.client.post(
            f"{self.base_url}/generate",
            json={
                "prompt": prompt,
                "duration": duration,
                "width": width,
                "height": height
            }
        )
        response.raise_for_status()
        return response.json()
    
    async def get_status(self, job_id):
        """Check the status of a generation job."""
        response = await self.client.get(f"{self.base_url}/status/{job_id}")
        response.raise_for_status()
        return response.json()
    
    async def download_video(self, file_id, output_path):
        """Download a generated video."""
        response = await self.client.get(f"{self.base_url}/download/{file_id}")
        response.raise_for_status()
        
        with open(output_path, 'wb') as f:
            f.write(response.content)
    
    async def generate_and_wait(self, prompt, **kwargs):
        """Generate video and wait for completion."""
        # Start generation
        result = await self.generate_video(prompt, **kwargs)
        job_id = result["job_id"]
        
        # Poll for completion
        while True:
            status = await self.get_status(job_id)
            
            if status["status"] == "completed":
                return status
            elif status["status"] == "failed":
                raise Exception(f"Generation failed: {status.get('error')}")
            
            await asyncio.sleep(2)  # Wait 2 seconds before next poll

# Usage example
async def main():
    client = VideoGeneratorClient()
    
    try:
        result = await client.generate_and_wait(
            "A peaceful mountain lake at sunset"
        )
        
        # Extract file ID from video URL
        video_url = result["video_url"]
        file_id = video_url.split("/")[-1]
        
        # Download the video
        await client.download_video(file_id, "generated_video.mp4")
        print("Video downloaded successfully!")
        
    except Exception as e:
        print(f"Error: {e}")

# Run the example
asyncio.run(main())
```

### cURL Examples

**Generate Video:**

```bash
curl -X POST "http://localhost:8000/api/generate" \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "A bustling city street at night with neon lights",
    "duration": 20,
    "width": 1280,
    "height": 720
  }'
```

**Check Status:**

```bash
curl -X GET "http://localhost:8000/api/status/01jyg74z6ee6e9y23ceq2fmwc4"
```

**Download Video:**

```bash
curl -X GET "http://localhost:8000/api/download/gen_01jyg74z6ee6e9y23ceq2fmwc4" \
  --output my_video.mp4
```

## Interactive Documentation

The API provides interactive documentation through Swagger UI:

- **Swagger UI**: `http://localhost:8000/api/docs`
- **OpenAPI JSON**: `http://localhost:8000/openapi.json`

The Swagger UI allows you to:
- Explore all available endpoints
- Test API calls directly in the browser
- View request/response schemas
- Download OpenAPI specification

## Webhooks (Future Feature)

*Note: Webhooks are not currently implemented but may be added in future versions.*

Planned webhook functionality:
- Notification when video generation completes
- Status updates during processing
- Error notifications

## SDK and Libraries

Currently, no official SDKs are provided. The API is designed to be simple enough to integrate with standard HTTP libraries in any programming language.

Recommended libraries:
- **JavaScript**: fetch API, axios
- **Python**: httpx, requests
- **Node.js**: axios, node-fetch
- **PHP**: Guzzle, cURL
- **Java**: OkHttp, HttpClient
- **C#**: HttpClient

## Support and Issues

For API-related issues:

1. Check the interactive documentation at `/api/docs`
2. Verify your request format matches the examples
3. Check the application logs for detailed error information
4. Review the Azure OpenAI service status

---

*This API documentation is automatically generated from the OpenAPI specification and manually enhanced with examples and usage guidance.*
