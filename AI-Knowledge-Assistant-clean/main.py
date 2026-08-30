from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from database import init_db, upsert_documents
from utils import extract_text_from_file, chunk_text
from embeddings import get_embedding
from rag_pipeline import ask_question

app = FastAPI(
    title="AI Knowledge Assistant",
    description="Backend API for a local FAISS-powered RAG knowledge assistant with Gemini",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

class QueryRequest(BaseModel):
    query: str

@app.get("/")
def read_root():
    return {"message": "Welcome to AI Knowledge Assistant Backend"}

@app.post("/upload")
async def upload_document(file: UploadFile = File(...)):
    """
    Upload a document (.txt or .pdf), process into embeddings, 
    and store them in the local FAISS vector index.
    """
    if not file.filename.endswith(('.txt', '.pdf')):
        raise HTTPException(status_code=400, detail="Only .txt and .pdf files are supported")
    
    try:
        # Read file contents
        content = await file.read()
        
        # Extract text
        text = extract_text_from_file(content, file.filename)
        if not text.strip():
            raise HTTPException(status_code=400, detail="Could not extract text from document.")
            
        # Chunk text
        chunks = chunk_text(text, chunk_size=800, overlap=150)
        
        # Generate embeddings in batch
        embeddings_list = [get_embedding(chunk) for chunk in chunks]
        
        # Store vectors in the local FAISS index
        upsert_documents(chunks, embeddings_list, file.filename)
        
        return {
            "message": "File processed and stored successfully", 
            "filename": file.filename, 
            "chunks_created": len(chunks)
        }
        
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Database or Infrastructure Error: {str(e)}")

@app.post("/ask")
async def ask_knowledge(request: QueryRequest):
    """
    Ask a question against the stored knowledge.
    """
    if not request.query.strip():
        raise HTTPException(status_code=400, detail="Query cannot be empty")
        
    try:
        result = ask_question(request.query)
        if "error" in result:
            raise Exception(result["error"])
        return result
    except Exception as e:
        import traceback
        with open("ask_dump.txt", "w") as f:
            f.write(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))
