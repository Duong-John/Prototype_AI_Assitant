import os
import json
import base64
import asyncio
import re
import tempfile
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

from core.llm import GroqLLM
from core.audio import GroqAudioPipeline
from core.vision import NvidiaVision
from core.rag import PineconeRAG

load_dotenv()

app = FastAPI(title="Prototype_Web API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ==========================================
# GLOBAL
# ==========================================
print("[SYSTEM] Booting up AI Modules...")
ai_llm = GroqLLM()
ai_audio = GroqAudioPipeline()
ai_vision = NvidiaVision()
ai_rag = PineconeRAG()
print("[SYSTEM] All AI Modules Online.")

@app.get("/")
async def root_endpoint():
    return {"message": "Prototype_Web API is running. Connect via WebSocket at /ws/chat"}

@app.get("/health")
async def health_check():
    return {"status": "ok", "message": "Prototype Backend is awake."}

# ==========================================
# WEBSOCKET ENDPOINT (Real-time I/O)
# ==========================================
@app.websocket("/ws/chat")
async def websocket_chat_endpoint(websocket: WebSocket):
    await websocket.accept()
    print("\n[WEBSOCKET] Client connected.")
    
    # I/O FOLDER
    temp_dir = tempfile.mkdtemp()
    
    try:
        while True:
            data = await websocket.receive_text()
            
            try:
                payload = json.loads(data)
                action = payload.get("action")
                
                if action == "process":
                    user_email = payload.get("email", "guest@hcmut.edu.vn")
                    audio_b64 = payload.get("audio_b64", "")
                    image_b64 = payload.get("image_b64", "")
                    
                    if not audio_b64:
                        await websocket.send_json({"error": "No audio data received."})
                        continue

                    print(f"\n[WEBSOCKET] Processing request from {user_email}")
                    
                    # 1. SAVE AUDIO FROM BASE64 TO TEMP FILE
                    input_audio_path = os.path.join(temp_dir, "input_mic.wav")
                    with open(input_audio_path, "wb") as f:
                        f.write(base64.b64decode(audio_b64))
                        
                    # 2. STT (Speech to Text)
                    user_text = await asyncio.to_thread(ai_audio.transcribe_audio, input_audio_path)
                    print(f"[USER HEARD]: {user_text}")
                    
                    if not user_text:
                        await websocket.send_json({"error": "Could not understand audio."})
                        continue

                    # 3. RAG
                    memory_context = await asyncio.to_thread(ai_rag.retrieve_memory, user_email, user_text)
                    
                    # 4. VISION (Keyword 'VISION' with image)
                    vision_context = ""
                    if "vision" in user_text.lower() and image_b64:
                        print("[WEBSOCKET] Vision keyword detected. Analyzing frame...")
                        
                        await websocket.send_json({"type": "status", "status": "analyzing_vision"})
                        vision_context = await asyncio.to_thread(ai_vision.analyze_image_base64, image_b64)
                        vision_context = f"[SYSTEM TOOL RESULT - DEEP VISION]: {vision_context}"

                    # 5. PROMPT & LLM SYNTHESIS
                    system_prompt = f"""You are Prototype, a logical AI assistant. Speak ONLY English.
[RECALLED LONG-TERM MEMORY]:
{memory_context}

CRITICAL RULES:
1. NEVER ask follow-up questions. Answer and STOP.
2. SPOKEN TEXT ONLY. No markdown.
3. EMOTION TAG: You must include exactly one tag: [normal], [happy], or [sad]."""
                    
                    if vision_context:
                         system_prompt += f"\n\n{vision_context}\nCRITICAL INSTRUCTION: Based ONLY on the tool data above, answer the user's last question directly."

                    ai_response = await asyncio.to_thread(ai_llm.generate_response, user_text, system_prompt)
                    print(f"[PROTOTYPE RAW]: {ai_response}")

                    # 6. TRÍCH XUẤT CẢM XÚC (REGEX)
                    emotion_tag = "normal"
                    match = re.search(r"\[(normal|happy|sad)\]", ai_response, re.IGNORECASE)
                    if match:
                        emotion_tag = match.group(1).lower()
                        clean_text = re.sub(r"\[.*?\]", "", ai_response).strip()
                    else:
                        clean_text = ai_response

                    # 7. TTS (Text to Speech)
                    output_audio_path = os.path.join(temp_dir, "output_speech.wav")
                    tts_result_path = await asyncio.to_thread(ai_audio.synthesize_speech, clean_text, output_audio_path)
                    
                    output_audio_b64 = ""
                    if tts_result_path and os.path.exists(tts_result_path):
                        with open(tts_result_path, "rb") as f:
                            output_audio_b64 = base64.b64encode(f.read()).decode("utf-8")

                    # 8. RESULT TO  BROWSER (UI)
                    await websocket.send_json({
                        "type": "response",
                        "text": clean_text,
                        "emotion": emotion_tag,
                        "audio_b64": output_audio_b64
                    })
                    
                    # 9. SAVE TO PINE CONE (FIRE & FORGET)
                    # Create a asyncio thread run below
                    asyncio.create_task(
                        asyncio.to_thread(ai_rag.upsert_memory, user_email, user_text, clean_text)
                    )

            except json.JSONDecodeError:
                print("[WEBSOCKET] Error: Invalid JSON.")
            except Exception as e:
                print(f"[WEBSOCKET] Processing error: {e}")
                await websocket.send_json({"error": "Internal Server Error"})

    except WebSocketDisconnect:
        print("[WEBSOCKET] Client disconnected.")
    finally:
        import shutil
        shutil.rmtree(temp_dir, ignore_errors=True)

if __name__ == "__main__":
    import uvicorn
    print("Starting Prototype_Web Backend...")
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)