import requests
import json
import re
import os
import time
import datetime 
import chromadb
import threading
import queue
from chromadb.utils import embedding_functions
from chromadb.api.types import Documents, EmbeddingFunction, Embeddings

OLLAMA_API_URL = "http://localhost:11434/api/chat"
MODEL_NAME = "qwen2.5:7b"
EMBED_MODEL_NAME = "nomic-embed-text"
CHROMA_PERSIST_DIR = "./prototype1_memory"

class CustomOllamaEmbeddingFunction(EmbeddingFunction):
    def __init__(self, url="http://localhost:11434/api/embeddings", model_name="nomic-embed-text"):
        self.url = url
        self.model_name = model_name

    def __call__(self, input: Documents) -> Embeddings:
        embeddings = []
        for text in input:
            payload = {"model": self.model_name, "prompt": text}
            try:
                response = requests.post(self.url, json=payload).json()
                embeddings.append(response.get("embedding", []))
            except Exception as e:
                print(f"[EMBEDDING ERROR] {e}")
                embeddings.append([])
        return embeddings

class AIBuddyBrain:
    def __init__(self):
        self.short_term_memory = []
        self.max_history_turns = 8
        
        self.environment_state = {
            "user_identity": "Unknown",
            "visible_objects": "None",
            "vision_context": "None"
        }

        # ==========================================
        # 1. RAG DATABASE CHROMADB
        # ==========================================
        print("[BRAIN] Initializing Local Vector RAG (ChromaDB + Nomic-Embed)...")
        self.chroma_client = chromadb.PersistentClient(path=CHROMA_PERSIST_DIR)
        
        self.ollama_ef = CustomOllamaEmbeddingFunction(
            url="http://localhost:11434/api/embeddings",
            model_name=EMBED_MODEL_NAME
        )
        
        self.collection = self.chroma_client.get_or_create_collection(
            name="conversation_memory",
            embedding_function=self.ollama_ef
        )
        print(f"[BRAIN] RAG Engine Online. Total memories loaded: {self.collection.count()}")

        # ==========================================
        # 2. [New] MEMORY WORKER
        # ==========================================
        self.memory_queue = queue.Queue()
        self.memory_thread = threading.Thread(target=self._memory_worker_loop, daemon=True)
        self.memory_thread.start()

    def _memory_worker_loop(self):
        """Luồng ngầm liên tục chờ dữ liệu để ghi vào RAG mà không block Main Thread"""
        while True:
            # Blocked until new signal in Queue
            user_text, assistant_text = self.memory_queue.get()
            
            try:
                document_chunk = f"User: {user_text}\nPrototype_1: {assistant_text}"
                doc_id = f"mem_{int(time.time() * 1000)}"
                
                self.collection.add(
                    documents=[document_chunk],
                    metadatas=[{"timestamp": datetime.datetime.now().isoformat()}],
                    ids=[doc_id]
                )
                print(f"[RAG MEMORY] Background saved interaction. (Total: {self.collection.count()})")
            except Exception as e:
                print(f"[RAG MEMORY ERROR] Failed to store interaction: {e}")
            finally:
                # Đánh dấu hoàn tất task
                self.memory_queue.task_done()

    # ==========================================
    # RAG RETRIEVAL
    # ==========================================
    def _retrieve_relevant_facts(self, user_text):
        if self.collection.count() == 0:
            return "No previous memories stored yet."
            
        try:
            results = self.collection.query(
                query_texts=[user_text],
                n_results=min(2, self.collection.count())
            )
            
            retrieved_docs = results.get('documents', [[]])[0]
            if retrieved_docs:
                formatted_memory = "\n---\n".join(retrieved_docs)
                return formatted_memory
            return "No relevant context found."
        except Exception as e:
            print(f"[RAG RETRIEVE ERROR]: {e}")
            return "Memory retrieval error."

    # ==========================================
    # DETERMINISTIC ROUTING & CORE LOGIC
    # ==========================================
    def update_environment_state(self, key, value):
        if key in self.environment_state:
            self.environment_state[key] = value

    def build_system_prompt(self, user_text):
        state_str = "\n".join([f"- {k.replace('_', ' ').title()}: {v}" for k, v in self.environment_state.items()])
        recalled_memory = self._retrieve_relevant_facts(user_text)
        current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
            
        system_prompt = f"""You are Prototype_1, a logical AI assistant. Speak ONLY English.

[SYSTEM TIME]: {current_time}
[ENVIRONMENT]: {state_str}
[RECALLED LONG-TERM MEMORY (PAST CONVERSATIONS)]:
{recalled_memory}

CRITICAL RULES:
1. ZERO FOLLOW-UP QUESTIONS: NEVER ask questions at the end of your response. Provide the exact answer and STOP.
2. SPOKEN TEXT ONLY: Your output is read by a TTS voice. NEVER use Markdown, asterisks (**), bullet points, numbered lists, or URLs. Write in natural, flowing paragraphs ONLY.
3. MEMORY USAGE: Use the [RECALLED LONG-TERM MEMORY] to answer questions about the user's past, identity, major, or preferences.
4. EMOTION: You must include exactly one tag: [normal], [happy], or [sad].
"""
        return {"role": "system", "content": system_prompt}

    def _fast_path_filter(self, user_text):
        text_clean = user_text.strip().lower()
        if re.fullmatch(r"(ok|okay|k|thanks|thank you|got it|yep|yes|no|sure|cool)", text_clean):
            return "[happy] Acknowledged."
        return None

    def process_user_input(self, user_text, vision_tool_callback=None, search_tool_callback=None):
        print(f"\n[USER]: {user_text}")
        
        fast_response = self._fast_path_filter(user_text)
        if fast_response:
            print(f"[Prototype_1 (Fast-Path)]: {fast_response}")
            return fast_response
            
        self.short_term_memory.append({"role": "user", "content": user_text})

        if len(self.short_term_memory) > self.max_history_turns:
            self.short_term_memory = self.short_term_memory[-self.max_history_turns:]
        
        user_text_lower = user_text.lower()
        tool_result_context = ""

        if "vision" in user_text_lower and vision_tool_callback:
            print("\n[BRAIN: EXPLICIT TRIGGER] Deep Vision activated by keyword.")
            tool_result = vision_tool_callback(user_text)
            tool_result_context = f"[SYSTEM TOOL RESULT - DEEP VISION]: {tool_result}"

        elif "internet" in user_text_lower and search_tool_callback:
            print("\n[BRAIN: EXPLICIT TRIGGER] Web Search activated by keyword.")
            search_query = re.sub(r"(?i)\binternet\b", "", user_text)
            search_query = re.sub(r"^[^a-zA-Z0-9]+|[^a-zA-Z0-9]+$", "", search_query).strip()
            
            if not search_query:
                search_query = user_text 
                
            tool_result = search_tool_callback(search_query)
            tool_result_context = f"[SYSTEM TOOL RESULT - WEB SEARCH]: {tool_result}"

        messages = [self.build_system_prompt(user_text)] + self.short_term_memory
        
        if tool_result_context:
            messages.append({
                "role": "system",
                "content": f"{tool_result_context}\n\nCRITICAL INSTRUCTION: Based ONLY on the tool data above, answer the user's last question directly. DO NOT ask follow-up questions. DO NOT use markdown, asterisks, or URLs. Write a plain paragraph."
            })

        payload = {
            "model": MODEL_NAME,
            "messages": messages,
            "stream": False,
            "keep_alive": -1
        }

        try:
            print("[BRAIN] Synthesizing final answer...", end=" ", flush=True)
            res = requests.post(OLLAMA_API_URL, json=payload).json()
            final_text = res.get("message", {}).get("content", "").strip()
            
            self.short_term_memory.append({"role": "assistant", "content": final_text})
            print(f"\n[Prototype_1]: {final_text}")
            
            # [New] Fire-and-forget: Insert into Queue and run if able
            self.memory_queue.put((user_text, final_text))
            
            return final_text
            
        except Exception as e:
            print(f"\n[BRAIN: ERROR] {e}")
            return "[sad] System error."