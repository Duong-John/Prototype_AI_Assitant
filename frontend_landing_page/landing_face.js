class LandingFaceUI {
    constructor() {
        this.canvas = document.getElementById('bg-canvas');
        this.ctx = this.canvas.getContext('2d');
        
        this.currentGazeX = 0.0;
        this.currentGazeY = 0.0;
        this.targetGazeX = 0.0;
        this.targetGazeY = 0.0;
        this.maxGazeOffset = 180;
        
        this.isBlinking = false;
        this.topCut = 0.0;
        
        this.prototypeBlue = "#42a5f5";

        window.addEventListener('resize', () => this.resizeCanvas());
        
        // MOUSE TRACKING LISTENER
        window.addEventListener('mousemove', (e) => this.handleMouseMove(e));
        
        this.init();
    }

    init() {
        this.resizeCanvas();
        this.scheduleBlink();
        this.renderLoop();
    }

    resizeCanvas() {
        const dpr = window.devicePixelRatio || 1;
        this.canvas.width = window.innerWidth * dpr;
        this.canvas.height = window.innerHeight * dpr;
        this.ctx.scale(dpr, dpr);
    }

    handleMouseMove(event) {
        const mouseX = event.clientX;
        const mouseY = event.clientY;
        
        const centerX = window.innerWidth / 2;
        const centerY = window.innerHeight / 2;

        const normX = (mouseX - centerX) / centerX;
        const normY = (mouseY - centerY) / centerY;

        this.targetGazeX = normX;
        this.targetGazeY = normY;
    }

    scheduleBlink() {
        const nextBlink = Math.floor(Math.random() * (5000 - 2000 + 1) + 2000);
        setTimeout(() => this.startBlink(), nextBlink);
    }

    startBlink() {
        this.isBlinking = true;
        setTimeout(() => {
            this.isBlinking = false;
            this.scheduleBlink();
        }, 150);
    }

    updatePhysics() {
        // Smooth Gaze
        this.currentGazeX += (this.targetGazeX - this.currentGazeX) * 0.05;
        this.currentGazeY += (this.targetGazeY - this.currentGazeY) * 0.05;

        // Smooth Blink
        let targetTop = this.isBlinking ? 280 : 0;
        this.topCut += (targetTop - this.topCut) * (this.isBlinking ? 0.6 : 0.15);
    }

    drawEye(cx, cy, w, h) {
        this.ctx.save();
        this.ctx.translate(cx, cy);

        const visibleY = -h / 2 + this.topCut;
        const visibleH = Math.max(0, h - this.topCut);

        this.ctx.beginPath();
        this.ctx.rect(-w, visibleY, w * 2, visibleH);
        this.ctx.clip(); 

        // Vẽ con mắt
        this.ctx.beginPath();
        this.ctx.roundRect(-w / 2, -h / 2, w, h, 80);
        this.ctx.fillStyle = this.prototypeBlue;
        this.ctx.fill();

        this.ctx.restore();
    }

    renderLoop() {
        this.updatePhysics();

        this.ctx.clearRect(0, 0, window.innerWidth, window.innerHeight);

        const eyeW = 160;
        const eyeH = 280;
        const eyeSpacing = 320;
        const centerX = window.innerWidth / 2;
        const centerY = window.innerHeight / 2;
        
        const gazeOffsetX = this.currentGazeX * this.maxGazeOffset;
        const gazeOffsetY = this.currentGazeY * this.maxGazeOffset;

        this.drawEye(centerX - eyeSpacing / 2 + gazeOffsetX, centerY + gazeOffsetY, eyeW, eyeH);
        this.drawEye(centerX + eyeSpacing / 2 + gazeOffsetX, centerY + gazeOffsetY, eyeW, eyeH);

        requestAnimationFrame(() => this.renderLoop());
    }
}

window.addEventListener('load', () => {
    new LandingFaceUI();
});