import os
import time
import requests
from pinecone import Pinecone
from dotenv import load_dotenv

load_dotenv()

PINECONE_API_KEY = os.getenv("PINECONE_API_KEY")
PINECONE_INDEX_NAME = os.getenv("PINECONE_INDEX_NAME")

# Using Pinecone's built-in Inference API (No NVIDIA needed)
EMBEDDING_MODEL = "multilingual-e5-large"

class PineconeRAG:
    def __init__(self):
        print("[RAG] Initializing Pinecone Vector Database...")
        if not PINECONE_API_KEY or not PINECONE_INDEX_NAME:
            print("[RAG WARNING] Pinecone credentials missing.")
            self.index = None
        else:
            try:
                self.pc = Pinecone(api_key=PINECONE_API_KEY)
                self.index = self.pc.Index(name=PINECONE_INDEX_NAME)
                print(f"[RAG] Successfully connected to Pinecone Index: '{PINECONE_INDEX_NAME}'")
            except Exception as e:
                print(f"[RAG ERROR] Failed to connect to Pinecone: {e}")
                self.index = None

    def _generate_embedding(self, text: str, input_type: str = "passage") -> list:
        """
        Generates a 1024-dimensional vector embedding using Pinecone's native API.
        input_type: "passage" for saving to DB, "query" for searching.
        """
        if not PINECONE_API_KEY:
            return []

        url = "https://api.pinecone.io/embed"
        
        # Pinecone requires this specific header for their Inference API
        headers = {
            "Api-Key": PINECONE_API_KEY,
            "Content-Type": "application/json",
            "X-Pinecone-API-Version": "2024-07" 
        }
        
        payload = {
            "model": EMBEDDING_MODEL,
            "inputs": [{"text": text}],
            "parameters": {
                "input_type": input_type,
                "truncate": "END"
            }
        }

        try:
            response = requests.post(url, headers=headers, json=payload, timeout=10)
            if response.status_code == 200:
                data = response.json()
                # Extract the embedding vector array
                return data['data'][0]['values']
            else:
                print(f"[EMBEDDING ERROR] {response.status_code}: {response.text}")
                return []
        except Exception as e:
            print(f"[EMBEDDING ERROR] Failed to generate embedding: {e}")
            return []

    def upsert_memory(self, user_email: str, user_text: str, ai_text: str):
        """
        Saves a conversation interaction to Pinecone, tagged with the user's email.
        """
        if self.index is None:
            return

        print(f"[RAG] Saving memory for user: {user_email}...")
        document_chunk = f"User: {user_text}\nPrototype: {ai_text}"
        
        # Use input_type="passage" when storing documents
        vector = self._generate_embedding(document_chunk, input_type="passage")
        
        if not vector:
            print("[RAG ERROR] Cannot save memory due to embedding failure.")
            return

        doc_id = f"mem_{user_email.split('@')[0]}_{int(time.time() * 1000)}"
        
        metadata = {
            "email": user_email,
            "text": document_chunk,
            "timestamp": time.time()
        }

        try:
            self.index.upsert(
                vectors=[
                    {
                        "id": doc_id,
                        "values": vector,
                        "metadata": metadata
                    }
                ]
            )
            print(f"[RAG] Memory successfully saved to Pinecone.")
        except Exception as e:
            print(f"[RAG ERROR] Failed to upsert to Pinecone: {e}")

    def retrieve_memory(self, user_email: str, current_query: str, top_k: int = 2) -> str:
        """
        Retrieves relevant past conversations ONLY for the specific user.
        """
        if self.index is None:
            return "Memory offline."

        print(f"[RAG] Searching memories for user: {user_email}...")
        
        # Use input_type="query" when searching
        query_vector = self._generate_embedding(current_query, input_type="query")
        
        if not query_vector:
            return "Memory retrieval error."

        try:
            result = self.index.query(
                vector=query_vector,
                filter={
                    "email": {"$eq": user_email}
                },
                top_k=top_k,
                include_metadata=True
            )

            matches = result.get("matches", [])
            if not matches:
                return "No relevant past memories found."

            retrieved_docs = [match["metadata"]["text"] for match in matches]
            formatted_memory = "\n---\n".join(retrieved_docs)
            return formatted_memory

        except Exception as e:
            print(f"[RAG ERROR] Failed to retrieve memory: {e}")
            return "Memory retrieval error."

# ==========================================
# TEST MODULE 
# ==========================================
if __name__ == "__main__":
    print("--- TESTING PINECONE NATIVE RAG PIPELINE ---")
    
    rag = PineconeRAG()
    test_email = "tester@hcmut.edu.vn"
    
    print("\n[TEST 1] Upserting synthetic memory...")
    test_user_q = "My favorite programming language is Python and I love WebRTC."
    test_ai_a = "I will remember that you like Python and WebRTC."
    rag.upsert_memory(user_email=test_email, user_text=test_user_q, ai_text=test_ai_a)
    
    print("\n[INFO] Waiting 5 seconds for Pinecone to index the new vector...")
    time.sleep(5)
    
    print("\n[TEST 2] Retrieving memory...")
    search_query = "What is my favorite programming language?"
    recalled_facts = rag.retrieve_memory(user_email=test_email, current_query=search_query)
    
    print(f"\n[QUERY]: {search_query}")
    print(f"[RECALLED MEMORY]:\n{recalled_facts}")