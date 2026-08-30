import io
from PyPDF2 import PdfReader

def extract_text_from_file(file_bytes: bytes, filename: str) -> str:
    """
    Extract text content from uploaded file bytes.
    Supports .txt and .pdf files.
    """
    if filename.lower().endswith(".pdf"):
        reader = PdfReader(io.BytesIO(file_bytes))
        text = ""
        for page in reader.pages:
            text += page.extract_text() + "\n"
        return text
    else:
        # Default to plain text file, ignoring/replacing strict encoding errors
        return file_bytes.decode("utf-8", errors="replace")

def chunk_text(text: str, chunk_size: int = 1000, overlap: int = 200) -> list[str]:
    """
    Split text into simple overlapping chunks.
    """
    chunks = []
    start = 0
    text_length = len(text)
    
    while start < text_length:
        end = start + chunk_size
        chunk = text[start:end]
        chunks.append(chunk)
        start += (chunk_size - overlap)
        
    return chunks
