# Prototype AI Vision Assistant

![Version](https://img.shields.io/badge/Version-Prototype_1.0.1-blue.svg)
![Status](https://img.shields.io/badge/Status-Experimental-orange.svg)
![Platform](https://img.shields.io/badge/Platform-Linux-lightgrey.svg)

> **Note:** This project is currently in the **Prototype 1** stage. It serves as an experimental foundation for a fully localized, multimodal AI agent capable of sight, speech, and semantic memory.

<p align="center">
  <!-- [PLACEHOLDER: Insert demo image/GIF of the True Geometry Bot Eye UI here] -->
  <img src="docs/assets/eye_ui_demo.png" alt="Bot Eye UI Demo" width="600"/>
</p>

## Overview

The **Prototype AI Vision Assistant** is a multimodal, proactive AI agent designed to run entirely locally. Built with a focus on strict state management, deterministic routing, and zero-latency audio-visual processing, this prototype bridges the gap between raw Large Language Models (LLMs) and real-time physical environment interaction.

Rather than relying on cloud APIs, this system leverages a robust CUDA backend to handle high-performance tasks—including Vision-Language Models (VLMs), object detection, speech-to-text, and semantic Vector RAG—all orchestrated concurrently without blocking the main Python thread.

## System Architecture & Modules

The project is structured into highly cohesive, decoupled modules coordinated by a strict State Machine.

*   **`main.py` (Central Nervous System):** 
    Acts as the multi-threading orchestrator. It manages the `AgentState` (IDLE, LISTENING, THINKING, SPEAKING) to prevent race conditions (e.g., the AI interrupting itself). It also securely routes signals between the background AI tasks and the frontend PyQt5 UI.
*   **`brain/brain.py` (Cognitive Core & RAG):** 
    Houses the integration with `Qwen2.5:7b`. It features a custom Vector RAG implementation using ChromaDB and Ollama Embeddings (`nomic-embed-text`) for long-term semantic memory. It utilizes Deterministic Keyword Routing (`vision`, `internet`) to trigger tools with absolute reliability, eliminating LLM hallucination during tool calls.
*   **`eye/eye.py` (Vision & Motion Detection):** 
    Runs a background OpenCV loop powered by YOLOv10-nano and `face_recognition`. It calculates Gaze Tracking using an Exponential Moving Average (EMA) low-pass filter to eliminate jitter. It also features a "Turbulence Detection" algorithm that recognizes rapid motion (like waving) and triggers proactive interactions.
*   **`face/face.py` (True Geometry UI):** 
    A lightweight, frameless PyQt5 window (800x480) that renders the AI's "eyes". It uses dynamic geometric clipping (`QPainterPath`) to smoothly animate emotions (Happy, Sad, Normal) and natural blinking cycles without relying on pre-rendered GIFs.
*   **`audio/audio.py` (I/O Speech System):** 
    Utilizes `faster-whisper` (CUDA) for blazing-fast Speech-to-Text and Silero TTS for text synthesis. To bypass the Python Global Interpreter Lock (GIL) and prevent UI freezing, the audio playback is offloaded directly to the OS kernel via the `aplay` command, layered with a custom Sci-Fi ring modulation effect.
*   **`tools/web_search.py` (Internet Adapter):** 
    Integrates `duckduckgo_search` (DDGS) to pull text snippets. By filtering out raw HTML and relying on search snippets, it feeds highly condensed, relevant facts to the LLM without overflowing the context window.

## Tech Stack & Tools

*   **Core LLM & VLM:** Ollama, Qwen2.5:7b, MiniCPM-V
*   **Vector Database (RAG):** ChromaDB, Nomic-Embed-Text
*   **Computer Vision:** OpenCV, Ultralytics (YOLOv10-nano), `face_recognition`
*   **Audio Processing:** Faster-Whisper, Silero TTS, `sounddevice`, `scipy`
*   **GUI:** PyQt5
*   **Web Search:** DuckDuckGo Search (`duckduckgo-search`)
*   **Hardware Interaction:** `evdev` (Kernel-level spacebar monitoring)

## Hardware Requirements & Memory Allocation

This prototype is heavily optimized for localized execution on modern NVIDIA GPUs. The current configuration is tailored for an **NVIDIA RTX 5080 (16GB VRAM)**.

To maximize performance and isolate dependencies, the Ollama backend is containerized using Apptainer (`ollama.sif`), listening on `localhost:11434`.

### VRAM Budget Breakdown (16GB Limit)

Running a multimodal agent requires careful VRAM orchestration. The system distributes the load as follows:

1.  **Qwen2.5:7b (Ollama):** ~5.5 GB (4-bit/8-bit quantization)
    *   *Primary reasoning engine and conversational core.*
2.  **MiniCPM-V (Ollama):** ~6.0 GB
    *   *Loaded dynamically for deep visual analysis when the `vision` keyword is triggered.*
3.  **Faster-Whisper (`small.en`):** ~1.0 GB
    *   *Kept resident on CUDA for instant voice transcription.*
4.  **YOLOv10-nano & Face Recognition:** ~0.5 GB
    *   *Extremely lightweight footprint for continuous real-time object tracking.*
5.  **Nomic-Embed-Text:** ~0.3 GB
    *   *Used seamlessly for ChromaDB semantic memory storage.*
6.  **OS/Display Overhead:** ~1.5 GB

*Total Peak VRAM Usage: ~14.8 GB / 16.0 GB*

## Setup & Execution

### 1. Prerequisites
Ensure you have Python 3.10+, CUDA toolkit installed, and the Ollama Apptainer image (`ollama.sif`) running locally.

```bash
# Start Ollama via Apptainer
apptainer run --nv ollama.sif serve
```

### 2. Pull Required Models
```bash
ollama pull qwen2.5:7b
ollama pull minicpm-v
ollama pull nomic-embed-text
```
Or you can use ```curl``` to pull:

```bash
curl http://localhost:11434/api/pull -d '{"name": "qwen2.5:7b"}'
curl http://localhost:11434/api/pull -d '{"name": "minicpm-v"}'
curl http://localhost:11434/api/pull -d '{"name": "nomic-embed-text"}'
```

### 3. Install Other Ubuntu Package
```bash
# This is for Ubuntu 26.04, these package may have differents names on older versions
sudo apt install libportaudio2 portaudio19-dev -y
sudo apt install cmake build-essential libgl1 libglib2.0-0 -y

```

### 4. Install Python Dependencies
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirement.txt
sudo chmod a+rw /dev/input/event*
```

## Usage Guidelines

*   **Push-to-Talk:** ~~Press and hold the ```[SPACEBAR]``` to communicate with the Assistant.~~ Say ```"Hey Prototype 1"``` to wake up the system.
*   **Deep Vision:** Say the keyword ```"vision"``` in your prompt (For example: "Use vision to tell me what I am holding") to explicitly route the frame to MiniCPM-V.
*   **Web Search:** Say the keyword ```"internet"``` (For example: "Search the internet for the current CEO of NVIDIA") to route the query to DuckDuckGo and bypass outdated LLM knowledge.
*   **Motion Interaction:** Wave or move rapidly side-to-side in front of the camera while the agent is ```"IDLE```" to trigger a proactive greeting.

*Disclaimer: Prototype 1 is an experimental build. Future iterations aim to replace the hardware key monitor with a continuous Wake-Word engine.*

## History of Development
* **```v1.0.0```:** Developed and tested basic feature for the Prototype 1
* **```v1.0.1```:** Added Wak-up mechanism by saying ```"Hey Prototype 1"```. Fixed problems of Audio by creating chunk of audios. Upgraded the system to optimize the performace by applying I/O Waiting và Non-blocking Memory.