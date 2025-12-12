"""
Inkly - Backend FastAPI
Servidor principal da aplicação
"""

from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from typing import Optional
import os

from gemini_service import GeminiService
from game_manager import GameManager
from models import Difficulty


# Inicialização
app = FastAPI(title="Inkly - AI Drawing Game")
templates = Jinja2Templates(directory="templates")

# Montar arquivos estáticos
app.mount("/static", StaticFiles(directory="static"), name="static")

# Serviços
game_manager = GameManager()
gemini_service = GeminiService()


# Models para requisições
class CreatePlayerRequest(BaseModel):
    name: str


class StartSessionRequest(BaseModel):
    player_id: str
    difficulty: Optional[str] = "medium"
    surprise_mode: bool = True


class CompleteSessionRequest(BaseModel):
    session_id: str
    drawing_data: str  # Base64 image
    time_spent: float


class JoinRoomRequest(BaseModel):
    player_id: str
    room_id: Optional[str] = None


# Rotas HTML
@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    """Página principal"""
    return templates.TemplateResponse("index.html", {"request": request})


@app.get("/game", response_class=HTMLResponse)
async def game_page(request: Request, player_id: str):
    """Página do jogo"""
    player = game_manager.get_player(player_id)
    if not player:
        raise HTTPException(status_code=404, detail="Jogador não encontrado")
    
    return templates.TemplateResponse("game.html", {
        "request": request,
        "player": player
    })


@app.get("/leaderboard", response_class=HTMLResponse)
async def leaderboard_page(request: Request):
    """Página de ranking"""
    leaderboard = game_manager.get_leaderboard(limit=20)
    return templates.TemplateResponse("leaderboard.html", {
        "request": request,
        "leaderboard": leaderboard
    })


# API Routes
@app.post("/api/player/create")
async def create_player(request: CreatePlayerRequest):
    """Cria novo jogador"""
    player = game_manager.create_player(request.name)
    return {
        "player_id": player.id,
        "name": player.name,
        "level": player.level,
        "xp": player.xp
    }


@app.get("/api/player/{player_id}")
async def get_player(player_id: str):
    """Retorna dados do jogador"""
    player = game_manager.get_player(player_id)
    if not player:
        raise HTTPException(status_code=404, detail="Jogador não encontrado")
    
    return {
        "id": player.id,
        "name": player.name,
        "level": player.level,
        "xp": player.xp,
        "streak": player.streak,
        "total_drawings": player.total_drawings,
        "correct_guesses": player.correct_guesses,
        "accuracy": round((player.correct_guesses / player.total_drawings * 100) if player.total_drawings > 0 else 0, 1),
        "brushes_unlocked": [b.value for b in player.brushes_unlocked],
        "achievements": player.achievements
    }


@app.post("/api/session/start")
async def start_session(request: StartSessionRequest):
    """Inicia nova sessão de desenho"""
    try:
        difficulty_map = {
            "easy": Difficulty.EASY,
            "medium": Difficulty.MEDIUM,
            "hard": Difficulty.HARD
        }
        difficulty = difficulty_map.get(request.difficulty, Difficulty.MEDIUM)
        
        session = game_manager.start_session(
            request.player_id,
            difficulty=difficulty,
            surprise_mode=request.surprise_mode
        )
        
        return {
            "session_id": session.session_id,
            "prompt": {
                "text": session.prompt.text,
                "difficulty": session.prompt.difficulty.value,
                "time_limit": session.prompt.time_limit
            }
        }
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@app.post("/api/session/complete")
async def complete_session(request: CompleteSessionRequest):
    """Completa sessão e analisa desenho"""
    try:
        session = game_manager.sessions.get(request.session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Sessão não encontrada")
        
        # Remove prefixo data:image/png;base64,
        image_data = request.drawing_data.split(",")[1] if "," in request.drawing_data else request.drawing_data
        
        # Analisa com Gemini
        ai_result = gemini_service.analyze_drawing(
            image_data,
            session.prompt.text
        )
        
        # Completa sessão
        result = game_manager.complete_session(
            request.session_id,
            request.drawing_data,
            ai_result,
            request.time_spent
        )
        
        return {
            "correct": result["session"].correct,
            "guesses": result["session"].ai_guesses,
            "confidence": ai_result.get("confidence", 50),
            "feedback": ai_result.get("feedback", ""),
            "reaction": ai_result.get("reaction", "thinking"),
            "score": result["rewards"]["score"],
            "xp_gained": result["rewards"]["xp"],
            "breakdown": result["rewards"]["breakdown"],
            "achievements": result["achievements"],
            "level_up": result["level_up"],
            "new_level": result["new_level"],
            "player_stats": {
                "level": result["session"].player.level,
                "xp": result["session"].player.xp,
                "streak": result["session"].player.streak,
                "total_drawings": result["session"].player.total_drawings
            }
        }
        
    except Exception as e:
        print(f"Erro ao completar sessão: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/leaderboard")
async def get_leaderboard(limit: int = 10):
    """Retorna ranking"""
    return {"leaderboard": game_manager.get_leaderboard(limit)}


@app.post("/api/multiplayer/create")
async def create_room(request: JoinRoomRequest):
    """Cria sala multiplayer"""
    room_id = game_manager.create_multiplayer_room(request.player_id)
    return {"room_id": room_id}


@app.post("/api/multiplayer/join")
async def join_room(request: JoinRoomRequest):
    """Entra em sala multiplayer"""
    if not request.room_id:
        raise HTTPException(status_code=400, detail="room_id obrigatório")
    
    success = game_manager.join_multiplayer_room(request.room_id, request.player_id)
    if not success:
        raise HTTPException(status_code=404, detail="Sala não encontrada")
    
    players = game_manager.get_room_players(request.room_id)
    return {
        "room_id": request.room_id,
        "players": [
            {"id": p.id, "name": p.name, "level": p.level}
            for p in players
        ]
    }


@app.get("/api/multiplayer/room/{room_id}")
async def get_room(room_id: str):
    """Retorna informações da sala"""
    players = game_manager.get_room_players(room_id)
    if not players:
        raise HTTPException(status_code=404, detail="Sala não encontrada")
    
    return {
        "room_id": room_id,
        "players": [
            {"id": p.id, "name": p.name, "level": p.level}
            for p in players
        ]
    }


# Health check
@app.get("/health")
async def health():
    return {"status": "ok", "service": "Inkly"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)