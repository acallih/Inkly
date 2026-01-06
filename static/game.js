/**
 * Inkly - Game Logic
 * Sistema de desenho, canvas e interação com IA
 */

const DEBUG = true; // ATIVAR DEBUG MODE

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

let canvas = null;
let ctx = null;
let isDrawingNow = false;
let lastX = 0;
let lastY = 0;

const colors = [
    '#000000', '#FFFFFF', '#FF0000', '#00FF00', '#0000FF', '#FFFF00',
    '#FF00FF', '#00FFFF', '#FFA500', '#800080', '#FFC0CB', '#8B4513'
];

function log(...args) {
    if (DEBUG) console.log('[INKLY]', ...args);
}

document.addEventListener('DOMContentLoaded', () => {
    initCanvas();
    initBrushes();
    initColors();
    initRGBSliders();
    loadPlayerData();
    loadNewPrompt();
});

function initCanvas() {
    // Obter referencia ao canvas e contexto no momento da inicializacao
    canvas = document.getElementById('canvas');
    if (!canvas) {
        log('ERRO: Canvas element not found!');
        return false;
    }
    
    ctx = canvas.getContext('2d');
    if (!ctx) {
        log('ERRO: Canvas 2D context not available!');
        return false;
    }
    
    log('Canvas obtido e inicializado');
    
    // Garantir que o canvas tem o tamanho correto
    if (canvas.width !== 800 || canvas.height !== 600) {
        canvas.width = 800;
        canvas.height = 600;
    }
    
    // Preencher com fundo branco
    ctx.fillStyle = '#FFFFFF';
    ctx.fillRect(0, 0, canvas.width, canvas.height);
    
    ctx.lineCap = 'round';
    ctx.lineJoin = 'round';
    ctx.shadowBlur = 0;
    ctx.shadowColor = 'rgba(0,0,0,0)';
    
    // Inicializar cor padrao
    gameState.currentColor = '#000000';
    gameState.currentBrush = 'normal';
    gameState.brushSize = 8;
    
    log('Canvas: ' + canvas.width + 'x' + canvas.height + ' pronto para desenhar');
    
    // Teste de desenho - desenhar uma linha de teste
    log('Desenhando linha de teste no canvas');
    ctx.strokeStyle = '#FF0000';
    ctx.lineWidth = 2;
    ctx.beginPath();
    ctx.moveTo(10, 10);
    ctx.lineTo(100, 100);
    ctx.stroke();
    log('Linha de teste desenhada (deve ver uma linha vermelha)');
    
    // Limpar o teste
    setTimeout(() => {
        ctx.fillStyle = '#FFFFFF';
        ctx.fillRect(0, 0, canvas.width, canvas.height);
        log('Canvas limpado apos teste');
    }, 2000);
    
    // Adicionar listeners para mouse
    canvas.addEventListener('mousedown', startDrawingMouse);
    canvas.addEventListener('mousemove', drawMouse);
    canvas.addEventListener('mouseup', stopDrawing);
    canvas.addEventListener('mouseout', stopDrawing);
    
    // Adicionar listeners para touch (mobile)
    canvas.addEventListener('touchstart', startDrawingTouch);
    canvas.addEventListener('touchmove', drawTouch);
    canvas.addEventListener('touchend', stopDrawing);
    
    log('Event listeners configurados');
    return true;
}

function initBrushes() {
    const brushes = [
        {type: 'normal', name: 'Normal', emoji: '🖌️', unlocked: true},
        {type: 'thick', name: 'Grosso', emoji: '🖍️', unlocked: true},
        {type: 'neon', name: 'Neon', emoji: '✨', unlocked: true},
        {type: 'spray', name: 'Spray', emoji: '💨', unlocked: true},
        {type: 'marker', name: 'Marcador', emoji: '🖊️', unlocked: true},
        {type: 'sparkle', name: 'Brilho', emoji: '⭐', unlocked: true},
        {type: 'eraser', name: 'Borracha', emoji: '🧹', unlocked: true},
        {type: 'dotted', name: 'Pontilhado', emoji: '⚫', unlocked: true}
    ];
    
    const container = document.getElementById('brushes');
    brushes.forEach(brush => {
        const btn = document.createElement('button');
        btn.className = `p-3 rounded-lg text-center transition-all brush-btn ${
            brush.unlocked 
                ? 'bg-purple-100 hover:bg-purple-200' 
                : 'bg-gray-100 cursor-not-allowed opacity-50'
        }`;
        btn.id = `brush-${brush.type}`;
        btn.setAttribute('data-brush', brush.type);
        btn.innerHTML = `<div class="text-2xl">${brush.emoji}</div><div class="text-xs">${brush.name}</div>`;
        btn.disabled = !brush.unlocked;
        btn.onclick = () => selectBrush(brush.type);
        container.appendChild(btn);
    });
    
    // Marcar o primeiro pincel como selecionado
    const firstBrush = document.getElementById('brush-normal');
    if (firstBrush) {
        firstBrush.classList.add('ring-2', 'ring-purple-600');
    }
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
        log('Erro ao carregar jogador:', error);
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
    log('Botao Comeca clicado - iniciando desenho');
    gameState.isDrawing = true;
    log('gameState.isDrawing = true');
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
    log('startDrawingMouse called', 'isDrawing:', gameState.isDrawing);
    if (!gameState.isDrawing) {
        log('IGNORADO: gameState.isDrawing = false');
        return;
    }
    isDrawingNow = true;
    gameState.hasDrawn = true;
    const rect = canvas.getBoundingClientRect();
    [lastX, lastY] = [e.clientX - rect.left, e.clientY - rect.top];
    log('Mouse drawing iniciado em (' + lastX + ', ' + lastY + ')');
}

function drawMouse(e) {
    if (!isDrawingNow || !gameState.isDrawing) {
        if (!isDrawingNow) log('drawMouse ignorado: isDrawingNow=false');
        if (!gameState.isDrawing) log('drawMouse ignorado: gameState.isDrawing=false');
        return;
    }
    if (!canvas) {
        log('ERRO: canvas eh null em drawMouse');
        return;
    }
    const rect = canvas.getBoundingClientRect();
    const x = e.clientX - rect.left;
    const y = e.clientY - rect.top;
    log('drawMouse: x=' + x + ' y=' + y);
    draw(x, y);
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
    if (!ctx) {
        log('ERRO: Context is null!');
        return;
    }
    if (!canvas) {
        log('ERRO: Canvas is null!');
        return;
    }
    
    log('draw() executando: x=' + x + ', y=' + y + ', lastX=' + lastX + ', lastY=' + lastY);
    
    // Resetar propriedades do canvas
    ctx.shadowBlur = 0;
    ctx.shadowColor = 'rgba(0,0,0,0)';
    ctx.globalCompositeOperation = 'source-over';
    ctx.globalAlpha = 1;
    
    let lineWidth = gameState.brushSize;
    let strokeColor = gameState.currentColor;
    
    log('Desenhando em', x, y, 'cor:', strokeColor, 'pincel:', gameState.currentBrush);
    
    // Configurar propriedades por tipo de pincel
    switch(gameState.currentBrush) {
        case 'neon':
            ctx.shadowBlur = 20;
            ctx.shadowColor = gameState.currentColor;
            lineWidth = gameState.brushSize * 0.8;
            break;
        case 'thick':
            lineWidth = gameState.brushSize * 1.8;
            break;
        case 'eraser':
            ctx.globalCompositeOperation = 'destination-out';
            strokeColor = 'rgba(0,0,0,1)';
            lineWidth = gameState.brushSize * 1.5;
            break;
        case 'marker':
            ctx.globalAlpha = 0.6;
            lineWidth = gameState.brushSize * 1.3;
            break;
        case 'dotted':
            // Desenhar pontinhos em vez de linha contínua
            const distance = Math.sqrt(Math.pow(x - lastX, 2) + Math.pow(y - lastY, 2));
            const steps = Math.ceil(distance / 8);
            for (let i = 0; i <= steps; i++) {
                const px = lastX + (x - lastX) * (i / steps);
                const py = lastY + (y - lastY) * (i / steps);
                ctx.fillStyle = gameState.currentColor;
                ctx.beginPath();
                ctx.arc(px, py, gameState.brushSize / 2, 0, Math.PI * 2);
                ctx.fill();
            }
            [lastX, lastY] = [x, y];
            return;
    }
    
    ctx.strokeStyle = strokeColor;
    ctx.lineWidth = lineWidth;
    ctx.lineCap = 'round';
    ctx.lineJoin = 'round';
    
    // Desenhar linha
    ctx.beginPath();
    ctx.moveTo(lastX, lastY);
    ctx.lineTo(x, y);
    ctx.stroke();
    
    // Resetar estados especiais
    ctx.globalAlpha = 1;
    ctx.globalCompositeOperation = 'source-over';
    ctx.shadowBlur = 0;
    
    // Aplicar efeitos adicionais APÓS o stroke
    if (gameState.currentBrush === 'spray') {
        sprayEffect(x, y);
    } else if (gameState.currentBrush === 'sparkle') {
        sparkleEffect(x, y);
    }
    
    [lastX, lastY] = [x, y];
    console.log('Draw completed, lastX:', lastX, 'lastY:', lastY);
}

function sprayEffect(x, y) {
    const originalFillStyle = ctx.fillStyle;
    ctx.fillStyle = gameState.currentColor;
    for (let i = 0; i < 15; i++) {
        const offsetX = (Math.random() - 0.5) * gameState.brushSize * 3;
        const offsetY = (Math.random() - 0.5) * gameState.brushSize * 3;
        const size = Math.random() * 2 + 1;
        ctx.fillRect(x + offsetX, y + offsetY, size, size);
    }
    ctx.fillStyle = originalFillStyle;
}

function sparkleEffect(x, y) {
    const originalFillStyle = ctx.fillStyle;
    ctx.fillStyle = gameState.currentColor;
    for (let i = 0; i < 8; i++) {
        const angle = (Math.PI * 2 * i) / 8;
        const sparkleX = x + Math.cos(angle) * (gameState.brushSize + 5);
        const sparkleY = y + Math.sin(angle) * (gameState.brushSize + 5);
        ctx.fillRect(sparkleX, sparkleY, 3, 3);
    }
    ctx.fillStyle = originalFillStyle;
}

function selectBrush(type) {
    gameState.currentBrush = type;
    ctx.shadowBlur = 0;
    ctx.shadowColor = 'rgba(0,0,0,0)';
    
    // Atualizar selecao visual dos pinceis
    const allBrushes = document.querySelectorAll('.brush-btn');
    allBrushes.forEach(btn => btn.classList.remove('ring-2', 'ring-purple-600'));
    
    const selectedBtn = document.getElementById(`brush-${type}`);
    if (selectedBtn) {
        selectedBtn.classList.add('ring-2', 'ring-purple-600');
    }
    
    log('Pincel alterado: ' + type);
}

function selectColor(color) {
    gameState.currentColor = color;
    log('Cor alterada: ' + color);
}

function clearCanvas() {
    // 🎯 CORREÇÃO: Limpar E preencher com branco novamente
    ctx.fillStyle = '#FFFFFF';
    ctx.fillRect(0, 0, canvas.width, canvas.height);
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
        log('Erro ao enviar desenho:', error);
        alert('Erro ao enviar! :(');
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