// ==========================================
// PROTOTYPE WEB - FACE UI (HTML5 CANVAS)
// ==========================================

class FaceUI {
    constructor() {
        console.log("[FACE UI] Initializing Canvas UI...");
        
        // Setup Canvas
        this.canvas = document.createElement('canvas');
        this.ctx = this.canvas.getContext('2d');
        this.canvas.style.display = 'block';
        this.canvas.style.width = '100vw';
        this.canvas.style.height = '100vh';
        this.canvas.style.backgroundColor = 'black';
        document.body.appendChild(this.canvas);
        
        // Remove margins/padding on body to ensure full screen
        document.body.style.margin = '0';
        document.body.style.overflow = 'hidden';

        // Physics Variables
        this.currentGazeX = 0.0;
        this.currentGazeY = 0.0;
        this.targetGazeX = 0.0;
        this.targetGazeY = 0.0;
        this.maxGazeOffset = 300;

        // Eyelid Cuts
        this.topCut = 0.0;
        this.botCut = 0.0;
        this.emotionTargetTop = 0.0;
        this.emotionTargetBot = 0.0;
        this.isBlinking = false;
        
        // Core Colors
        this.prototypeBlue = "#42a5f5";

        // Bind resize event
        window.addEventListener('resize', () => this.resizeCanvas());
        
        this.init();
    }

    init() {
        this.resizeCanvas();
        this.scheduleBlink();
        this.renderLoop();
    }

    resizeCanvas() {
        // Handle high-DPI displays (Retina screens) for crisp rendering
        const dpr = window.devicePixelRatio || 1;
        this.canvas.width = window.innerWidth * dpr;
        this.canvas.height = window.innerHeight * dpr;
        this.ctx.scale(dpr, dpr);
    }

    // --- STATE SETTERS ---
    setGaze(x, y) {
        // Map Gaze coordinates (-1.0 to 1.0), amplifying slightly
        this.targetGazeX = Math.max(-1.0, Math.min(1.0, x * 1.3));
        this.targetGazeY = Math.max(-1.0, Math.min(1.0, y * 1.3));
    }

    setEmotion(emotion) {
        if (emotion === "normal") {
            this.emotionTargetTop = 0;
            this.emotionTargetBot = 0;
        } else if (emotion === "happy") {
            this.emotionTargetTop = 0;
            this.emotionTargetBot = 40;
        } else if (emotion === "sad") {
            this.emotionTargetTop = 40;
            this.emotionTargetBot = 0;
        }
    }

    // --- BLINK LOGIC ---
    scheduleBlink() {
        // Random interval between 2s and 6s
        const nextBlink = Math.floor(Math.random() * (6000 - 2000 + 1) + 2000);
        setTimeout(() => this.startBlink(), nextBlink);
    }

    startBlink() {
        this.isBlinking = true;
        // Blink duration is 150ms
        setTimeout(() => {
            this.isBlinking = false;
            this.scheduleBlink();
        }, 150);
    }

    // --- PHYSICS & RENDERING ---
    updatePhysics() {
        // 1. Smooth Gaze Movement (Linear Interpolation)
        const gazeSmoothness = 0.1;
        this.currentGazeX += (this.targetGazeX - this.currentGazeX) * gazeSmoothness;
        this.currentGazeY += (this.targetGazeY - this.currentGazeY) * gazeSmoothness;

        // 2. Smooth Eyelid Movement
        let targetTop, targetBot, cutSmoothness;
        
        if (this.isBlinking) {
            targetTop = 280; // Full height of eye
            targetBot = 0;
            cutSmoothness = 0.6; // Fast blink down
        } else {
            targetTop = this.emotionTargetTop;
            targetBot = this.emotionTargetBot;
            cutSmoothness = 0.15; // Smooth emotion transition
        }

        this.topCut += (targetTop - this.topCut) * cutSmoothness;
        this.botCut += (targetBot - this.botCut) * cutSmoothness;
    }

    drawTrueGeometryEye(cx, cy, w, h, color) {
        this.ctx.save();
        this.ctx.translate(cx, cy);

        // Calculate visible bounding box after clipping
        const visibleY = -h / 2 + this.topCut;
        const visibleH = Math.max(0, h - this.topCut - this.botCut);

        // Setup Eyelid Clipping Region (Mimics QPainterPath.intersected)
        this.ctx.beginPath();
        this.ctx.rect(-w, visibleY, w * 2, visibleH);
        this.ctx.clip(); // Everything drawn after this will be constrained to this box

        // Draw the base rounded rectangle eye
        this.ctx.beginPath();
        // ctx.roundRect(x, y, width, height, radii) - Modern Canvas API
        this.ctx.roundRect(-w / 2, -h / 2, w, h, 80);
        
        this.ctx.fillStyle = color;
        this.ctx.fill();

        this.ctx.restore();
    }

    renderLoop() {
        this.updatePhysics();

        // Clear previous frame
        this.ctx.fillStyle = 'black';
        this.ctx.fillRect(0, 0, window.innerWidth, window.innerHeight);

        // Core Dimensions (Matching face.py)
        const eyeW = 160;
        const eyeH = 280;
        const eyeSpacing = 300;
        const centerX = window.innerWidth / 2;
        const centerY = window.innerHeight / 2;
        
        // Calculate Gaze Offsets
        const gazeOffsetX = this.currentGazeX * this.maxGazeOffset;
        const gazeOffsetY = this.currentGazeY * this.maxGazeOffset;

        // Draw Left Eye
        this.drawTrueGeometryEye(
            centerX - eyeSpacing / 2 + gazeOffsetX, 
            centerY + gazeOffsetY, 
            eyeW, 
            eyeH, 
            this.prototypeBlue
        );

        // Draw Right Eye
        this.drawTrueGeometryEye(
            centerX + eyeSpacing / 2 + gazeOffsetX, 
            centerY + gazeOffsetY, 
            eyeW, 
            eyeH, 
            this.prototypeBlue
        );

        // Queue next frame
        requestAnimationFrame(() => this.renderLoop());
    }
}

// Export to global window object
window.addEventListener('load', () => {
    window.FaceUI = new FaceUI();
});