import time
import numpy as np
import sounddevice as sd
from scipy.io import wavfile
from faster_whisper import WhisperModel
import torch
import warnings
import soundfile as sf
import subprocess
import re
import queue
import openwakeword
import os

try:
    from num2words import num2words
except ImportError:
    num2words = str

try:
    from openwakeword.model import Model
except ImportError:
    print("[Prototype_1 AUDIO: WARNING] openwakeword is not installed.")

warnings.filterwarnings("ignore")

class Prototype_1Audio:
    def __init__(self, stt_model_size="small.en", tts_speaker="en_21"):
        print("[Prototype_1 AUDIO] Initializing Audio Pipeline...")
        self.stt_model_size = stt_model_size
        self.tts_speaker = tts_speaker
        self.tts_sample_rate = 48000
        
        self._load_models()

    def _load_models(self):
        # 1. STT (Whisper) GPU
        print(f"[Prototype_1 AUDIO] Loading STT Model ({self.stt_model_size}) on CUDA...")
        self.stt_model = WhisperModel(self.stt_model_size, device="cuda", compute_type="float16")
        
        # 2. TTS (Silero) CPU
        print("[Prototype_1 AUDIO] Loading TTS Model (Silero v3_en) on CPU...")
        self.tts_device = torch.device('cpu')
        self.tts_model, _ = torch.hub.load(repo_or_dir='snakers4/silero-models', model='silero_tts', language='en', speaker='v3_en', verbose=False)
        self.tts_model.to(self.tts_device)
        
        # 3. [New] VAD (Voice Activity Detection) CPU
        print("[Prototype_1 AUDIO] Loading VAD Model (Silero VAD) on CPU...")
        self.vad_model, _ = torch.hub.load(repo_or_dir='snakers4/silero-vad', model='silero_vad', force_reload=False)
        self.vad_model.to(self.tts_device)
        
        # 4. [New] Wake-word (openWakeWord) CPU
        print("[Prototype_1 AUDIO] Loading Custom Wake-word Model...")
        
        custom_model_path = "./hey_prototype.onnx"
        
        if os.path.exists(custom_model_path):
            print("[Prototype_1 AUDIO] Found custom model! Waking up to 'Hey Prototype'.")
            self.oww_model = Model(wakeword_model_paths=[custom_model_path])
        else:
            print("[Prototype_1 AUDIO: WARNING] Custom model not found. Falling back to 'hey_jarvis'.")
            pretrained_models = openwakeword.get_pretrained_model_paths()
            jarvis_path = next((p for p in pretrained_models if "jarvis" in p.lower()), None)
            self.oww_model = Model(wakeword_model_paths=[jarvis_path])

    def wait_for_wakeword(self):
        fs = 16000
        chunk_samples = 1280 
        q = queue.Queue()
        
        def callback(indata, frames, time_info, status):
            q.put(indata.copy())
            
        print("\n[Prototype_1 AUDIO] Sleep mode active. Say 'Hey Prototype' to wake up...")
        with sd.InputStream(samplerate=fs, channels=1, dtype='int16', callback=callback, blocksize=chunk_samples):
            while True:
                chunk = q.get()
                audio_array = np.squeeze(chunk)
                
                self.oww_model.predict(audio_array)
                
                # Threshold > 0.5 will wake the system
                for mdl in self.oww_model.prediction_buffer.keys():
                    if self.oww_model.prediction_buffer[mdl][-1] > 0.5:
                        print("\n[Prototype_1 AUDIO] WAKE-WORD DETECTED!")
                        return True

    def listen_dynamic(self, silence_threshold=1.5, max_wait_time=8.0):
        print(f"[Prototype_1 AUDIO: LISTENING] Speak now (Auto-cut after {silence_threshold}s silence)...")
        fs = 16000
        
        chunk_samples = 512  
        
        q = queue.Queue()
        def callback(indata, frames, time_info, status):
            q.put(indata.copy())

        audio_data = []
        has_spoken = False
        silence_start_time = None
        listen_start_time = time.time()

        with sd.InputStream(samplerate=fs, channels=1, dtype='int16', callback=callback, blocksize=chunk_samples):
            while True:
                chunk = q.get()
                audio_data.append(chunk)
                
                # Silero VAD (-1.0 - 1.0)
                audio_float32 = np.squeeze(chunk).astype(np.float32) / 32768.0
                tensor_chunk = torch.from_numpy(audio_float32)
                
                # Probabilty of Voice input every 32ms
                speech_prob = self.vad_model(tensor_chunk, fs).item()
                
                if speech_prob > 0.5: 
                    if not has_spoken:
                        print("[Prototype_1 AUDIO] Voice activity detected. Recording...")
                    has_spoken = True
                    silence_start_time = None  
                else:  
                    if has_spoken:
                        if silence_start_time is None:
                            silence_start_time = time.time()
                        elif time.time() - silence_start_time > silence_threshold:
                            print("[Prototype_1 AUDIO] Silence threshold reached. Stopping recording.")
                            break
                    else:
                        if time.time() - listen_start_time > max_wait_time:
                            print("[Prototype_1 AUDIO] Timeout: No speech detected after wake-up.")
                            return ""
        
        if not audio_data:
            return ""

        recording = np.concatenate(audio_data, axis=0)
        wav_filename = "temp_mic.wav"
        wavfile.write(wav_filename, fs, recording)
        
        segments, info = self.stt_model.transcribe(wav_filename, beam_size=5, language="en")
        text = " ".join([segment.text for segment in segments]).strip()
        
        print(f"[Prototype_1 AUDIO: HEARD] {text}")
        return text

    def _normalize_text(self, text):
        if not text:
            return ""
        text = text.replace('&', ' and ').replace('%', ' percent ').replace('@', ' at ').replace('#', ' hashtag ').replace('+', ' plus ').replace('-', ' minus ')
        text = re.sub(r'[*_~^|`\\[\]{}]', '', text)
        def replace_number(match):
            try:
                return num2words(int(match.group()))
            except:
                return match.group()
        text = re.sub(r'\b\d+\b', replace_number, text)
        text = re.sub(r'\s+', ' ', text).strip()
        return text

    def speak(self, text):
        """Synthesizes text to speech with Sci-Fi Robot modulation and plays it via OS native player."""
        if not text:
            return
            
        clean_text = self._normalize_text(text)
        print(f"[Prototype_1 AUDIO: SPEAKING] Cleaned Text: {clean_text}")
        
        try:
            # ---------------------------------------------------------
            # 1. TEXT CHUNKING: "." or "," or other similar character that seperate a sentence
            # ---------------------------------------------------------
            sentences = re.split(r'(?<=[.!?])\s+|\n+', clean_text)
            sentences = [s.strip() for s in sentences if s.strip()]
            
            audio_chunks = []
            for sentence in sentences:
                # Ignore sentences that has only less than 2 words to prevent TTS error tensor
                if len(sentence) < 2:
                    continue
                try:
                    chunk_audio = self.tts_model.apply_tts(
                        text=sentence, 
                        speaker=self.tts_speaker, 
                        sample_rate=self.tts_sample_rate
                    )
                    audio_chunks.append(chunk_audio.numpy())
                except Exception as e:
                    print(f"[Prototype_1 AUDIO: WARNING] Skipping chunk '{sentence}': {e}")
            
            if not audio_chunks:
                return

            # Concat all chunk
            audio_np = np.concatenate(audio_chunks)
            
            # ---------------------------------------------------------
            # 2. Ring Modulation (Robot Effect)
            # ---------------------------------------------------------
            t = np.arange(len(audio_np)) / self.tts_sample_rate
            carrier_freq = 45 # Metallic vibration frequency
            robot_effect = np.sin(2 * np.pi * carrier_freq * t)
            audio_robot = audio_np * robot_effect
            
            # ---------------------------------------------------------
            # 3. PLAYBACK BYPASSING PYTHON GIL
            # ---------------------------------------------------------
            temp_wav = "temp_reply.wav"
            sf.write(temp_wav, audio_robot, self.tts_sample_rate, subtype='PCM_16')
            subprocess.run(["aplay", "-q", temp_wav])
            
        except Exception as e:
            print(f"[Prototype_1 AUDIO: ERROR] Failed to synthesize speech: {e}")