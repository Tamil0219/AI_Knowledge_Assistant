from sentence_transformers import SentenceTransformer

# Load the model once when the module is imported
# all-MiniLM-L6-v2 outputs 384-dimensional embeddings
model = SentenceTransformer("all-MiniLM-L6-v2")

def get_embedding(text: str) -> list[float]:
    """
    Generates a 384-dimensional vector embedding for the given text.
    """
    embedding = model.encode(text)
    # Convert the embedding array to a plain Python list
    return embedding.tolist()
