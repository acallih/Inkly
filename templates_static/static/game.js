/**
 * Inkly - Game Logic
 * Sistema de desenho, canvas e interação com IA
 * Arquivo principal que gerencia toda a lógica do jogo de desenho
 */

// Flag para ativar/desativar logs de debug no console
const DEBUG = true // ATIVAR DEBUG MODE

// Objeto central que armazena o estado atual do jogo
const gameState = {
  playerId: window.PLAYER_ID || new URLSearchParams(window.location.search).get("player_id"), // ID do jogador obtido da URL ou variável global
  sessionId: null, // ID da sessão atual de jogo
  prompt: null, // Texto do desafio atual que o jogador deve desenhar
  timeLimit: 20, // Limite de tempo inicial para completar o desenho
  timeLeft: 20, // Tempo restante no cronômetro
  timerInterval: null, // Referência ao intervalo do timer para poder cancelá-lo depois
  isDrawing: false, // Flag que indica se o jogador está autorizado a desenhar
  hasDrawn: false, // Flag que indica se o jogador já desenhou algo no canvas
  currentBrush: "normal", // Tipo de pincel atualmente selecionado
  currentColor: "#000000", // Cor atual do pincel (preto por padrão)
  brushSize: 8, // Tamanho do pincel em pixels
}

// Variáveis globais para o canvas e seu contexto de desenho
let canvas = null // Elemento HTML canvas onde o desenho acontece
let ctx = null // Contexto 2D do canvas usado para desenhar
let isDrawingNow = false // Flag que indica se o usuário está ativamente desenhando no momento
let lastX = 0 // Última posição X do mouse/touch (usado para desenhar linhas)
let lastY = 0 // Última posição Y do mouse/touch (usado para desenhar linhas)

// Array com as cores disponíveis na paleta de cores
const colors = [
  "#000000", // Preto
  "#FFFFFF", // Branco
  "#FF0000", // Vermelho
  "#00FF00", // Verde
  "#0000FF", // Azul
  "#FFFF00", // Amarelo
  "#FF00FF", // Magenta
  "#00FFFF", // Ciano
  "#FFA500", // Laranja
  "#800080", // Roxo
  "#FFC0CB", // Rosa
  "#8B4513", // Marrom
]

/**
 * Função auxiliar para fazer logs apenas quando DEBUG está ativado
 * @param {...any} args - Argumentos para logar no console
 */
function log(...args) {
  if (DEBUG) console.log("[INKLY]", ...args)
}

/**
 * Event listener que aguarda o DOM estar totalmente carregado
 * Inicializa todos os componentes do jogo quando a página estiver pronta
 */
document.addEventListener("DOMContentLoaded", () => {
  log("playerId: " + gameState.playerId) // Log do ID do jogador
  initCanvas() // Inicializa o canvas de desenho
  initBrushes() // Cria os botões de pincéis
  initColors() // Cria a paleta de cores
  initRGBSliders() // Configura os sliders RGB para seleção de cores customizadas
  loadPlayerData() // Carrega os dados do jogador (level, XP, etc)
  loadNewPrompt() // Carrega o primeiro desafio de desenho
})

/**
 * Inicializa o canvas de desenho e seus event listeners
 * Configura o contexto 2D e propriedades iniciais do canvas
 * @returns {boolean} true se inicialização foi bem sucedida, false caso contrário
 */
function initCanvas() {
  // Obter referencia ao canvas e contexto no momento da inicializacao
  canvas = document.getElementById("canvas")
  if (!canvas) {
    log("ERRO: Canvas element not found!")
    return false
  }

  // Obter o contexto 2D para desenhar
  ctx = canvas.getContext("2d")
  if (!ctx) {
    log("ERRO: Canvas 2D context not available!")
    return false
  }

  log("Canvas obtido e inicializado")

  // Garantir que o canvas tem o tamanho correto (800x600 pixels)
  if (canvas.width !== 800 || canvas.height !== 600) {
    canvas.width = 800
    canvas.height = 600
  }

  // Preencher com fundo branco (importante para que o desenho tenha um fundo limpo)
  ctx.fillStyle = "#FFFFFF"
  ctx.fillRect(0, 0, canvas.width, canvas.height)

  // Configurar propriedades padrão do contexto de desenho
  ctx.lineCap = "round" // Extremidades das linhas arredondadas
  ctx.lineJoin = "round" // Junções entre linhas arredondadas
  ctx.shadowBlur = 0 // Sem desfoque de sombra inicialmente
  ctx.shadowColor = "rgba(0,0,0,0)" // Sombra transparente inicialmente

  // Inicializar cor padrao
  gameState.currentColor = "#000000" // Preto
  gameState.currentBrush = "normal" // Pincel normal
  gameState.brushSize = 8 // Tamanho médio

  log("Canvas: " + canvas.width + "x" + canvas.height + " pronto para desenhar")

  // Teste de desenho - desenhar uma linha de teste para verificar se está funcionando
  log("Desenhando linha de teste no canvas")
  ctx.strokeStyle = "#FF0000" // Vermelho para o teste
  ctx.lineWidth = 2
  ctx.beginPath()
  ctx.moveTo(10, 10) // Início da linha
  ctx.lineTo(100, 100) // Fim da linha
  ctx.stroke() // Desenhar a linha
  log("Linha de teste desenhada (deve ver uma linha vermelha)")

  // Limpar o teste após 2 segundos
  setTimeout(() => {
    ctx.fillStyle = "#FFFFFF"
    ctx.fillRect(0, 0, canvas.width, canvas.height)
    log("Canvas limpado apos teste")
  }, 2000)

  // Adicionar listeners para mouse (desktop)
  canvas.addEventListener("mousedown", startDrawingMouse) // Quando pressiona o botão do mouse
  canvas.addEventListener("mousemove", drawMouse) // Quando move o mouse
  canvas.addEventListener("mouseup", stopDrawing) // Quando solta o botão do mouse
  canvas.addEventListener("mouseout", stopDrawing) // Quando o mouse sai do canvas

  // Adicionar listeners para touch (mobile/tablets)
  canvas.addEventListener("touchstart", startDrawingTouch) // Quando toca na tela
  canvas.addEventListener("touchmove", drawTouch) // Quando arrasta o dedo
  canvas.addEventListener("touchend", stopDrawing) // Quando solta o dedo

  log("Event listeners configurados")
  return true
}

/**
 * Inicializa os botões de pincéis disponíveis no jogo
 * Cria os elementos HTML para cada tipo de pincel
 */
function initBrushes() {
  // Array com todos os tipos de pincéis disponíveis
  const brushes = [
    { type: "normal", name: "Normal", emoji: "🖌️", unlocked: true }, // Pincel padrão
    { type: "thick", name: "Grosso", emoji: "🖍️", unlocked: true }, // Pincel mais grosso
    { type: "neon", name: "Neon", emoji: "✨", unlocked: true }, // Pincel com efeito neon/brilho
    { type: "spray", name: "Spray", emoji: "💨", unlocked: true }, // Efeito de spray/aerossol
    { type: "marker", name: "Marcador", emoji: "🖊️", unlocked: true }, // Marcador semi-transparente
    { type: "sparkle", name: "Brilho", emoji: "⭐", unlocked: true }, // Pincel com partículas de brilho
    { type: "eraser", name: "Borracha", emoji: "🧹", unlocked: true }, // Borracha para apagar
    { type: "dotted", name: "Pontilhado", emoji: "⚫", unlocked: true }, // Linha pontilhada
  ]

  // Obter o container onde os botões serão inseridos
  const container = document.getElementById("brushes")

  // Criar um botão para cada pincel
  brushes.forEach((brush) => {
    const btn = document.createElement("button")
    // Aplicar classes CSS baseado no estado de desbloqueio
    btn.className = `p-3 rounded-lg text-center transition-all brush-btn ${
      brush.unlocked
        ? "bg-purple-100 hover:bg-purple-200" // Estilo para pincéis desbloqueados
        : "bg-gray-100 cursor-not-allowed opacity-50" // Estilo para pincéis bloqueados
    }`
    btn.id = `brush-${brush.type}` // ID único para cada botão
    btn.setAttribute("data-brush", brush.type) // Atributo data para identificar o tipo
    btn.innerHTML = `<div class="text-2xl">${brush.emoji}</div><div class="text-xs">${brush.name}</div>` // Emoji e nome
    btn.disabled = !brush.unlocked // Desabilitar se ainda não foi desbloqueado
    btn.onclick = () => selectBrush(brush.type) // Função a ser chamada ao clicar
    container.appendChild(btn) // Adicionar o botão ao container
  })

  // Marcar o primeiro pincel (normal) como selecionado por padrão
  const firstBrush = document.getElementById("brush-normal")
  if (firstBrush) {
    firstBrush.classList.add("ring-2", "ring-purple-600") // Adicionar borda roxa de seleção
  }
}

/**
 * Inicializa a paleta de cores com botões clicáveis
 * Cria um botão para cada cor disponível
 */
function initColors() {
  const container = document.getElementById("colorPalette")
  // Limpa container para evitar duplicação se a função for chamada novamente
  container.innerHTML = ""

  // Criar um botão para cada cor do array
  colors.forEach((color) => {
    const btn = document.createElement("button")
    btn.className =
      "w-8 h-8 rounded-lg border-2 border-gray-300 hover:scale-110 transition-transform focus:outline-none"
    btn.style.backgroundColor = color // Definir a cor de fundo do botão
    btn.onclick = () => {
      selectColor(color) // Selecionar a cor ao clicar
      // Remove destaque de todos os botões
      Array.from(container.children).forEach((b) => b.classList.remove("ring-2", "ring-offset-2", "ring-gray-600"))
      // Adiciona destaque visual apenas neste botão
      btn.classList.add("ring-2", "ring-offset-2", "ring-gray-600")
    }
    container.appendChild(btn) // Adicionar botão ao container
  })
}

/**
 * Função auxiliar para converter cor Hexadecimal (#RRGGBB) para valores RGB numéricos
 * @param {string} hex - Cor em formato hexadecimal (ex: "#FF0000" ou "F00")
 * @returns {Object} Objeto com propriedades r, g, b (números de 0-255)
 */
function hexToRgb(hex) {
  // Remove o # se existir no início
  hex = hex.replace(/^#/, "")
  // Suporte para hex curto (#F00 -> #FF0000)
  if (hex.length === 3) {
    hex = hex[0] + hex[0] + hex[1] + hex[1] + hex[2] + hex[2]
  }
  // Converter hexadecimal para número inteiro
  const bigint = Number.parseInt(hex, 16)
  // Extrair componentes R, G, B usando operações bit a bit
  const r = (bigint >> 16) & 255 // Desloca 16 bits e pega os últimos 8 bits (Red)
  const g = (bigint >> 8) & 255 // Desloca 8 bits e pega os últimos 8 bits (Green)
  const b = bigint & 255 // Pega os últimos 8 bits (Blue)
  return { r, g, b }
}

/**
 * Seleciona uma cor para desenhar
 * Atualiza a cor atual e sincroniza com os sliders RGB e preview
 * @param {string} color - Cor em formato hex (#RRGGBB) ou rgb(r,g,b)
 */
function selectColor(color) {
  gameState.currentColor = color // Atualizar a cor no estado do jogo
  log("Cor alterada: " + color)

  // 1. Atualizar o quadrado de pré-visualização grande
  const rgbPreview = document.getElementById("rgbPreview")
  if (rgbPreview) {
    rgbPreview.style.backgroundColor = color // Mostrar a cor selecionada visualmente
  }

  // 2. Se a cor veio dos botões (começa com #), precisamos atualizar os sliders
  if (color.startsWith("#")) {
    const rgb = hexToRgb(color) // Converter hex para RGB
    // Atualiza a posição das bolinhas dos sliders
    document.getElementById("colorR").value = rgb.r
    document.getElementById("colorG").value = rgb.g
    document.getElementById("colorB").value = rgb.b
    // Atualiza os números de texto ao lado dos sliders
    document.getElementById("rVal").textContent = rgb.r
    document.getElementById("gVal").textContent = rgb.g
    document.getElementById("bVal").textContent = rgb.b
  }

  // 3. (Opcional) Destaque visual no botão selecionado
  const allColorBtns = document.querySelectorAll("#colorPalette button")
  allColorBtns.forEach((btn) => {
    // Remove borda de seleção anterior
    btn.classList.remove("ring-2", "ring-offset-2", "ring-gray-400")
    // O destaque correto será feito no initColors/onClick
  })
}

/**
 * Inicializa os sliders RGB (Red, Green, Blue)
 * Permite seleção de cores customizadas ajustando cada componente de cor
 */
function initRGBSliders() {
  // Obter referências aos três sliders
  const rSlider = document.getElementById("colorR") // Slider do componente vermelho
  const gSlider = document.getElementById("colorG") // Slider do componente verde
  const bSlider = document.getElementById("colorB") // Slider do componente azul

  /**
   * Função interna que atualiza a cor baseada nos valores dos sliders
   */
  const updateRGB = () => {
    // Ler os valores atuais de cada slider (0-255)
    const r = Number.parseInt(rSlider.value)
    const g = Number.parseInt(gSlider.value)
    const b = Number.parseInt(bSlider.value)

    // Atualizar os textos que mostram os valores numéricos
    document.getElementById("rVal").textContent = r
    document.getElementById("gVal").textContent = g
    document.getElementById("bVal").textContent = b

    // Criar string de cor no formato rgb(r, g, b)
    const color = `rgb(${r}, ${g}, ${b})`
    // Atualizar o preview visual
    document.getElementById("rgbPreview").style.backgroundColor = color
    // Selecionar esta cor para desenhar
    selectColor(color)
  }

  // Adicionar listener para cada slider que atualiza quando o valor muda
  rSlider.addEventListener("input", updateRGB)
  gSlider.addEventListener("input", updateRGB)
  bSlider.addEventListener("input", updateRGB)
}

/**
 * Carrega os dados do jogador do servidor
 * Atualiza a UI com nível, XP, streak e pincéis desbloqueados
 */
async function loadPlayerData() {
  try {
    // Fazer requisição GET para obter dados do jogador
    const response = await fetch(`/api/player/${gameState.playerId}`)
    const player = await response.json()

    // Atualizar informações na UI
    document.getElementById("level").textContent = `Nv. ${player.level}` // Nível do jogador
    document.getElementById("xp").textContent = `${player.xp} XP` // Pontos de experiência
    document.getElementById("streak").textContent = `${player.streak}🔥` // Sequência de acertos

    // Desbloquear pincéis que o jogador conquistou
    player.brushes_unlocked.forEach((brush) => {
      const buttons = document.querySelectorAll("#brushes button")
      buttons.forEach((btn) => {
        if (btn.textContent.includes(brush)) {
          btn.disabled = false // Habilitar o botão
          btn.classList.remove("opacity-50", "cursor-not-allowed") // Remover estilo de bloqueado
          btn.classList.add("bg-purple-100", "hover:bg-purple-200") // Adicionar estilo de desbloqueado
        }
      })
    })
  } catch (error) {
    log("Erro ao carregar jogador:", error)
  }
}

/**
 * Carrega um novo desafio de desenho do servidor
 * Inicia uma nova sessão de jogo com um prompt aleatório
 */
async function loadNewPrompt() {
  try {
    log("Carregando novo desafio para player:", gameState.playerId)
    // Fazer requisição POST para iniciar uma nova sessão
    const response = await fetch("/api/session/start", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        player_id: gameState.playerId,
        difficulty: "medium", // Dificuldade média
        surprise_mode: true, // Modo surpresa ativado
      }),
    })

    // Verificar se a requisição foi bem sucedida
    if (!response.ok) {
      throw new Error(`HTTP ${response.status}: ${response.statusText}`)
    }

    // Parsear a resposta JSON
    const data = await response.json()
    log("Desafio carregado:", data.prompt.text)

    // Atualizar o estado do jogo com os dados da nova sessão
    gameState.sessionId = data.session_id // ID da sessão para enviar resultado depois
    gameState.prompt = data.prompt.text // Texto do desafio (ex: "Desenhe um gato")
    gameState.timeLimit = data.prompt.time_limit // Tempo limite para este desafio
    gameState.timeLeft = data.prompt.time_limit // Inicializar tempo restante

    // Atualizar a UI
    document.getElementById("prompt").textContent = `Desenhe: ${gameState.prompt}` // Mostrar o desafio
    document.getElementById("timer").textContent = gameState.timeLeft // Mostrar o tempo
    document.getElementById("startBtn").disabled = false // Habilitar botão de começar
    updateAIMascot("🤖", "Pronto para começar?") // Atualizar mascote da IA
  } catch (error) {
    log("Erro ao carregar prompt:", error)
    alert("Erro ao carregar desafio! 😢\nDetalhes: " + error.message)
  }
}

/**
 * Inicia o modo de desenho e o cronômetro
 * Chamado quando o jogador clica no botão "Começar"
 */
function startDrawing() {
  log("Botao Comeca clicado - iniciando desenho")
  gameState.isDrawing = true // Permitir que o jogador desenhe
  log("gameState.isDrawing = true")

  // Atualizar UI
  document.getElementById("startBtn").disabled = true // Desabilitar botão de começar
  document.getElementById("submitBtn").disabled = false // Habilitar botão de enviar
  document.getElementById("promptCard").classList.add("opacity-50") // Diminuir opacidade do card do prompt
  updateAIMascot("👀", "Estou observando...") // Atualizar mascote

  // Iniciar o cronômetro que decrementa a cada segundo
  gameState.timerInterval = setInterval(() => {
    gameState.timeLeft-- // Diminuir tempo restante
    document.getElementById("timer").textContent = gameState.timeLeft // Atualizar display

    // Se estiver nos últimos 5 segundos, adicionar animação de alerta
    if (gameState.timeLeft <= 5) {
      document.getElementById("timer").classList.add("text-red-500", "animate-pulse")
    }

    // Se o tempo acabou
    if (gameState.timeLeft <= 0) {
      clearInterval(gameState.timerInterval) // Parar o cronômetro
      if (gameState.hasDrawn) {
        submitDrawing() // Se desenhou algo, enviar automaticamente
      } else {
        updateAIMascot("😅", "O tempo acabou!") // Se não desenhou, mostrar mensagem
        setTimeout(nextRound, 2000) // Ir para próxima rodada após 2 segundos
      }
    }
  }, 1000) // Executar a cada 1000ms (1 segundo)
}

/**
 * Inicia o desenho com mouse (desktop)
 * Chamado quando o botão do mouse é pressionado no canvas
 * @param {MouseEvent} e - Evento do mouse
 */
function startDrawingMouse(e) {
  log("startDrawingMouse called", "isDrawing:", gameState.isDrawing)
  // Verificar se o jogador tem permissão para desenhar
  if (!gameState.isDrawing) {
    log("IGNORADO: gameState.isDrawing = false")
    return // Se não começou o jogo ainda, ignorar
  }
  e.preventDefault() // Prevenir comportamento padrão do navegador
  isDrawingNow = true // Marcar que está desenhando agora
  gameState.hasDrawn = true // Marcar que o jogador já desenhou algo

  // Calcular posição do mouse relativa ao canvas
  const rect = canvas.getBoundingClientRect() // Posição do canvas na tela
  const scaleX = canvas.width / rect.width // Escala X (caso o canvas esteja redimensionado via CSS)
  const scaleY = canvas.height / rect.height // Escala Y
  lastX = (e.clientX - rect.left) * scaleX // Posição X ajustada
  lastY = (e.clientY - rect.top) * scaleY // Posição Y ajustada
  log("Mouse drawing iniciado em (" + lastX + ", " + lastY + ")")
}

/**
 * Desenha com mouse enquanto ele está sendo movido
 * Chamado continuamente enquanto o mouse se move sobre o canvas
 * @param {MouseEvent} e - Evento do mouse
 */
function drawMouse(e) {
  // Verificar se está desenhando E se tem permissão
  if (!isDrawingNow || !gameState.isDrawing) {
    if (!isDrawingNow) log("drawMouse ignorado: isDrawingNow=false")
    if (!gameState.isDrawing) log("drawMouse ignorado: gameState.isDrawing=false")
    return
  }
  // Verificar se o canvas existe
  if (!canvas) {
    log("ERRO: canvas eh null em drawMouse")
    return
  }
  e.preventDefault() // Prevenir comportamento padrão

  // Calcular nova posição do mouse
  const rect = canvas.getBoundingClientRect()
  const scaleX = canvas.width / rect.width
  const scaleY = canvas.height / rect.height
  const x = (e.clientX - rect.left) * scaleX
  const y = (e.clientY - rect.top) * scaleY
  log("drawMouse: x=" + x + " y=" + y)

  // Chamar função de desenho principal
  draw(x, y)
}

/**
 * Inicia o desenho com touch (mobile/tablet)
 * Chamado quando o usuário toca na tela
 * @param {TouchEvent} e - Evento de touch
 */
function startDrawingTouch(e) {
  if (!gameState.isDrawing) return // Verificar permissão
  e.preventDefault() // Prevenir scroll da página
  isDrawingNow = true // Marcar que está desenhando
  gameState.hasDrawn = true // Marcar que desenhou algo

  const touch = e.touches[0] // Primeiro ponto de toque
  const rect = canvas.getBoundingClientRect()
  // Salvar posição inicial do toque
  ;[lastX, lastY] = [touch.clientX - rect.left, touch.clientY - rect.top]
}

/**
 * Desenha com touch enquanto o dedo está sendo arrastado
 * Chamado continuamente enquanto o dedo se move sobre o canvas
 * @param {TouchEvent} e - Evento de touch
 */
function drawTouch(e) {
  if (!isDrawingNow || !gameState.isDrawing) return // Verificar estado
  e.preventDefault() // Prevenir scroll

  const touch = e.touches[0] // Primeiro ponto de toque
  const rect = canvas.getBoundingClientRect()
  // Chamar função de desenho com posição do toque
  draw(touch.clientX - rect.left, touch.clientY - rect.top)
}

/**
 * Para o desenho (mouse ou touch)
 * Chamado quando o botão é solto ou o toque termina
 */
function stopDrawing() {
  isDrawingNow = false // Marcar que parou de desenhar
}

/**
 * Função principal de desenho no canvas
 * Desenha uma linha da última posição até a posição atual
 * @param {number} x - Coordenada X atual
 * @param {number} y - Coordenada Y atual
 */
function draw(x, y) {
  // Verificar se o contexto existe
  if (!ctx) {
    log("ERRO: Context is null!")
    return
  }
  // Verificar se o canvas existe
  if (!canvas) {
    log("ERRO: Canvas is null!")
    return
  }

  log("draw() executando: x=" + x + ", y=" + y + ", lastX=" + lastX + ", lastY=" + lastY)

  // Resetar propriedades do canvas para valores padrão
  ctx.shadowBlur = 0 // Sem desfoque
  ctx.shadowColor = "rgba(0,0,0,0)" // Sem sombra
  ctx.globalCompositeOperation = "source-over" // Modo de composição normal
  ctx.globalAlpha = 1 // Opacidade total

  // Variáveis para armazenar configurações do pincel
  let lineWidth = gameState.brushSize // Tamanho da linha
  let strokeColor = gameState.currentColor // Cor da linha

  log("Desenhando em", x, y, "cor:", strokeColor, "pincel:", gameState.currentBrush)

  // Configurar propriedades específicas por tipo de pincel
  switch (gameState.currentBrush) {
    case "neon":
      // Pincel neon: adiciona brilho ao redor da linha
      ctx.shadowBlur = 20 // Desfoque forte
      ctx.shadowColor = gameState.currentColor // Sombra da mesma cor
      lineWidth = gameState.brushSize * 0.8 // Linha um pouco mais fina
      break
    case "thick":
      // Pincel grosso: linha mais grossa
      lineWidth = gameState.brushSize * 1.8
      break
    case "eraser":
      // Borracha: remove o que foi desenhado
      ctx.globalCompositeOperation = "destination-out" // Modo de apagar
      strokeColor = "rgba(0,0,0,1)" // Cor não importa no modo destination-out
      lineWidth = gameState.brushSize * 1.5 // Borracha um pouco maior
      break
    case "marker":
      // Marcador: semi-transparente
      ctx.globalAlpha = 0.6 // 60% de opacidade
      lineWidth = gameState.brushSize * 1.3 // Um pouco mais grosso
      break
    case "dotted":
      // Pontilhado: desenhar pontinhos em vez de linha contínua
      const distance = Math.sqrt(Math.pow(x - lastX, 2) + Math.pow(y - lastY, 2)) // Calcular distância
      const steps = Math.ceil(distance / 8) // Quantos pontos desenhar (a cada 8 pixels)
      // Loop para desenhar cada ponto
      for (let i = 0; i <= steps; i++) {
        // Interpolar posição entre último ponto e ponto atual
        const px = lastX + (x - lastX) * (i / steps)
        const py = lastY + (y - lastY) * (i / steps)
        ctx.fillStyle = gameState.currentColor
        ctx.beginPath()
        ctx.arc(px, py, gameState.brushSize / 2, 0, Math.PI * 2) // Desenhar círculo
        ctx.fill() // Preencher o círculo
      }
      ;[lastX, lastY] = [x, y] // Atualizar última posição
      return // Sair da função (não desenhar linha normal)
  }

  // Configurar cor e tamanho para desenhar
  ctx.strokeStyle = strokeColor // Definir cor da linha
  ctx.lineWidth = lineWidth // Definir espessura da linha
  ctx.lineCap = "round" // Extremidades arredondadas
  ctx.lineJoin = "round" // Junções arredondadas

  log("👀 Prestes a desenhar linha: beginPath()")
  // Desenhar linha da última posição até a posição atual
  ctx.beginPath() // Iniciar novo caminho
  log("👀 ctx.moveTo(" + lastX + ", " + lastY + ")")
  ctx.moveTo(lastX, lastY) // Mover para última posição (sem desenhar)
  log("👀 ctx.lineTo(" + x + ", " + y + ")")
  ctx.lineTo(x, y) // Desenhar linha até posição atual
  log("👀 ctx.stroke() - DESENHANDO AGORA")
  ctx.stroke() // Aplicar o traçado (realmente desenha)
  log("✅ Linha desenhada com sucesso!")

  // Resetar estados especiais após desenhar
  ctx.globalAlpha = 1 // Voltar para opacidade total
  ctx.globalCompositeOperation = "source-over" // Voltar para modo normal
  ctx.shadowBlur = 0 // Remover desfoque

  // Aplicar efeitos adicionais especiais APÓS o stroke principal
  if (gameState.currentBrush === "spray") {
    sprayEffect(x, y) // Adicionar efeito de spray
  } else if (gameState.currentBrush === "sparkle") {
    sparkleEffect(x, y) // Adicionar efeito de brilho
  }
  // Atualizar última posição para a próxima iteração
  ;[lastX, lastY] = [x, y]
  log("Draw completed, lastX:", lastX, "lastY:", lastY)
}

/**
 * Aplica efeito de spray (partículas aleatórias ao redor do ponto)
 * @param {number} x - Coordenada X central
 * @param {number} y - Coordenada Y central
 */
function sprayEffect(x, y) {
  const originalFillStyle = ctx.fillStyle // Salvar cor de preenchimento original
  ctx.fillStyle = gameState.currentColor // Usar cor atual

  // Desenhar 15 partículas aleatórias ao redor do ponto
  for (let i = 0; i < 15; i++) {
    // Offset aleatório ao redor do ponto central
    const offsetX = (Math.random() - 0.5) * gameState.brushSize * 3 // -1.5x a +1.5x o tamanho do pincel
    const offsetY = (Math.random() - 0.5) * gameState.brushSize * 3
    const size = Math.random() * 2 + 1 // Tamanho aleatório entre 1 e 3 pixels
    ctx.fillRect(x + offsetX, y + offsetY, size, size) // Desenhar pequeno retângulo
  }

  ctx.fillStyle = originalFillStyle // Restaurar cor original
}

/**
 * Aplica efeito de brilho (estrela de 8 pontas ao redor do ponto)
 * @param {number} x - Coordenada X central
 * @param {number} y - Coordenada Y central
 */
function sparkleEffect(x, y) {
  const originalFillStyle = ctx.fillStyle // Salvar cor original
  ctx.fillStyle = gameState.currentColor // Usar cor atual

  // Desenhar 8 pontos formando uma estrela ao redor do centro
  for (let i = 0; i < 8; i++) {
    const angle = (Math.PI * 2 * i) / 8 // Ângulo para cada ponto (360° / 8 = 45°)
    // Calcular posição de cada ponto da estrela
    const sparkleX = x + Math.cos(angle) * (gameState.brushSize + 5)
    const sparkleY = y + Math.sin(angle) * (gameState.brushSize + 5)
    ctx.fillRect(sparkleX, sparkleY, 3, 3) // Desenhar pequeno quadrado
  }

  ctx.fillStyle = originalFillStyle // Restaurar cor original
}

/**
 * Seleciona um tipo de pincel
 * Atualiza o estado e a interface visual
 * @param {string} type - Tipo do pincel (ex: 'normal', 'neon', 'eraser')
 */
function selectBrush(type) {
  gameState.currentBrush = type // Atualizar pincel no estado
  // Resetar efeitos especiais do contexto
  ctx.shadowBlur = 0
  ctx.shadowColor = "rgba(0,0,0,0)"

  // Atualizar seleção visual dos pincéis
  const allBrushes = document.querySelectorAll(".brush-btn")
  allBrushes.forEach((btn) => btn.classList.remove("ring-2", "ring-purple-600")) // Remover destaque de todos

  // Adicionar destaque ao pincel selecionado
  const selectedBtn = document.getElementById(`brush-${type}`)
  if (selectedBtn) {
    selectedBtn.classList.add("ring-2", "ring-purple-600") // Adicionar borda roxa
  }

  log("Pincel alterado: " + type)
}

/**
 * Limpa todo o conteúdo do canvas
 * Preenche com branco e reseta flag de desenho
 */
function clearCanvas() {
  // 🎯 CORREÇÃO: Limpar E preencher com branco novamente
  ctx.fillStyle = "#FFFFFF" // Definir cor branca
  ctx.fillRect(0, 0, canvas.width, canvas.height) // Preencher todo o canvas
  gameState.hasDrawn = false // Marcar que não desenhou nada ainda
}

/**
 * Envia o desenho para o servidor para análise da IA
 * Converte o canvas em imagem e envia junto com metadados da sessão
 */
async function submitDrawing() {
  // Verificar se o jogador desenhou algo
  if (!gameState.hasDrawn) {
    alert("Desenhe algo primeiro! 🎨")
    return
  }

  // Parar o cronômetro
  clearInterval(gameState.timerInterval)
  document.getElementById("submitBtn").disabled = true // Desabilitar botão de enviar
  updateAIMascot("🤔", "Analisando seu desenho...") // Atualizar mascote

  // Converter canvas para data URL (imagem em Base64)
  const imageData = canvas.toDataURL("image/png")
  // Calcular quanto tempo o jogador levou
  const timeSpent = gameState.timeLimit - gameState.timeLeft

  try {
    // Enviar desenho para o servidor
    const response = await fetch("/api/session/complete", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        session_id: gameState.sessionId, // ID da sessão atual
        drawing_data: imageData, // Imagem do desenho em Base64
        time_spent: timeSpent, // Tempo gasto em segundos
      }),
    })

    // Parsear resposta JSON
    const result = await response.json()
    // Mostrar resultados ao jogador
    showResults(result)
  } catch (error) {
    log("Erro ao enviar desenho:", error)
    alert("Erro ao enviar! :(")
  }
}

/**
 * Mostra os resultados da análise da IA em um modal
 * Exibe se acertou, palpites da IA, pontos ganhos, etc.
 * @param {Object} result - Objeto com resultados da análise
 */
function showResults(result) {
  const modal = document.getElementById("resultModal") // Obter modal

  // Configurar modal baseado se acertou ou errou
  if (result.correct) {
    // ACERTOU!
    createConfetti() // Criar confetes animados
    document.getElementById("resultEmoji").textContent = "🎉" // Emoji de comemoração
    document.getElementById("resultTitle").textContent = "Incrível!" // Título positivo
    updateAIMascot("😍", result.feedback) // Mascote feliz
  } else {
    // ERROU
    document.getElementById("resultEmoji").textContent = "🤔" // Emoji pensativo
    document.getElementById("resultTitle").textContent = "Quase lá!" // Título encorajador
    updateAIMascot("😅", result.feedback) // Mascote com feedback
  }

  // Mostrar feedback textual da IA
  document.getElementById("resultMessage").textContent = result.feedback

  // Mostrar os palpites da IA (top 3 ou top 5)
  const guessesDiv = document.getElementById("aiGuesses")
  guessesDiv.innerHTML = result.guesses
    .map(
      (guess, i) => `
        <div class="bg-white rounded-lg p-3 border-2 ${i === 0 ? "border-purple-400" : "border-gray-200"}">
            <span class="font-bold">${i + 1}º)</span> ${guess}
            ${i === 0 ? `<span class="text-purple-600">(${result.confidence}% confiança)</span>` : ""}
        </div>
    `,
    )
    .join("") // Mapeando cada palpite para HTML

  // Mostrar pontuação e XP ganho
  document.getElementById("scoreVal").textContent = `+${result.score}`
  document.getElementById("xpVal").textContent = `+${result.xp_gained} XP`

  // Se desbloqueou alguma conquista, mostrar
  if (result.achievements && result.achievements.length > 0) {
    document.getElementById("achievementsDisplay").classList.remove("hidden") // Mostrar seção de conquistas
    document.getElementById("achievementsList").innerHTML = result.achievements
      .map(
        (ach) => `
            <div class="bg-yellow-100 rounded-lg p-3 mb-2">
                <div class="font-bold">🏆 ${ach.name}</div>
                <div class="text-sm text-gray-600">${ach.description}</div>
            </div>
        `,
      )
      .join("") // Mapear cada conquista para HTML
    createConfetti() // Mais confetes para conquistas!
  }

  // Se subiu de nível, mostrar alert especial
  if (result.level_up) {
    setTimeout(() => {
      alert(`🎊 LEVEL UP! Você alcançou o nível ${result.new_level}! 🎊`)
    }, 500) // Delay de 500ms para não aparecer imediatamente
  }

  // Atualizar estatísticas do jogador na interface
  document.getElementById("level").textContent = `Nv. ${result.player_stats.level}`
  document.getElementById("xp").textContent = `${result.player_stats.xp} XP`
  document.getElementById("streak").textContent = `${result.player_stats.streak}🔥`

  // Mostrar o modal
  modal.classList.remove("hidden") // Remover classe que esconde
  modal.classList.add("flex") // Adicionar classe flex para centralizar
}

/**
 * Avança para a próxima rodada
 * Fecha modais, limpa canvas e carrega novo desafio
 */
function nextRound() {
  // Fechar modais
  document.getElementById("resultModal").classList.add("hidden")
  document.getElementById("achievementsDisplay").classList.add("hidden")

  // Limpar canvas
  clearCanvas()

  // Resetar estado do jogo
  gameState.isDrawing = false // Não pode desenhar até começar
  gameState.hasDrawn = false // Não desenhou nada ainda

  // Resetar UI
  document.getElementById("promptCard").classList.remove("opacity-50") // Restaurar opacidade do card
  document.getElementById("timer").classList.remove("text-red-500", "animate-pulse") // Remover animação de urgência

  // Carregar novo desafio
  loadNewPrompt()
}

/**
 * Pula o desafio atual
 * Pede confirmação e vai para próxima rodada sem ganhar pontos
 */
function skipPrompt() {
  // Pedir confirmação
  if (confirm("Tem certeza que quer pular?")) {
    clearInterval(gameState.timerInterval) // Parar cronômetro
    nextRound() // Ir para próxima rodada
  }
}

/**
 * Atualiza o mascote da IA com emoji e mensagem
 * @param {string} emoji - Emoji para mostrar
 * @param {string} message - Mensagem de texto
 */
function updateAIMascot(emoji, message) {
  document.getElementById("aiEmoji").textContent = emoji // Atualizar emoji
  document.getElementById("aiMessage").textContent = message // Atualizar mensagem
}

/**
 * Cria animação de confetes caindo na tela
 * Usado quando o jogador acerta ou ganha conquistas
 */
function createConfetti() {
  // Array de cores para os confetes
  const colors = ["#FF0000", "#00FF00", "#0000FF", "#FFFF00", "#FF00FF", "#00FFFF"]

  // Criar 50 confetes com delay progressivo
  for (let i = 0; i < 50; i++) {
    setTimeout(() => {
      // Criar elemento div para cada confete
      const confetti = document.createElement("div")
      confetti.className = "confetti" // Classe CSS para animação
      confetti.style.left = Math.random() * window.innerWidth + "px" // Posição X aleatória
      confetti.style.backgroundColor = colors[Math.floor(Math.random() * colors.length)] // Cor aleatória
      document.body.appendChild(confetti) // Adicionar ao body

      // Remover confete após 3 segundos (quando a animação terminar)
      setTimeout(() => confetti.remove(), 3000)
    }, i * 30) // Delay de 30ms entre cada confete (efeito cascata)
  }
}

/**
 * Event listener para o slider de tamanho do pincel
 * Atualiza o tamanho do pincel quando o slider é movido
 */
document.getElementById("brushSize").addEventListener("input", (e) => {
  gameState.brushSize = e.target.value // Atualizar tamanho no estado
  document.getElementById("sizeVal").textContent = `${e.target.value}px` // Atualizar texto que mostra o tamanho
})
