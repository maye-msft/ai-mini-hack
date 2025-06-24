# Azure OpenAI Sora Video Generation Web Application

A simple web application for generating videos using Azure OpenAI Sora. This application provides a clean, intuitive interface for users to create videos from natural language prompts.

## Features

- **Simple Web Interface**: Clean, responsive UI for video generation
- **Natural Language Prompts**: Generate videos using descriptive text prompts
- **Real-time Status Updates**: Track video generation progress with live status polling
- **Video Preview & Download**: View generated videos directly in the browser or download them
- **Azure OpenAI Sora Integration**: Powered by cutting-edge AI video generation technology

## Quick Start

### Prerequisites

- Python 3.8+ 
- Azure OpenAI API access with Sora model enabled
- Virtual environment (recommended)

### Installation

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd MINIHACK-HVE
   ```

2. **Create and activate virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On macOS/Linux
   # or
   venv\Scripts\activate     # On Windows
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Set up environment variables**
   Create a `.env` file in the root directory:
   ```env
   AZURE_OPENAI_API_KEY=your_api_key_here
   AZURE_OPENAI_ENDPOINT=your_endpoint_here
   AZURE_OPENAI_API_VERSION=2024-02-15-preview
   ```

5. **Run the application**
   ```bash
   uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
   ```

6. **Access the application**
   Open your browser and navigate to: `http://localhost:8000`

## Usage

1. **Enter a Prompt**: Describe the video you want to generate in natural language
2. **Set Parameters**: Configure duration, width, and height (optional)
3. **Generate**: Click the generate button to start video creation
4. **Monitor Progress**: Watch real-time status updates during generation
5. **View Result**: Preview and download your generated video

## Project Structure

```
├── app/
│   ├── main.py                 # FastAPI application entry point
│   ├── api/
│   │   └── video.py           # Video generation API endpoints
│   ├── models/
│   │   └── video.py           # Pydantic models for requests/responses
│   ├── services/
│   │   └── azure_sora.py      # Azure OpenAI Sora service integration
│   ├── static/                # Frontend files
│   │   ├── index.html         # Main web interface
│   │   ├── main.js            # Frontend JavaScript logic
│   │   └── style.css          # Application styling
│   └── storage/               # Generated video storage
├── doc/                       # Documentation
├── tests/                     # Test files
├── userstories/              # Project user stories
├── requirements.txt          # Python dependencies
└── README.md                 # This file
```

## API Documentation

The application provides a REST API for video generation. Access the interactive API documentation at:
- Swagger UI: `http://localhost:8000/api/docs`
- OpenAPI JSON: `http://localhost:8000/openapi.json`

### Key Endpoints

- `POST /api/generate` - Start video generation
- `GET /api/status/{job_id}` - Check generation status  
- `GET /api/download/{file_id}` - Download generated video

## Development

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=app tests/
```

### Development Setup

```bash
# Install development dependencies
pip install pytest pytest-cov

# Run in development mode
uvicorn app.main:app --reload --log-level debug
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Ensure all tests pass
6. Submit a pull request

## Support

For issues and questions:
- Check the [documentation](./doc/)
- Review existing [issues](issues)
- Create a new issue if needed

## License

This project is licensed under the MIT License - see the LICENSE file for details.
