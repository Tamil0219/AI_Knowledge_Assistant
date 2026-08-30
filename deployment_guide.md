# Full-Stack Deployment Guide

This application has three main parts: the React frontend, FastAPI backend, and local FAISS vector index.

## 1. Backend

The backend can be deployed to a Python hosting platform such as Render or another service that supports FastAPI.

Build command:

```bash
pip install -r requirements.txt
```

Start command:

```bash
uvicorn main:app --host 0.0.0.0 --port $PORT
```

Environment variable:

```text
GEMINI_API_KEY=your_gemini_key
```

## 2. Frontend

The Vite React frontend can be deployed to Vercel or another static hosting platform.

```bash
npm install
npm run build
```

Update the backend API URL in `frontend/src/App.jsx` to use an environment variable for production.

## 3. Important Deployment Note

The current FAISS index is stored in memory. A backend restart clears the uploaded document vectors. For a production version, add persistent vector storage or save/load the FAISS index and metadata to durable storage.
