let lastVector = [0, 0];
let canvas, ctx;
const SCALE_FACTOR = 1;  // Adjust this to scale the vector visualization
const UPDATE_INTERVAL = 50;  // Update every 50ms

function initCanvas() {
    canvas = document.getElementById('vectorCanvas');
    ctx = canvas.getContext('2d');
    
    // Set canvas size
    canvas.width = 400;
    canvas.height = 400;
    
    // Initial draw
    drawVector();
}

function drawVector() {
    // Clear canvas
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    
    // Draw grid lines
    ctx.strokeStyle = '#363636';
    ctx.lineWidth = 1;
    
    // Vertical and horizontal lines
    for(let i = 0; i <= canvas.width; i += 40) {
        ctx.beginPath();
        ctx.moveTo(i, 0);
        ctx.lineTo(i, canvas.height);
        ctx.stroke();
        
        ctx.beginPath();
        ctx.moveTo(0, i);
        ctx.lineTo(canvas.width, i);
        ctx.stroke();
    }
    
    // Draw center point
    const centerX = canvas.width / 2;
    const centerY = canvas.height / 2;
    
    // Draw center crosshair
    ctx.strokeStyle = '#00ff88';
    ctx.lineWidth = 1;
    
    ctx.beginPath();
    ctx.moveTo(centerX - 10, centerY);
    ctx.lineTo(centerX + 10, centerY);
    ctx.moveTo(centerX, centerY - 10);
    ctx.lineTo(centerX, centerY + 10);
    ctx.stroke();
    
    ctx.beginPath();
    ctx.arc(centerX, centerY, 5, 0, 2 * Math.PI);
    ctx.fillStyle = '#00ff88';
    ctx.fill();
    
    // Draw vector with glow effect
    ctx.shadowBlur = 10;
    ctx.shadowColor = '#00ff88';
    
    ctx.beginPath();
    ctx.moveTo(centerX, centerY);
    ctx.lineTo(
        centerX + (lastVector[0] * SCALE_FACTOR),
        centerY + (lastVector[1] * SCALE_FACTOR)
    );
    ctx.strokeStyle = '#00ff88';
    ctx.lineWidth = 2;
    ctx.stroke();
    
    // Draw vector end point
    ctx.beginPath();
    ctx.arc(
        centerX + (lastVector[0] * SCALE_FACTOR),
        centerY + (lastVector[1] * SCALE_FACTOR),
        4, 0, 2 * Math.PI
    );
    ctx.fillStyle = '#00ff88';
    ctx.fill();
    
    // Reset shadow
    ctx.shadowBlur = 0;
}

function updateVectorDisplay(vector) {
    document.getElementById('vectorX').textContent = vector[0].toFixed(2);
    document.getElementById('vectorY').textContent = vector[1].toFixed(2);
    lastVector = vector;
    drawVector();
}

function fetchVector() {
    fetch('http://localhost:8000')
        .then(response => response.json())
        .then(data => {
            updateVectorDisplay(data.vector);
        })
        .catch(error => {
            console.error('Error fetching vector:', error);
        });
}

function updateThresholdDisplay(threshold) {
    document.getElementById('thresholdValue').textContent = threshold.toFixed(2);
}

function sendCommand(command) {
    fetch('http://localhost:8000/command', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify(command)
    })
    .then(response => response.json())
    .then(data => {
        console.log('Command response:', data);
        if (data.threshold !== undefined) {
            updateThresholdDisplay(data.threshold);
        }
        if (data.show_filtered !== undefined) {
            document.getElementById('filterBtn').classList.toggle('active', data.show_filtered);
        }
    })
    .catch(error => {
        console.error('Error sending command:', error);
    });
}

// Initialize when page loads
window.onload = function() {
    initCanvas();
    // Start periodic updates
    setInterval(fetchVector, UPDATE_INTERVAL);

    // Add button listeners
    document.getElementById('calibrateBtn').addEventListener('click', () => {
        sendCommand({ action: 'calibrate' });
    });

    document.getElementById('filterBtn').addEventListener('click', () => {
        sendCommand({ action: 'toggle_filter' });
    });

    document.getElementById('thresholdUpBtn').addEventListener('click', () => {
        sendCommand({ action: 'threshold_up' });
    });

    document.getElementById('thresholdDownBtn').addEventListener('click', () => {
        sendCommand({ action: 'threshold_down' });
    });
}; 