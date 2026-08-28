import os
from groq import Groq
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Initialize Groq Client
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
if not GROQ_API_KEY:
    print("[WARNING] GROQ_API_KEY is not set in .env file.")

client = Groq(api_key=GROQ_API_KEY)

# Use the Qwen model available on Groq (Fallback to a stable one if the exact string changes)
# Note: Groq frequently updates model IDs. 
# Current stable Qwen on Groq is often "qwen-2.5-32b-it" or similar.
LLM_MODEL = "qwen/qwen3.8-27b" 

class GroqLLM:
    def __init__(self, model_name: str = LLM_MODEL):
        self.model_name = model_name

    def generate_response(self, user_text: str, system_prompt: str = "", chat_history: list = None) -> str:
        """
        Calls Groq API to generate a response based on the conversation history.
        """
        if chat_history is None:
            chat_history = []

        # Construct messages array
        messages = []
        
        # Add system prompt if provided
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
            
        # Append history
        messages.extend(chat_history)
        
        # Append current user prompt
        messages.append({"role": "user", "content": user_text})

        try:
            print(f"[LLM] Sending request to Groq ({self.model_name})...")
            chat_completion = client.chat.completions.create(
                messages=messages,
                model=self.model_name,
                temperature=0.7,
                max_tokens=256, # Keep it concise for voice interaction
            )
            
            response_text = chat_completion.choices[0].message.content.strip()
            return response_text
            
        except Exception as e:
            print(f"[LLM ERROR] Groq API Request Failed: {e}")
            return "[sad] System cognitive error."

# ==========================================
# TEST MODULE 
# ==========================================
if __name__ == "__main__":
    print("--- TESTING GROQ LLM ---")
    brain = GroqLLM()
    
    test_system = "You are Prototype. Speak ONLY English. Answer in 1 short sentence."
    test_user = "Hello Prototype, what is the core advantage of running AI on the edge?"
    
    answer = brain.generate_response(user_text=test_user, system_prompt=test_system)
    print(f"\n[USER]: {test_user}")
    print(f"[PROTOTYPE]: {answer}")