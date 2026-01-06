from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from typing import Optional
import os

from gemini_service import GeminiService
from game_manager import GameManager
from models import Difficulty

# Inicializacao
app = FastAPI(title="Inkly")
templates = Jinja2Templates(directory="templates")
app.mount("/static", StaticFiles(directory="static"), name="static")

game_manager = GameManager()
gemini_service = GeminiService()

@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/game", response_class=HTMLResponse)
async def game_page(request: Request, player_id: str):
    player = game_manager.get_player(player_id)
    if not player:
        raise HTTPException(status_code=404, detail="Jogador nao encontrado")
    return templates.TemplateResponse("game.html", {"request": request, "player": player})

@app.get("/leaderboard", response_class=HTMLResponse)
async def leaderboard_page(request: Request):
    leaderboard = game_manager.get_leaderboard(limit=20)
    return templates.TemplateResponse("leaderboard.html", {"request": request, "leaderboard": leaderboard})

@app.post("/api/player/create")
async def create_player(request: Request):
    data = await request.json()
    name = data.get("name")
    if not name:
        raise HTTPException(status_code=400, detail="Nome obrigatorio")
    player = game_manager.create_player(name)
    return {"player_id": player.id, "name": player.name, "level": player.level, "xp": player.xp}

@app.get("/api/player/{player_id}")
async def get_player(player_id: str):
    player = game_manager.get_player(player_id)
    if not player:
        raise HTTPException(status_code=404, detail="Jogador nao encontrado")
    return {
        "id": player.id, "name": player.name, "level": player.level, "xp": player.xp,
        "streak": player.streak, "total_drawings": player.total_drawings,
        "correct_guesses": player.correct_guesses,
        "brushes_unlocked": [b.value for b in player.brushes_unlocked],
        "achievements": player.achievements
    }

@app.post("/api/session/start")
async def start_session(request: Request):
    data = await request.json()
    player_id = data.get("player_id")
    difficulty_str = data.get("difficulty", "medium")
    surprise_mode = data.get("surprise_mode", True)
    
    try:
        dif_map = {"easy": Difficulty.EASY, "medium": Difficulty.MEDIUM, "hard": Difficulty.HARD}
        dif = dif_map.get(difficulty_str, Difficulty.MEDIUM)
        session = game_manager.start_session(player_id, difficulty=dif, surprise_mode=surprise_mode)
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
async def complete_session(request: Request):
    data = await request.json()
    session_id = data.get("session_id")
    drawing_data = data.get("drawing_data")
    time_spent = data.get("time_spent", 0)
    
    try:
        session = game_manager.sessions.get(session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Sessao nao encontrada")
            
        img_data = drawing_data.split(",")[1] if "," in drawing_data else drawing_data
        ai_result = gemini_service.analyze_drawing(img_data, session.prompt.text)
        
        result = game_manager.complete_session(session_id, drawing_data, ai_result, time_spent)
        
        return {
            "correct": result["session"].correct,
            "guesses": result["session"].ai_guesses,
            "confidence": ai_result.get("confidence", 50),
            "feedback": ai_result.get("feedback", ""),
            "reaction": ai_result.get("reaction", "thinking"),
            "score": result["rewards"]["score"],
            "xp_gained": result["rewards"]["xp"],
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
        print(f"Erro: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
async def health():
    return {"status": "ok"}