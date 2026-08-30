# AI Knowledge Assistant

A full-stack **RAG (Retrieval-Augmented Generation) Knowledge Assistant** for uploading PDF/TXT documents and asking questions about their content. The application uses **React + Vite**, **FastAPI**, **Sentence Transformers**, a local **FAISS** vector index, and **Google Gemini**.

## Architecture

```text
React + Vite
     |
     v
FastAPI Backend
     |
     +--> PDF/TXT extraction
     |
     +--> Text chunking
     |
     +--> all-MiniLM-L6-v2 embeddings
     |
     +--> FAISS similarity search
     |
     +--> Gemini answer generation
     |
     v
Answer + source chunks
```

## Repository Structure

```text
ai-knowledge-assistant/
├── main.py              # FastAPI API
├── rag_pipeline.py      # RAG retrieval + Gemini generation
├── embeddings.py        # Sentence Transformer embeddings
├── utils.py             # PDF/TXT parsing and chunking
├── database.py          # Local FAISS vector index
├── requirements.txt     # Python dependencies
├── .env.example         # Environment variable template
├── run_instructions.txt # Local setup instructions
├── deployment_guide.md  # Deployment notes
├── test_api.py          # Basic API smoke test
└── frontend/            # React + Vite UI
    ├── package.json
    ├── src/
    │   ├── App.jsx
    │   ├── index.css
    │   └── main.jsx
    └── vite.config.js
```

## Features

- Upload `.pdf` and `.txt` documents
- Extract and chunk document text
- Generate 384-dimensional embeddings with `all-MiniLM-L6-v2`
- Store and search embeddings with local FAISS
- Retrieve the top relevant document chunks
- Generate grounded answers with Gemini
- Display source text and similarity scores
- React chat interface with dark/light theme

## Setup

### 1. Backend

Create and activate a virtual environment, then install dependencies:

```bash
python -m venv venv
```

Windows:
```bash
venv\Scripts\activate
```

macOS/Linux:
```bash
source venv/bin/activate
```

Install packages:

```bash
pip install -r requirements.txt
```

Copy `.env.example` to `.env` and add your Gemini API key:

```env
GEMINI_API_KEY=your_gemini_api_key_here
```

Run FastAPI:

```bash
uvicorn main:app --reload
```

Backend: `http://localhost:8000`
Swagger docs: `http://localhost:8000/docs`

### 2. Frontend

```bash
cd frontend
npm install
npm run dev
```

Frontend: `http://localhost:5173`

## RAG Workflow

1. User uploads a PDF or TXT file.
2. FastAPI extracts the text.
3. Text is divided into overlapping chunks.
4. Sentence Transformer converts chunks into embeddings.
5. FAISS stores the vectors in memory.
6. User submits a question.
7. The question is embedded and compared with stored vectors.
8. The top relevant chunks are selected.
9. Those chunks are supplied to Gemini as context.
10. The generated answer and source chunks are returned to React.

## Current Limitation

The FAISS index is currently **in memory**. Restarting the backend clears uploaded document vectors. Persistent storage can be added in the next development phase.
