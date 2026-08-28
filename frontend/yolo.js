// ==========================================
// PROTOTYPE WEB - VISION SYSTEM (TFJS)
// ==========================================

class VisionSystem {
    constructor() {
        this.videoElement = null;
        this.canvasElement = null;
        this.model = null;
        this.isRunning = false;

        // Gaze Tracking filtering (Exponential Moving Average)
        this.filteredCx = 0.5;
        this.filteredCy = 0.5;
        this.alpha = 0.15; // Smoothness factor (lower = smoother but slower)

        console.log("[VISION] Initializing Vision System...");
        this.init();
    }

    async init() {
        try {
            // 1. Create a hidden video element to capture webcam stream
            this.videoElement = document.createElement('video');
            this.videoElement.style.display = 'none';
            this.videoElement.setAttribute('autoplay', '');
            this.videoElement.setAttribute('muted', '');
            this.videoElement.setAttribute('playsinline', '');
            document.body.appendChild(this.videoElement);

            // 2. Create a hidden canvas for capturing frames (Base64)
            this.canvasElement = document.createElement('canvas');
            this.canvasElement.style.display = 'none';
            document.body.appendChild(this.canvasElement);

            // 3. Request Webcam Access
            const stream = await navigator.mediaDevices.getUserMedia({
                video: { width: 640, height: 480, facingMode: "user" },
                audio: false
            });
            this.videoElement.srcObject = stream;

            // Wait for video to be ready
            await new Promise((resolve) => {
                this.videoElement.onloadedmetadata = () => {
                    this.videoElement.play();
                    resolve();
                };
            });

            // Set canvas dimensions to match video
            this.canvasElement.width = this.videoElement.videoWidth;
            this.canvasElement.height = this.videoElement.videoHeight;

            console.log("[VISION] Webcam stream active.");

            // 4. Load TensorFlow.js Object Detection Model (COCO-SSD)
            // Note: Make sure tfjs and coco-ssd scripts are included in index.html
            console.log("[VISION] Loading Object Detection Model...");
            this.model = await cocoSsd.load();
            console.log("[VISION] Model loaded. Vision Loop starting.");

            this.isRunning = true;
            this.detectLoop();

        } catch (err) {
            console.error("[VISION ERROR] Failed to initialize webcam or model:", err);
        }
    }

    async detectLoop() {
        if (!this.isRunning || !this.model) return;

        try {
            // Run inference on the current video frame
            const predictions = await this.model.detect(this.videoElement);
            
            let targetFound = false;
            let rawCx = 0.5;
            let rawCy = 0.5;

            if (predictions.length > 0) {
                // Find the largest object (or prioritize 'person')
                let largestArea = 0;
                let bestMatch = null;

                for (const pred of predictions) {
                    const [x, y, width, height] = pred.bbox;
                    const area = width * height;

                    // Boost priority for humans
                    const score = pred.class === 'person' ? area * 1.5 : area;

                    if (score > largestArea) {
                        largestArea = score;
                        bestMatch = pred;
                    }
                }

                if (bestMatch) {
                    const [x, y, width, height] = bestMatch.bbox;
                    // Calculate center normalized coordinates (0.0 to 1.0)
                    rawCx = (x + width / 2) / this.videoElement.videoWidth;
                    rawCy = (y + height / 2) / this.videoElement.videoHeight;
                    targetFound = true;
                }
            }

            // Apply Exponential Moving Average (EMA) for smooth eye movement
            if (targetFound) {
                this.filteredCx = this.alpha * rawCx + (1 - this.alpha) * this.filteredCx;
                this.filteredCy = this.alpha * rawCy + (1 - this.alpha) * this.filteredCy;
            } else {
                // Slowly drift back to center if nothing is found
                const driftAlpha = 0.05;
                this.filteredCx = driftAlpha * 0.5 + (1 - driftAlpha) * this.filteredCx;
                this.filteredCy = driftAlpha * 0.5 + (1 - driftAlpha) * this.filteredCy;
            }

            // Convert to Gaze Coordinates (-1.0 to 1.0)
            // X is inverted so the eyes follow you like a mirror
            const gazeX = -((this.filteredCx * 2) - 1.0);
            const gazeY = (this.filteredCy * 2) - 1.0;

            // Send coordinates to the Face UI if it exists
            if (window.FaceUI) {
                window.FaceUI.setGaze(gazeX, gazeY);
            }

        } catch (err) {
            console.error("[VISION ERROR] Detection loop failed:", err);
        }

        // Keep the loop running at monitor refresh rate
        requestAnimationFrame(() => this.detectLoop());
    }

    captureFrameBase64() {
        if (!this.videoElement || !this.canvasElement) {
            console.error("[VISION ERROR] Cannot capture frame, system not ready.");
            return "";
        }

        // Draw current video frame to hidden canvas
        const ctx = this.canvasElement.getContext('2d');
        ctx.drawImage(this.videoElement, 0, 0, this.canvasElement.width, this.canvasElement.height);
        
        // Export to Base64 (JPEG, 80% quality to save bandwidth)
        const dataUrl = this.canvasElement.toDataURL('image/jpeg', 0.8);
        return dataUrl; // Returns "data:image/jpeg;base64,..."
    }
}

// Export to global window object so app.js can access it
window.addEventListener('load', () => {
    window.VisionSys = new VisionSystem();
});