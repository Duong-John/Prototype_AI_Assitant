// ==========================================
// PROTOTYPE WEB - CORE ORCHESTRATOR
// ==========================================

// TODO: Replace with your actual Render WebSocket URL (e.g., wss://prototype-backend-xxxx.onrender.com/ws/chat)
const WS_URL = "wss://prototype-backend-2jkf.onrender.com/ws/chat";
// const USER_EMAIL = "tester@hcmut.edu.vn"; // Hardcoded for testing Cloudflare Zero-Trust logic

// System Variables
let socket;
let mediaRecorder;
let audioChunks = [];
let isRecording = false;

// Agent State Machine
const AgentState = {
    IDLE: 'IDLE',
    LISTENING: 'LISTENING',
    THINKING: 'THINKING',
    SPEAKING: 'SPEAKING'
};
let currentState = AgentState.IDLE;

// ==========================================
// 1. WEBSOCKET SIGNALING
// ==========================================
function initWebSocket() {
    console.log("[SYSTEM] Initializing WebSocket connection...");
    socket = new WebSocket(WS_URL);

    socket.onopen = () => {
        console.log("[SYSTEM] WebSocket connected successfully.");
    };

    socket.onmessage = async (event) => {
        const data = JSON.parse(event.data);

        if (data.type === "status") {
            console.log(`[STATUS] ${data.status}`);
            if (data.status === "analyzing_vision" && window.FaceUI) {
                window.FaceUI.setEmotion("sad"); // Squinting/focusing emotion
            }
        } 
        else if (data.type === "response") {
            currentState = AgentState.SPEAKING;
            console.log(`[PROTOTYPE]: ${data.text}`);

            // 1. Update Emotion
            if (window.FaceUI) {
                window.FaceUI.setEmotion(data.emotion);
            }

            // 2. Play Audio Synthesis
            if (data.audio_b64) {
                await playAudioBase64(data.audio_b64);
            }

            // 3. Return to IDLE state after speaking
            currentState = AgentState.IDLE;
            if (window.FaceUI) {
                window.FaceUI.setEmotion("normal");
            }
        } 
        else if (data.error) {
            console.error(`[SYSTEM ERROR] ${data.error}`);
            currentState = AgentState.IDLE;
            if (window.FaceUI) window.FaceUI.setEmotion("normal");
        }
    };

    socket.onclose = () => {
        console.warn("[SYSTEM] WebSocket disconnected. Reconnecting in 3 seconds...");
        setTimeout(initWebSocket, 3000);
    };
}

// ==========================================
// 2. AUDIO I/O (MEDIA RECORDER)
// ==========================================
async function initAudio() {
    try {
        const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
        
        // Use webm for broad browser compatibility
        mediaRecorder = new MediaRecorder(stream, { mimeType: 'audio/webm' });

        mediaRecorder.ondataavailable = (event) => {
            if (event.data.size > 0) {
                audioChunks.push(event.data);
            }
        };

        mediaRecorder.onstop = async () => {
            const audioBlob = new Blob(audioChunks, { type: 'audio/webm' });
            audioChunks = [];

            const base64Audio = await blobToBase64(audioBlob);
            
            // Extract a frame from YOLO module if it exists
            let base64Image = "";
            if (window.VisionSys) {
                base64Image = window.VisionSys.captureFrameBase64();
            }

            sendToBackend(base64Audio, base64Image);
        };
        console.log("[SYSTEM] Microphone access granted. Audio Pipeline Ready.");

    } catch (err) {
        console.error("[SYSTEM ERROR] Microphone access denied or failed:", err);
    }
}

function sendToBackend(audioB64, imageB64) {
    if (!socket || socket.readyState !== WebSocket.OPEN) {
        console.error("[SYSTEM ERROR] WebSocket is not open.");
        return;
    }

    currentState = AgentState.THINKING;
    if (window.FaceUI) window.FaceUI.setEmotion("sad"); // Processing face

    // Strip the Data URI scheme prefix (data:audio/webm;base64,...)
    const cleanAudioB64 = audioB64.split(',')[1] || audioB64;
    const cleanImageB64 = imageB64 ? (imageB64.split(',')[1] || imageB64) : "";

    const payload = {
        action: "process",
        email: USER_EMAIL,
        audio_b64: cleanAudioB64,
        image_b64: cleanImageB64
    };

    socket.send(JSON.stringify(payload));
    console.log("[SYSTEM] Payload transmitted to backend.");
}

// ==========================================
// 3. HARDWARE INTERACTION (PUSH TO TALK)
// ==========================================
window.addEventListener('keydown', (e) => {
    if (e.code === 'Space' && !isRecording && currentState === AgentState.IDLE) {
        isRecording = true;
        currentState = AgentState.LISTENING;
        audioChunks = [];
        
        mediaRecorder.start();
        console.log("[AUDIO] Listening (Spacebar held)...");
        
        if (window.FaceUI) window.FaceUI.setEmotion("happy"); 
    }
});

window.addEventListener('keyup', (e) => {
    if (e.code === 'Space' && isRecording) {
        isRecording = false;
        mediaRecorder.stop();
        console.log("[AUDIO] Recording stopped. Packaging data...");
    }
});

// ==========================================
// 4. HELPER FUNCTIONS
// ==========================================
function blobToBase64(blob) {
    return new Promise((resolve, reject) => {
        const reader = new FileReader();
        reader.onloadend = () => resolve(reader.result);
        reader.onerror = reject;
        reader.readAsDataURL(blob);
    });
}

async function playAudioBase64(base64String) {
    return new Promise((resolve) => {
        // Render backend returns WAV format
        const audio = new Audio("data:audio/wav;base64," + base64String);
        audio.onended = resolve;
        audio.play().catch(e => {
            console.error("[AUDIO ERROR] Playback failed (Browser Auto-play policy?):", e);
            resolve(); // Resolve to free the state machine
        });
    });
}

function getCloudflareEmail() {
    try {
        const cookies = document.cookie.split(';');
        const cfCookie = cookies.find(c => c.trim().startsWith('CF_Authorization='));
        
        // Fallback for Localhost testing (no Cloudflare wrapper)
        if (!cfCookie) return "local_dev@hcmut.edu.vn"; 

        const token = cfCookie.split('=')[1];
        const payloadBase64 = token.split('.')[1];
        // Decode Base64 JWT Payload
        const decodedPayload = JSON.parse(atob(payloadBase64));
        
        return decodedPayload.email || "unknown@hcmut.edu.vn";
    } catch (e) {
        console.warn("[SYSTEM] Could not decode Cloudflare Identity.");
        return "guest@hcmut.edu.vn";
    }
}

const USER_EMAIL = getCloudflareEmail();
console.log(`[SYSTEM] Authenticated as: ${USER_EMAIL}`);

// ==========================================
// BOOT SEQUENCE
// ==========================================
window.addEventListener('load', () => {
    console.log("==========================================");
    console.log(" PROTOTYPE WEB UI BOOTING...");
    console.log("==========================================");
    initWebSocket();
    initAudio();
});