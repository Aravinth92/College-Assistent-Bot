import os
import struct
import google.generativeai as genai
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Initialize Gemini Configuration
api_key = os.getenv("GEMINI_API_KEY")
if api_key:
    genai.configure(api_key=api_key)

def serialize_vector(vector):
    """
    Serializes a list of floats into a binary BLOB.
    """
    if not vector:
        return b""
    return struct.pack(f'{len(vector)}f', *vector)

def deserialize_vector(blob):
    """
    Deserializes a binary BLOB back into a list of floats.
    """
    if not blob:
        return []
    num_floats = len(blob) // 4
    return list(struct.unpack(f'{num_floats}f', blob))

def get_embedding(text, is_query=False):
    """
    Generates an embedding for the given text using Gemini's text-embedding-004.
    Uses 'retrieval_query' for query text, and 'retrieval_document' for document chunks.
    """
    global api_key
    # Recheck key in case it was added dynamically
    if not api_key:
        api_key = os.getenv("GEMINI_API_KEY")
        if api_key:
            genai.configure(api_key=api_key)
            
    if not api_key:
        print("Warning: GEMINI_API_KEY not configured. Cannot generate embeddings.")
        # Fallback to zero vector so system doesn't crash, but log error
        return [0.0] * 768

    try:
        task_type = "retrieval_query" if is_query else "retrieval_document"
        response = genai.embed_content(
            model="models/text-embedding-004",
            content=text,
            task_type=task_type
        )
        return response['embedding']
    except Exception as e:
        print(f"Error generating embedding for text: {e}")
        # Return a zero vector fallback
        return [0.0] * 768

def cosine_similarity(v1, v2):
    """
    Computes cosine similarity between two vector lists.
    """
    if len(v1) != len(v2) or len(v1) == 0:
        return 0.0
    
    dot_product = sum(x * y for x, y in zip(v1, v2))
    norm_v1 = sum(x * x for x in v1) ** 0.5
    norm_v2 = sum(x * x for x in v2) ** 0.5
    
    if norm_v1 == 0.0 or norm_v2 == 0.0:
        return 0.0
        
    return dot_product / (norm_v1 * norm_v2)

def search_prospectus(query_text, top_k=5):
    """
    Performs vector similarity search on prospectus chunks in the database.
    """
    query_vector = get_embedding(query_text, is_query=True)
    if not query_vector or all(x == 0.0 for x in query_vector):
        return []

    # Import inside function to avoid circular dependencies
    from database.db import get_db_connection
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute("SELECT id, chunk_text, embedding FROM prospectus_chunks")
        rows = cursor.fetchall()
    except Exception as e:
        print(f"Error querying prospectus chunks: {e}")
        rows = []
    finally:
        conn.close()

    results = []
    for row in rows:
        chunk_text = row['chunk_text']
        blob = row['embedding']
        if not blob:
            continue
            
        chunk_vector = deserialize_vector(blob)
        sim = cosine_similarity(query_vector, chunk_vector)
        results.append((chunk_text, sim))

    # Sort by similarity in descending order
    results.sort(key=lambda x: x[1], reverse=True)
    return results[:top_k]
