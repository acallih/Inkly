/**
 * Inkly - Game Logic
 * Sistema de desenho, canvas e interação com IA
 */

const gameState = {
    playerId: new URLSearchParams(window.location.search).get('player_id'),
    sessionId: null,
    prompt: null,
    timeLimit: 20,
    timeLeft: 20,
    timerInterval: null,
    isDrawing: false,
    hasDrawn: false,
    currentBrush: 'normal',
    currentColor: '#000000',
    brushSize: 8
};

const canvas = document.getElementById('canvas');
const ctx = canvas.getContext('2d');
let isDrawingNow = false;
let lastX = 0;
let lastY = 0;

const colors = [
    '#000000', '#FFFFFF', '#FF0000', '#00FF00', '#0000FF', '#FFFF00',
    '#FF00FF', '#00FFFF', '#FFA500', '#800080', '#FFC0CB', '#8B4513'
];

document.addEventListener('DOMContentLoaded', () => {
    initCanvas();
    initBrushes();
    initColors();
    initRGBSliders();
    loadPlayerData();
    loadNewPrompt();
});

function initCanvas() {
    ctx.lineCap = 'round';
    ctx.lineJoin = 'round';
    
    canvas.addEventListener('mousedown', startDrawingMouse);
    canvas.addEventListener('mousemove', drawMouse);
    canvas.addEventListener('mouseup', stopDrawing);
    canvas.addEventListener('mouseout', stopDrawing);
    
    canvas.addEventListener('touchstart', startDrawingTouch);
    canvas.addEventListener('touchmove', drawTouch);
    canvas.addEventListener('touchend', stopDrawing);
}

function initBrushes() {
    const brushes = [
        {type: 'normal', name: 'Normal', emoji: '🖌️', unlocked: true},
        {type: 'neon', name: 'Neon', emoji: '✨', unlocked: false},
        {type: 'spray', name: 'Spray', emoji: '💨', unlocked: false},
        {type: 'marker', name: 'Marcador', emoji: '🖊️', unlocked: false},
        {type: 'sparkle', name: 'Brilho', emoji: '⭐', unlocked: false}
    ];
    
    const container = document.getElementById('brushes');
    brushes.forEach(brush => {
        const btn = document.createElement('button');
        btn.className = `p-3 rounded-lg text-center transition-all ${
            brush.unlocked 
                ? 'bg-purple-100 hover:bg-purple-200' 
                : 'bg-gray-100 cursor-not-allowed opacity-50'
        }`;
        btn.innerHTML = `<div class="text-2xl">${brush.emoji}</div><div class="text-xs">${brush.name}</div>`;
        btn.disabled = !brush.unlocked;
        btn.onclick = () => selectBrush(brush.type);
        container.appendChild(btn);
    });
}

function initColors() {
    const container = document.getElementById('colorPalette');
    colors.forEach(color => {
        const btn = document.createElement('button');
        btn.className = 'w-8 h-8 rounded-lg border-2 border-gray-300 hover:scale-110 transition-transform';
        btn.style.backgroundColor = color;
        btn.onclick = () => selectColor(color);
        container.appendChild(btn);
    });
}

function initRGBSliders() {
    const rSlider = document.getElementById('colorR');
    const gSlider = document.getElementById('colorG');
    const bSlider = document.getElementById('colorB');
    
    const updateRGB = () => {
        const r = parseInt(rSlider.value);
        const g = parseInt(gSlider.value);
        const b = parseInt(bSlider.value);
        
        document.getElementById('rVal').textContent = r;
        document.getElementById('gVal').textContent = g;
        document.getElementById('bVal').textContent = b;
        
        const color = `rgb(${r}, ${g}, ${b})`;
        document.getElementById('rgbPreview').style.backgroundColor = color;
        selectColor(color);
    };
    
    rSlider.addEventListener('input', updateRGB);
    gSlider.addEventListener('input', updateRGB);
    bSlider.addEventListener('input', updateRGB);
}

async function loadPlayerData() {
    try {
        const response = await fetch(`/api/player/${gameState.playerId}`);
        const player = await response.json();
        
        document.getElementById('level').textContent = `Nv. ${player.level}`;
        document.getElementById('xp').textContent = `${player.xp} XP`;
        document.getElementById('streak').textContent = `${player.streak}🔥`;
        
        player.brushes_unlocked.forEach(brush => {
            const buttons = document.querySelectorAll('#brushes button');
            buttons.forEach(btn => {
                if (btn.textContent.includes(brush)) {
                    btn.disabled = false;
                    btn.classList.remove('opacity-50', 'cursor-not-allowed');
                    btn.classList.add('bg-purple-100', 'hover:bg-purple-200');
                }
            });
        });
    } catch (error) {
        console.error('Erro ao carregar jogador:', error);
    }
}

async function loadNewPrompt() {
    try {
        const response = await fetch('/api/session/start', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({
                player_id: gameState.playerId,
                difficulty: 'medium',
                surprise_mode: true
            })
        });
        
        const data = await response.json();
        gameState.sessionId = data.session_id;
        gameState.prompt = data.prompt.text;
        gameState.timeLimit = data.prompt.time_limit;
        gameState.timeLeft = data.prompt.time_limit;
        
        document.getElementById('prompt').textContent = `Desenhe: ${gameState.prompt}`;
        document.getElementById('timer').textContent = gameState.timeLeft;
        document.getElementById('startBtn').disabled = false;
        updateAIMascot('🤖', 'Pronto para começar?');
        
    } catch (error) {
        console.error('Erro ao carregar prompt:', error);
        alert('Erro ao carregar desafio! 😢');
    }
}

function startDrawing() {
    gameState.isDrawing = true;
    document.getElementById('startBtn').disabled = true;
    document.getElementById('submitBtn').disabled = false;
    document.getElementById('promptCard').classList.add('opacity-50');
    updateAIMascot('👀', 'Estou observando...');
    
    gameState.timerInterval = setInterval(() => {
        gameState.timeLeft--;
        document.getElementById('timer').textContent = gameState.timeLeft;
        
        if (gameState.timeLeft <= 5) {
            document.getElementById('timer').classList.add('text-red-500', 'animate-pulse');
        }
        
        if (gameState.timeLeft <= 0) {
            clearInterval(gameState.timerInterval);
            if (gameState.hasDrawn) {
                submitDrawing();
            } else {
                updateAIMascot('😅', 'O tempo acabou!');
                setTimeout(nextRound, 2000);
            }
        }
    }, 1000);
}

function startDrawingMouse(e) {
    if (!gameState.isDrawing) return;
    isDrawingNow = true;
    gameState.hasDrawn = true;
    [lastX, lastY] = [e.offsetX, e.offsetY];
}

function drawMouse(e) {
    if (!isDrawingNow || !gameState.isDrawing) return;
    draw(e.offsetX, e.offsetY);
}

function startDrawingTouch(e) {
    if (!gameState.isDrawing) return;
    e.preventDefault();
    isDrawingNow = true;
    gameState.hasDrawn = true;
    const touch = e.touches[0];
    const rect = canvas.getBoundingClientRect();
    [lastX, lastY] = [touch.clientX - rect.left, touch.clientY - rect.top];
}

function drawTouch(e) {
    if (!isDrawingNow || !gameState.isDrawing) return;
    e.preventDefault();
    const touch = e.touches[0];
    const rect = canvas.getBoundingClientRect();
    draw(touch.clientX - rect.left, touch.clientY - rect.top);
}

function stopDrawing() {
    isDrawingNow = false;
}

function draw(x, y) {
    ctx.strokeStyle = gameState.currentColor;
    ctx.lineWidth = gameState.brushSize;
    
    ctx.beginPath();
    ctx.moveTo(lastX, lastY);
    ctx.lineTo(x, y);
    ctx.stroke();
    
    if (gameState.currentBrush === 'neon') {
        ctx.shadowBlur = 15;
        ctx.shadowColor = gameState.currentColor;
    } else if (gameState.currentBrush === 'spray') {
        sprayEffect(x, y);
    } else if (gameState.currentBrush === 'sparkle') {
        sparkleEffect(x, y);
    }
    
    [lastX, lastY] = [x, y];
}

function sprayEffect(x, y) {
    for (let i = 0; i < 10; i++) {
        const offsetX = (Math.random() - 0.5) * gameState.brushSize * 2;
        const offsetY = (Math.random() - 0.5) * gameState.brushSize * 2;
        ctx.fillStyle = gameState.currentColor;
        ctx.fillRect(x + offsetX, y + offsetY, 2, 2);
    }
}

function sparkleEffect(x, y) {
    ctx.fillStyle = '#FFD700';
    for (let i = 0; i < 5; i++) {
        const angle = (Math.PI * 2 * i) / 5;
        const sparkleX = x + Math.cos(angle) * 10;
        const sparkleY = y + Math.sin(angle) * 10;
        ctx.fillRect(sparkleX, sparkleY, 3, 3);
    }
}

function selectBrush(type) {
    gameState.currentBrush = type;
    ctx.shadowBlur = 0;
}

function selectColor(color) {
    gameState.currentColor = color;
}

function clearCanvas() {
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    gameState.hasDrawn = false;
}

async function submitDrawing() {
    if (!gameState.hasDrawn) {
        alert('Desenhe algo primeiro! 🎨');
        return;
    }
    
    clearInterval(gameState.timerInterval);
    document.getElementById('submitBtn').disabled = true;
    updateAIMascot('🤔', 'Analisando seu desenho...');
    
    const imageData = canvas.toDataURL('image/png');
    const timeSpent = gameState.timeLimit - gameState.timeLeft;
    
    try {
        const response = await fetch('/api/session/complete', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({
                session_id: gameState.sessionId,
                drawing_data: imageData,
                time_spent: timeSpent
            })
        });
        
        const result = await response.json();
        showResults(result);
        
    } catch (error) {
        console.error('Erro ao enviar desenho:', error);
        alert('Erro ao enviar! 😢');
    }
}

function showResults(result) {
    const modal = document.getElementById('resultModal');
    
    if (result.correct) {
        createConfetti();
        document.getElementById('resultEmoji').textContent = '🎉';
        document.getElementById('resultTitle').textContent = 'Incrível!';
        updateAIMascot('😍', result.feedback);
    } else {
        document.getElementById('resultEmoji').textContent = '🤔';
        document.getElementById('resultTitle').textContent = 'Quase lá!';
        updateAIMascot('😅', result.feedback);
    }
    
    document.getElementById('resultMessage').textContent = result.feedback;
    
    const guessesDiv = document.getElementById('aiGuesses');
    guessesDiv.innerHTML = result.guesses.map((guess, i) => `
        <div class="bg-white rounded-lg p-3 border-2 ${i === 0 ? 'border-purple-400' : 'border-gray-200'}">
            <span class="font-bold">${i + 1}º)</span> ${guess}
            ${i === 0 ? `<span class="text-purple-600">(${result.confidence}% confiança)</span>` : ''}
        </div>
    `).join('');
    
    document.getElementById('scoreVal').textContent = `+${result.score}`;
    document.getElementById('xpVal').textContent = `+${result.xp_gained} XP`;
    
    if (result.achievements && result.achievements.length > 0) {
        document.getElementById('achievementsDisplay').classList.remove('hidden');
        document.getElementById('achievementsList').innerHTML = result.achievements.map(ach => `
            <div class="bg-yellow-100 rounded-lg p-3 mb-2">
                <div class="font-bold">🏆 ${ach.name}</div>
                <div class="text-sm text-gray-600">${ach.description}</div>
            </div>
        `).join('');
        createConfetti();
    }
    
    if (result.level_up) {
        setTimeout(() => {
            alert(`🎊 LEVEL UP! Você alcançou o nível ${result.new_level}! 🎊`);
        }, 500);
    }
    
    document.getElementById('level').textContent = `Nv. ${result.player_stats.level}`;
    document.getElementById('xp').textContent = `${result.player_stats.xp} XP`;
    document.getElementById('streak').textContent = `${result.player_stats.streak}🔥`;
    
    modal.classList.remove('hidden');
    modal.classList.add('flex');
}

function nextRound() {
    document.getElementById('resultModal').classList.add('hidden');
    document.getElementById('achievementsDisplay').classList.add('hidden');
    
    clearCanvas();
    gameState.isDrawing = false;
    gameState.hasDrawn = false;
    document.getElementById('promptCard').classList.remove('opacity-50');
    document.getElementById('timer').classList.remove('text-red-500', 'animate-pulse');
    
    loadNewPrompt();
}

function skipPrompt() {
    if (confirm('Tem certeza que quer pular?')) {
        clearInterval(gameState.timerInterval);
        nextRound();
    }
}

function updateAIMascot(emoji, message) {
    document.getElementById('aiEmoji').textContent = emoji;
    document.getElementById('aiMessage').textContent = message;
}

function createConfetti() {
    const colors = ['#FF0000', '#00FF00', '#0000FF', '#FFFF00', '#FF00FF', '#00FFFF'];
    for (let i = 0; i < 50; i++) {
        setTimeout(() => {
            const confetti = document.createElement('div');
            confetti.className = 'confetti';
            confetti.style.left = Math.random() * window.innerWidth + 'px';
            confetti.style.backgroundColor = colors[Math.floor(Math.random() * colors.length)];
            document.body.appendChild(confetti);
            setTimeout(() => confetti.remove(), 3000);
        }, i * 30);
    }
}

document.getElementById('brushSize').addEventListener('input', (e) => {
    gameState.brushSize = e.target.value;
    document.getElementById('sizeVal').textContent = `${e.target.value}px`;
});