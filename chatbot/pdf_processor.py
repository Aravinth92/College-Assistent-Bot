import re
from pypdf import PdfReader

def extract_text_from_pdf(pdf_path):
    """
    Extracts all text from a PDF file using pypdf.
    """
    try:
        reader = PdfReader(pdf_path)
        extracted_text = []
        for i, page in enumerate(reader.pages):
            text = page.extract_text()
            if text:
                extracted_text.append(text)
        
        full_text = "\n".join(extracted_text)
        return clean_text(full_text)
    except Exception as e:
        print(f"Error extracting PDF: {e}")
        return ""

def clean_text(text):
    """
    Cleans raw text by normalizing whitespace, removing duplicate spaces,
    and stripping trailing/leading whitespaces.
    """
    # Replace multiple spaces with a single space
    text = re.sub(r'[ \t]+', ' ', text)
    # Replace multiple consecutive newlines with two newlines (to preserve paragraphs)
    text = re.sub(r'\n{3,}', '\n\n', text)
    return text.strip()

def chunk_text(text, chunk_size=800, overlap=150):
    """
    Splits text into chunks of specified character length with an overlap.
    """
    if not text:
        return []
    
    chunks = []
    start = 0
    text_len = len(text)
    
    while start < text_len:
        end = start + chunk_size
        # Adjust end to finish at a word boundary if possible (within reason)
        if end < text_len:
            # Look back up to 50 characters for a newline or space
            limit = max(start, end - 50)
            boundary = -1
            for pos in range(end, limit, -1):
                if text[pos] in ('\n', ' ', '.'):
                    boundary = pos
                    break
            if boundary != -1:
                end = boundary + 1 # Include the space/period
        
        chunk = text[start:end].strip()
        if len(chunk) > 50: # Only keep substantial chunks
            chunks.append(chunk)
            
        start += (chunk_size - overlap)
        # Avoid infinite loops or tiny advancements
        if start >= end:
            start = end
            
    return chunks

if __name__ == "__main__":
    # Test block
    sample_text = "This is a sample college prospectus text that will be chunked. " * 30
    chunks = chunk_text(sample_text, 100, 20)
    print(f"Generated {len(chunks)} chunks.")
    for idx, c in enumerate(chunks[:3]):
        print(f"Chunk {idx+1}: {c}")
