# CV-Job Matching System

A state-of-the-art platform for parsing CVs and matching them with job descriptions using AI/ML.

## Features
- **CV Parsing**: Extracts structured data from PDF resumes using LLMs.
- **Job Matching**: Semantically matches CVs to job descriptions.
- **Streaming API**: Real-time updates on parsing and matching progress via WebSockets.
- **Research Friendly**: Jupyter notebooks for experimenting with parsers and matchers.
- **Production Ready**: Docker and Kubernetes configurations included.

## Setup

### Prerequisites
- Python 3.10+
- Docker & Docker Compose
- Ollama (for local LLMs)

### Installation
1. Clone the repository.
2. Install dependencies:
   ```bash
   pip install .
   ```

### Running the Application
1. Start the infrastructure (Postgres + pgvector):
   ```bash
   docker-compose -f infra/docker-compose.yml up -d
   ```
2. Start the API:
   ```bash
   uvicorn api.main:app --reload
   ```
3. Open `http://localhost:8000/static/index.html` to test the UI.

### Research
Run Jupyter notebooks:
```bash
jupyter notebook research/
```

## Architecture
- **API**: FastAPI
- **Core**: LangChain, LangGraph
- **Database**: PostgreSQL + pgvector
- **LLM**: Ollama (Llama 3 recommended)

## Bibliography
See `latex/bibliography.bib` for references.
