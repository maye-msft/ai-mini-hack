# Architecture Decision Record: Technology Stack

## Context

This project aims to build a simple web application for Video Generation with Azure OpenAI Sora. The application will have a backend API and a frontend SPA. The backend will interact with Azure OpenAI Sora and handle video generation, while the frontend will provide a user interface for input and video playback.

## Options Considered

### Backend
1. **Python (FastAPI)**
   - Pros: Modern, async, easy to use, good for prototyping, integrates well with AI/ML workflows, easy to run in a virtual environment.
   - Cons: Less mature ecosystem for video streaming than some other languages.
2. **Python (Flask)**
   - Pros: Simple, lightweight, familiar to many, easy to run in a virtual environment.
   - Cons: Less async support, less performant for concurrent requests.

### Frontend
1. **Vanilla JavaScript + HTML5 + CSS3**
   - Pros: No build step, easy to start, minimal dependencies, aligns with constraints.
   - Cons: No framework features, manual DOM management.
2. **React**
   - Pros: Component-based, scalable, large ecosystem.
   - Cons: More complex, adds build tooling, not required per constraints.

## Recommendation
- **Backend:** Python with FastAPI, running in a virtual environment.
- **Frontend:** Vanilla JavaScript, HTML5, and CSS3 (no framework).

## Rationale
- FastAPI is modern, async, and well-suited for rapid prototyping and AI integration.
- Vanilla JS/HTML/CSS keeps the frontend simple and dependency-free, as required.
- This stack is easy to test, maintain, and extend.

## Decision
- Use Python (FastAPI) for the backend API.
- Use vanilla JavaScript, HTML5, and CSS3 for the frontend SPA.

## Consequences
- Simple, maintainable codebase.
- Easy onboarding for contributors familiar with Python and basic web technologies.
- No advanced frontend features unless needed in the future.

---

*Decision confirmed by user on June 24, 2025.*
