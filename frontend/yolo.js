// ==========================================
// PROTOTYPE WEB - VISION SYSTEM (DELEGATED TO WORKER)
// ==========================================

class VisionSystem {
    constructor() {
        this.videoElement = null;
        
        this.captureCanvas = null;
        this.captureCtx = null;
        
        this.processCanvas = null;
        this.processCtx = null;

        this.worker = null;
        this.isWorkerReady = false;
        this.isDetecting = false;

        // Gaze Tracking
        this.filteredCx = 0.5;
        this.filteredCy = 0.5;
        this.alpha = 0.15;

        console.log("[VISION] Initializing Delegated Vision System...");
        this.init();
    }

    async init() {
        try {
            this.videoElement = document.createElement('video');
            this.videoElement.style.display = 'none';
            this.videoElement.autoplay = true;
            this.videoElement.muted = true;
            this.videoElement.playsInline = true;
            document.body.appendChild(this.videoElement);

            this.captureCanvas = document.createElement('canvas');
            this.captureCanvas.style.display = 'none';
            this.captureCtx = this.captureCanvas.getContext('2d');
            document.body.appendChild(this.captureCanvas);

            // Optimize: Small Canvas (320x240) for Quick Tracking
            this.processCanvas = document.createElement('canvas');
            this.processCtx = this.processCanvas.getContext('2d', { willReadFrequently: true });
            this.processCanvas.width = 320;
            this.processCanvas.height = 240;

            const stream = await navigator.mediaDevices.getUserMedia({
                video: { width: 640, height: 480, facingMode: "user" },
                audio: false
            });
            this.videoElement.srcObject = stream;

            await new Promise((resolve) => {
                this.videoElement.onloadedmetadata = () => {
                    this.videoElement.play();
                    resolve();
                };
            });

            this.captureCanvas.width = this.videoElement.videoWidth;
            this.captureCanvas.height = this.videoElement.videoHeight;

            console.log("[VISION] Webcam active. Booting Background AI Worker...");
            
            // Init Web Worker
            this.worker = new Worker('worker.js');
            this.worker.onmessage = (e) => this.handleWorkerMessage(e);

        } catch (err) {
            console.error("[VISION ERROR] Initialization failed:", err);
        }
    }

    handleWorkerMessage(e) {
        if (e.data.type === 'STATUS' && e.data.status === 'READY') {
            this.isWorkerReady = true;
            this.startDetectionLoop();
        } 
        else if (e.data.type === 'RESULT') {
            this.isDetecting = false; // Unlock for the next frame
            
            if (e.data.found) {
                this.filteredCx = this.alpha * e.data.cx + (1 - this.alpha) * this.filteredCx;
                this.filteredCy = this.alpha * e.data.cy + (1 - this.alpha) * this.filteredCy;
            } else {
                const driftAlpha = 0.05;
                this.filteredCx = driftAlpha * 0.5 + (1 - driftAlpha) * this.filteredCx;
                this.filteredCy = driftAlpha * 0.5 + (1 - driftAlpha) * this.filteredCy;
            }

            const gazeX = -((this.filteredCx * 2) - 1.0);
            const gazeY = (this.filteredCy * 2) - 1.0;

            if (window.FaceUI) {
                window.FaceUI.setGaze(gazeX, gazeY);
            }
        }
    }

    startDetectionLoop() {
        // Limit: 15 times/second (66ms) for smoothness
        setInterval(() => {
            if (!this.isWorkerReady || this.isDetecting) return;
            
            this.isDetecting = true; // Lock
            
            // Draw frame video to canvas with low resolution
            this.processCtx.drawImage(this.videoElement, 0, 0, this.processCanvas.width, this.processCanvas.height);
            
            // process pixel
            const imageData = this.processCtx.getImageData(0, 0, this.processCanvas.width, this.processCanvas.height);
            
            // Forward to worker.js
            this.worker.postMessage({
                type: 'DETECT',
                imageData: imageData,
                width: this.processCanvas.width,
                height: this.processCanvas.height
            });

        }, 66);
    }

    captureFrameBase64() {
        if (!this.videoElement || !this.captureCanvas) return "";
        // Backend LLM captureCanvas high res
        this.captureCtx.drawImage(this.videoElement, 0, 0, this.captureCanvas.width, this.captureCanvas.height);
        return this.captureCanvas.toDataURL('image/jpeg', 0.8);
    }
}

window.addEventListener('load', () => {
    window.VisionSys = new VisionSystem();
});