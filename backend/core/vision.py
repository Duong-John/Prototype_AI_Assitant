import os
import requests
from dotenv import load_dotenv

load_dotenv()

NVIDIA_API_KEY = os.getenv("NVIDIA_API_KEY")

# Using the Llama 3.2 11B Vision Instruct model hosted on NVIDIA NIM
VISION_MODEL = "meta/llama-3.2-11b-vision-instruct"

class NvidiaVision:
    def __init__(self):
        self.api_key = NVIDIA_API_KEY
        self.url = "https://integrate.api.nvidia.com/v1/chat/completions"

    def analyze_image_base64(self, base64_image: str, query: str = "Describe this image concisely.") -> str:
        """
        Sends a base64 encoded image to the NVIDIA Vision API for analysis.
        """
        if not self.api_key:
            print("[VISION ERROR] NVIDIA_API_KEY is not set.")
            return "Vision API key missing."
            
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Accept": "application/json"
        }
        
        # Payload structured according to OpenAI's vision standard 
        # which NVIDIA NIM uses.
        payload = {
            "model": VISION_MODEL,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": query
                        },
                        {
                            "type": "image_url",
                            "image_url": {
                                # Ensure we prefix with the correct data URI scheme
                                "url": f"data:image/jpeg;base64,{base64_image}"
                            }
                        }
                    ]
                }
            ],
            "max_tokens": 256,
            "temperature": 0.5
        }
        
        try:
            print(f"[VISION] Sending image to NVIDIA API ({VISION_MODEL})...")
            response = requests.post(self.url, headers=headers, json=payload, timeout=15)
            
            if response.status_code == 200:
                data = response.json()
                context = data.get('choices', [{}])[0].get('message', {}).get('content', '').strip()
                return context
            else:
                print(f"[VISION ERROR] API returned {response.status_code}: {response.text}")
                return "Error analyzing visual data."
                
        except requests.exceptions.Timeout:
            print("[VISION ERROR] Request timed out.")
            return "Vision system timeout."
        except Exception as e:
            print(f"[VISION ERROR] Request failed: {e}")
            return "Vision system encountered an error."

# ==========================================
# TEST MODULE 
# ==========================================
if __name__ == "__main__":
    print("--- TESTING NVIDIA VISION PIPELINE ---")
    vision = NvidiaVision()
    
    # We use a hardcoded Base64 string of a tiny 1x1 pixel Red Image just to test the API connection
    # without needing you to manually place an image in the folder.
    test_b64_red_pixel = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg=="
    
    test_query = "What color is this image? Please answer in one word."
    print("[TEST] Sending a 1x1 red pixel test image to NVIDIA...")
    
    result = vision.analyze_image_base64(base64_image=test_b64_red_pixel, query=test_query)
    print(f"[VISION RESULT]: {result}")