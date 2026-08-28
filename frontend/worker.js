// ==========================================
// PROTOTYPE WEB - BACKGROUND AI WORKER
// ==========================================

// Import TFJS and COCO-SSD directly into the worker thread
importScripts('https://cdn.jsdelivr.net/npm/@tensorflow/tfjs');
importScripts('https://cdn.jsdelivr.net/npm/@tensorflow-models/coco-ssd');

let model = null;

// Khởi chạy model ngầm
cocoSsd.load().then(loadedModel => {
    model = loadedModel;
    console.log("[WORKER] COCO-SSD Model Loaded successfully.");
    postMessage({ type: 'STATUS', status: 'READY' });
});

// Lắng nghe yêu cầu từ luồng chính
onmessage = async (e) => {
    if (!model) return;
    
    if (e.data.type === 'DETECT') {
        const { imageData, width, height } = e.data;

        try {
            // TFJS có thể phân tích trực tiếp đối tượng ImageData
            const predictions = await model.detect(imageData);
            
            let bestMatch = null;
            let largestArea = 0;

            for (const pred of predictions) {
                const [x, y, w, h] = pred.bbox;
                const area = w * h;
                const score = pred.class === 'person' ? area * 1.5 : area;
                
                if (score > largestArea) {
                    largestArea = score;
                    bestMatch = pred;
                }
            }

            if (bestMatch) {
                const [x, y, w, h] = bestMatch.bbox;
                const rawCx = (x + w / 2) / width;
                const rawCy = (y + h / 2) / height;
                
                postMessage({ type: 'RESULT', found: true, cx: rawCx, cy: rawCy });
            } else {
                postMessage({ type: 'RESULT', found: false });
            }
        } catch (err) {
            console.error("[WORKER ERROR]", err);
            // Giải phóng khóa (lock) để luồng chính tiếp tục gửi frame
            postMessage({ type: 'RESULT', found: false }); 
        }
    }
};