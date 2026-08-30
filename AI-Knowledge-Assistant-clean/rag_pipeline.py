import os
from google import genai
from embeddings import get_embedding
from database import search_similar
from dotenv import load_dotenv

load_dotenv(override=True)

# Initialize Gemini Client
# Explicitly pulling from OS Env to dodge Uvicorn's parent env cache
try:
    api_key = os.getenv("GEMINI_API_KEY")
    gemini_client = genai.Client(api_key=api_key) if api_key else None
except Exception as e:
    gemini_client = None
    print(f"Warning: Could not initialize Gemini Client. Check your API key. Error: {e}")

def ask_question(query: str) -> dict:
    """
    Main RAG logic: 
    1. Embed query
    2. Search DB
    3. Generate prompt
    4. Call LLM (or mock)
    """
    try:
        # 1. Embed query
        query_vector = get_embedding(query)
        
        # 2. Search Top 3 relevant chunks
        results = search_similar(query_vector, top_k=3)
        
        if not results:
            return {"answer": "I don't have enough context in my database to answer this question.", "sources": []}

        # 3. Construct prompt with context
        context_parts = []
        sources = []
        
        for idx, item in enumerate(results):
            # Fallback handling just in case response format is object attributes instead of dictionary keys
            metadata = item.get("meta", {}) if isinstance(item, dict) else getattr(item, "meta", {})
            text = metadata.get("text", "")
            source = metadata.get("source", "Unknown")
            
            context_parts.append(f"--- Context {idx + 1} (Source: {source}) ---\n{text}\n")
            sources.append({"source": source, "text": text, "similarity": item.get('similarity', 0.0) if isinstance(item, dict) else getattr(item, "similarity", 0.0)})

        combined_context = "\n".join(context_parts)
        
        prompt = f"""You are a helpful knowledge assistant. Keep your answers concise and accurate.
Answer the user's question ONLY using the context provided below. 
If the context does not contain the answer, politely say you do not know.

{combined_context}

User's Question: {query}
"""

        # 4. Call Gemini Model or Fallback to Mock
        if not gemini_client:
            mock_response = f"*(Mock AI Response)*\n\nI am running in mock mode because my Gemini API Key is missing. However, I successfully searched the FAISS database! I found the context from your documents (see sources below). \n\nIf I were connected, I would summarize: **{combined_context[:100]}...**"
            return {
                "answer": mock_response,
                "sources": sources
            }

        response = gemini_client.models.generate_content(
            model='gemini-2.0-flash',
            contents=prompt
        )
        
        return {
            "answer": response.text,
            "sources": sources
        }
    except Exception as e:
        return {"error": str(e), "answer": "An error occurred during query processing."}
