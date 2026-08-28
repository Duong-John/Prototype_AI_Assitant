import os
import requests
from groq import Groq
from dotenv import load_dotenv

load_dotenv()

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
client = Groq(api_key=GROQ_API_KEY)

STT_MODEL = "whisper-large-v3-turbo"
TTS_MODEL = "canopylabs/orpheus-v1-english"

class GroqAudioPipeline:
    def __init__(self):
        self.api_key = GROQ_API_KEY

    def transcribe_audio(self, audio_file_path: str) -> str:
        """
        Converts spoken audio file into text using Groq's Whisper Turbo.
        """
        if not os.path.exists(audio_file_path):
            print(f"[STT ERROR] File not found: {audio_file_path}")
            return ""

        print(f"[STT] Transcribing {audio_file_path} via Groq...")
        try:
            with open(audio_file_path, "rb") as file:
                transcription = client.audio.transcriptions.create(
                  file=(os.path.basename(audio_file_path), file.read()),
                  model=STT_MODEL,
                  response_format="json",
                  language="en" 
                )
            return transcription.text.strip()
        except Exception as e:
            print(f"[STT ERROR] Transcription failed: {e}")
            return ""

    def synthesize_speech(self, text: str, output_path: str = "temp_output.wav") -> str:
        """
        Converts text into spoken audio using Groq's TTS endpoint.
        Uses standard HTTP request to ensure compatibility with OpenAI-like endpoints.
        """
        print(f"[TTS] Synthesizing speech via Groq: '{text[:30]}...'")
        
        url = "https://api.groq.com/openai/v1/audio/speech"
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": TTS_MODEL,
            "input": text,
            "voice": "diana",
            "response_format": "wav" 
        }

        try:
            response = requests.post(url, headers=headers, json=payload, timeout=10)
            
            if response.status_code == 200:
                with open(output_path, 'wb') as f:
                    f.write(response.content)
                print(f"[TTS] Successfully saved audio to {output_path}")
                return output_path
            else:
                print(f"[TTS ERROR] API returned status {response.status_code}: {response.text}")
                return ""
                
        except Exception as e:
            print(f"[TTS ERROR] Speech synthesis failed: {e}")
            return ""

# ==========================================
# TEST MODULE 
# ==========================================
if __name__ == "__main__":
    print("--- TESTING GROQ AUDIO PIPELINE ---")
    audio_sys = GroqAudioPipeline()
    
    # 1. Test TTS (Text to Speech)
    test_text = "System is fully operational. Audio pipeline initialized."
    output_file = audio_sys.synthesize_speech(test_text, "test_speech.wav")
    
    # 2. Test STT (Speech to Text)
    # We will feed the newly generated TTS audio back into the STT model!
    if output_file and os.path.exists(output_file):
        print("\n[TEST] Feeding the generated audio back into STT...")
        transcribed_text = audio_sys.transcribe_audio(output_file)
        print(f"[STT RESULT]: {transcribed_text}")
    else:
        print("[TEST FAILED] Could not generate audio file for STT testing.")