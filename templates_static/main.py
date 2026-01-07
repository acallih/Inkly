# Importações do FastAPI para criação de aplicação web
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from typing import Optional
import os

# Importações dos serviços customizados do projeto
from gemini_service import GeminiService
from game_manager import GameManager
from models import Difficulty

# Inicialização da aplicação FastAPI
# FastAPI é o framework web usado para criar a API REST
app = FastAPI(title="Inkly")

# Configuração do motor de templates Jinja2
# Templates são os arquivos HTML que serão renderizados
templates = Jinja2Templates(directory="templates")

# Montagem da pasta de arquivos estáticos (CSS, JS, imagens)
# Todos os arquivos em /static estarão acessíveis via URL /static/...
app.mount("/static", StaticFiles(directory="static"), name="static")

# Inicialização dos serviços principais da aplicação
game_manager = GameManager()  # Gerencia jogadores, sessões e pontuação
gemini_service = GeminiService()  # Serviço de IA para analisar desenhos

# ===== ROTAS DE PÁGINAS HTML =====

@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    """
    Rota principal da aplicação - Página inicial
    Renderiza o arquivo index.html com a tela de boas-vindas
    """
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/game", response_class=HTMLResponse)
async def game_page(request: Request, player_id: str):
    """
    Rota da página do jogo
    Recebe o ID do jogador como parâmetro de query string
    Busca os dados do jogador e renderiza a página do jogo
    Se o jogador não existir, cria um automaticamente (útil para testes)
    """
    # Busca o jogador pelo ID
    player = game_manager.get_player(player_id)
    
    if not player:
        # Criar jogador automaticamente se não existir (para testes)
        player = game_manager.create_player(f"Player_{player_id}")
    
    # Renderiza a página do jogo passando os dados do jogador
    return templates.TemplateResponse("game.html", {"request": request, "player": player})

@app.get("/test/minimal", response_class=HTMLResponse)
async def test_minimal(request: Request):
    """
    Rota de teste minimalista
    Renderiza uma versão simplificada do jogo para testes e debug
    """
    return templates.TemplateResponse("test_minimal.html", {"request": request})

@app.get("/leaderboard", response_class=HTMLResponse)
async def leaderboard_page(request: Request):
    """
    Rota da página de ranking
    Busca os top 20 jogadores e renderiza a tabela de classificação
    """
    # Obtém os 20 melhores jogadores do ranking
    leaderboard = game_manager.get_leaderboard(limit=20)
    
    # Renderiza a página passando os dados do ranking
    return templates.TemplateResponse("leaderboard.html", {"request": request, "leaderboard": leaderboard})

# ===== ROTAS DA API REST =====

@app.post("/api/player/create")
async def create_player(request: Request):
    """
    API para criar um novo jogador
    Recebe: { "name": "Nome do Jogador" }
    Retorna: Dados do jogador criado (id, nome, level, xp)
    """
    # Extrai os dados JSON do corpo da requisição
    data = await request.json()
    name = data.get("name")
    
    # Validação: nome é obrigatório
    if not name:
        raise HTTPException(status_code=400, detail="Nome obrigatorio")
    
    # Cria o novo jogador no sistema
    player = game_manager.create_player(name)
    
    # Retorna os dados básicos do jogador criado
    return {"player_id": player.id, "name": player.name, "level": player.level, "xp": player.xp}

@app.get("/api/player/{player_id}")
async def get_player(player_id: str):
    """
    API para buscar dados de um jogador específico
    Recebe: player_id na URL
    Retorna: Dados completos do jogador (stats, conquistas, pincéis desbloqueados)
    """
    # Busca o jogador pelo ID
    player = game_manager.get_player(player_id)
    
    # Se não encontrar, retorna erro 404
    if not player:
        raise HTTPException(status_code=404, detail="Jogador nao encontrado")
    
    # Retorna todos os dados do jogador
    return {
        "id": player.id,
        "name": player.name,
        "level": player.level,
        "xp": player.xp,
        "streak": player.streak,  # Sequência de acertos
        "total_drawings": player.total_drawings,  # Total de desenhos feitos
        "correct_guesses": player.correct_guesses,  # Total de acertos da IA
        "brushes_unlocked": [b.value for b in player.brushes_unlocked],  # Pincéis desbloqueados
        "achievements": player.achievements  # Lista de conquistas
    }

@app.post("/api/session/start")
async def start_session(request: Request):
    """
    API para iniciar uma nova sessão de jogo
    Recebe: { "player_id": "id", "difficulty": "easy|medium|hard", "surprise_mode": true|false }
    Retorna: ID da sessão e o prompt/desafio para o jogador desenhar
    """
    # Extrai os dados da requisição
    data = await request.json()
    player_id = data.get("player_id")
    difficulty_str = data.get("difficulty", "medium")  # Padrão: medium
    surprise_mode = data.get("surprise_mode", True)  # Padrão: modo surpresa ativo
    
    try:
        # Mapeia a string de dificuldade para o enum Difficulty
        dif_map = {"easy": Difficulty.EASY, "medium": Difficulty.MEDIUM, "hard": Difficulty.HARD}
        dif = dif_map.get(difficulty_str, Difficulty.MEDIUM)
        
        # Inicia uma nova sessão de jogo
        session = game_manager.start_session(player_id, difficulty=dif, surprise_mode=surprise_mode)
        
        # Retorna o ID da sessão e o prompt para o jogador
        return {
            "session_id": session.session_id,
            "prompt": {
                "text": session.prompt.text,  # O que o jogador deve desenhar
                "difficulty": session.prompt.difficulty.value,  # Nível de dificuldade
                "time_limit": session.prompt.time_limit  # Tempo limite em segundos
            }
        }
    except ValueError as e:
        # Se o jogador não for encontrado, retorna erro 404
        raise HTTPException(status_code=404, detail=str(e))

@app.post("/api/session/complete")
async def complete_session(request: Request):
    """
    API para finalizar uma sessão de jogo e avaliar o desenho
    Recebe: { "session_id": "id", "drawing_data": "base64", "time_spent": segundos }
    Retorna: Resultado da avaliação, pontos ganhos, XP, conquistas e level up
    """
    # Extrai os dados da requisição
    data = await request.json()
    session_id = data.get("session_id")
    drawing_data = data.get("drawing_data")  # Imagem em base64
    time_spent = data.get("time_spent", 0)  # Tempo gasto desenhando
    
    try:
        # Busca a sessão pelo ID
        session = game_manager.sessions.get(session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Sessao nao encontrada")
        
        # Extrai apenas os dados base64 da imagem (remove o prefixo "data:image/png;base64,")
        img_data = drawing_data.split(",")[1] if "," in drawing_data else drawing_data
        
        # Envia o desenho para a IA Gemini analisar
        ai_result = gemini_service.analyze_drawing(img_data, session.prompt.text)
        
        # Finaliza a sessão e calcula pontos, XP e conquistas
        result = game_manager.complete_session(session_id, drawing_data, ai_result, time_spent)
        
        # Retorna todos os resultados da sessão
        return {
            "correct": result["session"].correct,  # Se a IA acertou
            "guesses": result["session"].ai_guesses,  # Palpites da IA
            "confidence": ai_result.get("confidence", 50),  # Confiança da IA (0-100%)
            "feedback": ai_result.get("feedback", ""),  # Feedback textual da IA
            "reaction": ai_result.get("reaction", "thinking"),  # Reação da IA (emoji/texto)
            "score": result["rewards"]["score"],  # Pontos ganhos
            "xp_gained": result["rewards"]["xp"],  # XP ganho
            "achievements": result["achievements"],  # Novas conquistas desbloqueadas
            "level_up": result["level_up"],  # Se subiu de nível
            "new_level": result["new_level"],  # Novo nível (se level_up = true)
            "player_stats": {  # Estatísticas atualizadas do jogador
                "level": result["session"].player.level,
                "xp": result["session"].player.xp,
                "streak": result["session"].player.streak,
                "total_drawings": result["session"].player.total_drawings
            }
        }
    except Exception as e:
        # Em caso de erro, imprime no console e retorna erro 500
        print(f"Erro: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ===== ROTA DE HEALTH CHECK =====

@app.get("/health")
async def health():
    """
    Rota de verificação de saúde da API
    Usada para monitoramento e verificar se o servidor está funcionando
    """
    return {"status": "ok"}
