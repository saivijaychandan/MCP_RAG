from fastmcp import FastMCP
import chromadb
from chromadb.utils import embedding_functions
import os
from typing import List, Optional
import mimetypes
from pypdf import PdfReader
from docx import Document
import logging
import hashlib
from langchain_text_splitters import RecursiveCharacterTextSplitter

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("RAG-Server")

# Initialize FastMCP server
mcp = FastMCP("RAG-Server")

# Initialize ChromaDB
CHROMA_DATA_PATH = os.path.join(os.getcwd(), "chroma_data")
DATA_DIR = os.path.join(os.getcwd(), "data")

# Create data directory if it doesn't exist
if not os.path.exists(DATA_DIR):
    os.makedirs(DATA_DIR)
    logger.info(f"Created data directory at {DATA_DIR}")

client = chromadb.PersistentClient(path=CHROMA_DATA_PATH)
default_ef = embedding_functions.DefaultEmbeddingFunction()

# Create or get collection
collection = client.get_or_create_collection(
    name="documents",
    embedding_function=default_ef
)

# Initialize Text Splitter for chunking
text_splitter = RecursiveCharacterTextSplitter(
    chunk_size=1000,
    chunk_overlap=100,
    length_function=len,
    is_separator_regex=False,
)

def get_file_hash(file_path: str) -> str:
    """Generate a hash for the file to track changes."""
    hasher = hashlib.md5()
    with open(file_path, 'rb') as f:
        buf = f.read()
        hasher.update(buf)
    return hasher.hexdigest()

def process_file_content(file_path: str) -> Optional[str]:
    """Helper to extract text from different file types."""
    ext = os.path.splitext(file_path)[1].lower()
    content = ""
    
    try:
        if ext in ['.txt', '.md']:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
        elif ext == '.pdf':
            reader = PdfReader(file_path)
            for page in reader.pages:
                text = page.extract_text()
                if text:
                    content += text + "\n"
        elif ext in ['.doc', '.docx']:
            doc = Document(file_path)
            content = "\n".join([para.text for para in doc.paragraphs])
        
        return content.strip() if content.strip() else None
    except Exception as e:
        logger.error(f"Error extracting text from {file_path}: {str(e)}")
        return None

def ingest_data_folder():
    """Ingest all supported files from the 'data' directory on startup."""
    logger.info(f"Scanning data directory: {DATA_DIR}")
    files = [f for f in os.listdir(DATA_DIR) if os.path.isfile(os.path.join(DATA_DIR, f))]
    
    for filename in files:
        file_path = os.path.join(DATA_DIR, filename)
        file_hash = get_file_hash(file_path)
        
        # Check if already ingested using file hash
        existing = collection.get(where={"file_hash": file_hash})
        if existing and existing['ids']:
            logger.info(f"Skipping {filename} (already ingested with same content)")
            continue
            
        content = process_file_content(file_path)
        if content:
            # Chunk the content
            chunks = text_splitter.split_text(content)
            
            import uuid
            ids = [str(uuid.uuid4()) for _ in chunks]
            metadatas = [{
                "source": file_path, 
                "filename": filename, 
                "file_hash": file_hash,
                "chunk": i,
                "total_chunks": len(chunks)
            } for i in range(len(chunks))]
            
            collection.add(
                documents=chunks,
                metadatas=metadatas,
                ids=ids
            )
            logger.info(f"Successfully auto-ingested: {filename} into {len(chunks)} chunks")
        else:
            logger.warning(f"Could not extract text from: {filename}")

@mcp.tool()
def ping() -> str:
    """Check if the server is responsive."""
    return "pong"

@mcp.tool()
def add_document(content: str, metadata: Optional[dict] = None) -> str:
    """
    Add a document to the RAG knowledge base.
    
    Args:
        content: The text content of the document.
        metadata: Optional dictionary of metadata associated with the document.
    """
    chunks = text_splitter.split_text(content)
    import uuid
    
    ids = [str(uuid.uuid4()) for _ in chunks]
    metadatas = [metadata or {} for _ in chunks]
    for i, meta in enumerate(metadatas):
        meta.update({"chunk": i, "total_chunks": len(chunks)})

    collection.add(
        documents=chunks,
        metadatas=metadatas,
        ids=ids
    )
    return f"Document added successfully and split into {len(chunks)} chunks."

@mcp.tool()
def ingest_file(file_path: str) -> str:
    """
    Read a file (PDF, DOCX, TXT, MD) and add its content to the knowledge base.
    Security: Only allows files from within the workspace data folder.
    
    Args:
        file_path: The name of the file within the 'data' directory or absolute path.
    """
    # Security: Normalize path and ensure it's within DATA_DIR
    if not os.path.isabs(file_path):
        full_path = os.path.join(DATA_DIR, file_path)
    else:
        full_path = os.path.abspath(file_path)

    if not full_path.startswith(os.path.abspath(DATA_DIR)):
        return f"Error: Security violation. Access to {file_path} is restricted to the data directory."

    if not os.path.exists(full_path):
        return f"Error: File not found at {full_path}"
    
    file_hash = get_file_hash(full_path)
    content = process_file_content(full_path)
        
    if not content:
        return "Error: Could not extract any text from the file or unsupported format."
        
    chunks = text_splitter.split_text(content)
    import uuid
    ids = [str(uuid.uuid4()) for _ in chunks]
    metadatas = [{
        "source": full_path, 
        "filename": os.path.basename(full_path),
        "file_hash": file_hash,
        "chunk": i,
        "total_chunks": len(chunks)
    } for i in range(len(chunks))]
    
    collection.add(
        documents=chunks,
        metadatas=metadatas,
        ids=ids
    )
    return f"Successfully ingested {os.path.basename(full_path)} into {len(chunks)} chunks."

@mcp.tool()
def search_documents(query: str, n_results: int = 5) -> List[str]:
    """
    Search for relevant document chunks in the knowledge base.
    
    Args:
        query: The search query.
        n_results: Number of results to return.
    """
    results = collection.query(
        query_texts=[query],
        n_results=n_results
    )
    
    return results.get('documents', [[]])[0]

@mcp.tool()
def search_documents_with_metadata(query: str, filters: dict, n_results: int = 5) -> List[dict]:
    """
    Search for relevant document chunks with filtering.
    
    Args:
        query: The search query.
        filters: ChromaDB filter dictionary.
        n_results: Number of results to return.
    """
    results = collection.query(
        query_texts=[query],
        where=filters,
        n_results=n_results
    )
    
    docs = []
    if results['ids']:
        for i in range(len(results['ids'][0])):
            docs.append({
                "id": results['ids'][0][i],
                "content": results['documents'][0][i],
                "metadata": results['metadatas'][0][i]
            })
    return docs

@mcp.tool()
def delete_document(doc_id: str) -> str:
    """
    Delete a document (or chunk) from the knowledge base by its ID.
    """
    collection.delete(ids=[doc_id])
    return f"Entry {doc_id} deleted successfully."

@mcp.tool()
def list_documents(limit: int = 10) -> List[dict]:
    """
    List entries currently in the knowledge base.
    """
    results = collection.get(limit=limit)
    docs = []
    for i in range(len(results['ids'])):
        docs.append({
            "id": results['ids'][i],
            "content": results['documents'][i],
            "metadata": results['metadatas'][i]
        })
    return docs

if __name__ == "__main__":
    logger.info("Starting Production RAG MCP Server...")
    logger.info(f"ChromaDB data path: {CHROMA_DATA_PATH}")
    
    try:
        # Auto-ingest files from the data folder
        ingest_data_folder()
    except Exception as e:
        logger.error(f"Failed to auto-ingest data folder: {e}")
    
    mcp.run()
