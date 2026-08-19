import time
import numpy as np
import sounddevice as sd
from scipy.io import wavfile
from faster_whisper import WhisperModel
import torch
import warnings
import soundfile as sf
import subprocess

# Suppress PyTorch Hub warnings for clean terminal output
warnings.filterwarnings("ignore")

class Prototype_1Audio:
    def __init__(self, stt_model_size="small.en", tts_speaker="en_21"):
        print("[Prototype_1 AUDIO] Initializing Audio Pipeline...")
        self.stt_model_size = stt_model_size
        self.tts_speaker = tts_speaker
        self.tts_sample_rate = 48000
        
        self._load_models()

    def _load_models(self):
        # 1. Load STT (Whisper) on GPU
        print(f"[Prototype_1 AUDIO] Loading STT Model ({self.stt_model_size}) on CUDA...")
        self.stt_model = WhisperModel(self.stt_model_size, device="cuda", compute_type="float16")
        
        # 2. Load TTS (Silero) on CPU
        print("[Prototype_1 AUDIO] Loading TTS Model (Silero v3_en) on CPU...")
        self.tts_device = torch.device('cpu')
        self.tts_model, _ = torch.hub.load(
            repo_or_dir='snakers4/silero-models',
            model='silero_tts',
            language='en',
            speaker='v3_en',
            verbose=False
        )
        self.tts_model.to(self.tts_device)
        print("[Prototype_1 AUDIO] Audio Pipeline Ready.")

    def listen(self, seconds=5):
        """Records audio for a given duration and returns the transcribed text."""
        fs = 16000  # Whisper requires 16kHz
        
        print(f"\n[Prototype_1 AUDIO: LISTENING] Speak now... ({seconds}s)")
        recording = sd.rec(int(seconds * fs), samplerate=fs, channels=1, dtype='int16')
        sd.wait() 
        
        wav_filename = "temp_mic.wav"
        wavfile.write(wav_filename, fs, recording)
        
        # Transcribe
        segments, info = self.stt_model.transcribe(wav_filename, beam_size=5, language="en")
        text = " ".join([segment.text for segment in segments]).strip()
        
        print(f"[Prototype_1 AUDIO: HEARD] {text}")
        return text

    # def speak(self, text):
    #     """Synthesizes text to speech with Sci-Fi Robot modulation and plays it."""
    #     if not text:
    #         return
            
    #     print(f"[Prototype_1 AUDIO: SPEAKING] Applying Robot Effect...")
    #     try:
    #         # Generate Base Audio
    #         audio = self.tts_model.apply_tts(
    #             text=text, 
    #             speaker=self.tts_speaker, 
    #             sample_rate=self.tts_sample_rate
    #         )
            
    #         # --- Ring Modulation (Robot Effect) ---
    #         audio_np = audio.numpy()
    #         t = np.arange(len(audio_np)) / self.tts_sample_rate
    #         carrier_freq = 45 # Metallic vibration frequency
    #         robot_effect = np.sin(2 * np.pi * carrier_freq * t)
    #         audio_robot = audio_np * robot_effect
            
    #         # Play Audio
    #         sd.play(audio_robot, self.tts_sample_rate)
    #         sd.wait()
            
    #     except Exception as e:
    #         print(f"[Prototype_1 AUDIO: ERROR] Failed to synthesize speech: {e}")

    def speak(self, text):
        """Synthesizes text to speech with Sci-Fi Robot modulation and plays it via OS native player."""
        if not text:
            return
            
        print(f"[Prototype_1 AUDIO: SPEAKING] Applying Robot Effect...")
        try:
            # 1. Generate Base Audio (Silero)
            audio = self.tts_model.apply_tts(
                text=text, 
                speaker=self.tts_speaker, 
                sample_rate=self.tts_sample_rate
            )
            
            # 2. Ring Modulation (Robot Effect)
            audio_np = audio.numpy()
            t = np.arange(len(audio_np)) / self.tts_sample_rate
            carrier_freq = 45 # Metallic vibration frequency
            robot_effect = np.sin(2 * np.pi * carrier_freq * t)
            audio_robot = audio_np * robot_effect
            
            # ---------------------------------------------------------
            # 3. [FIXED] PLAYBACK BYPASSING PYTHON GIL
            # ---------------------------------------------------------
            temp_wav = "temp_reply.wav"

            sf.write(temp_wav, audio_robot, self.tts_sample_rate, subtype='PCM_16')
            
            subprocess.run(["aplay", "-q", temp_wav])
            
        except Exception as e:
            print(f"[Prototype_1 AUDIO: ERROR] Failed to synthesize speech: {e}")