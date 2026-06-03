import chromadb
from chromadb.utils import embedding_functions
import os
import uuid

# This script is to test if the database part works independently
CHROMA_DATA_PATH = os.path.join(os.getcwd(), "chroma_data")
client = chromadb.PersistentClient(path=CHROMA_DATA_PATH)
default_ef = embedding_functions.DefaultEmbeddingFunction()

collection = client.get_or_create_collection(
    name="documents",
    embedding_function=default_ef
)

# Add a test document
test_content = "The capital of France is Paris. It is known for the Eiffel Tower."
doc_id = str(uuid.uuid4())
collection.add(
    documents=[test_content],
    ids=[doc_id]
)
print(f"Added test document: {doc_id}")

# Search for it
results = collection.query(
    query_texts=["What is the capital of France?"],
    n_results=1
)
print("Search Results:", results['documents'][0])
