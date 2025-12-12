"""
Inkly - Gerenciador de Jogo
Sistema de gerenciamento de sessões e jogadores em memória
"""

from typing import Dict, Optional, List
from datetime import datetime
import uuid
import random

from models import (
    Player, DrawingSession, Prompt, PromptGenerator,
    Difficulty, BrushType, AchievementSystem
)


class GameManager:
    """Gerencia jogadores e sessões de jogo"""
    
    def __init__(self):
        self.players: Dict[str, Player] = {}
        self.sessions: Dict[str, DrawingSession] = {}
        self.multiplayer_rooms: Dict[str, List[str]] = {}  # room_id: [player_ids]
        
    def create_player(self, name: str) -> Player:
        """Cria um novo jogador"""
        player_id = str(uuid.uuid4())
        player = Player(
            id=player_id,
            name=name,
            last_played=datetime.now()
        )
        self.players[player_id] = player
        return player
    
    def get_player(self, player_id: str) -> Optional[Player]:
        """Retorna jogador pelo ID"""
        return self.players.get(player_id)
    
    def start_session(
        self, 
        player_id: str, 
        difficulty: Difficulty = Difficulty.MEDIUM,
        surprise_mode: bool = True
    ) -> DrawingSession:
        """Inicia uma nova sessão de desenho"""
        player = self.get_player(player_id)
        if not player:
            raise ValueError("Jogador não encontrado")
        
        # Gera prompt baseado no nível do jogador
        if player.level < 3:
            difficulty = Difficulty.EASY
        elif player.level < 7:
            difficulty = Difficulty.MEDIUM
        else:
            difficulty = random.choice([Difficulty.MEDIUM, Difficulty.HARD])
        
        prompt = PromptGenerator.generate(difficulty, surprise=surprise_mode)
        
        session_id = str(uuid.uuid4())
        session = DrawingSession(
            session_id=session_id,
            player=player,
            prompt=prompt,
            started_at=datetime.now()
        )
        
        self.sessions[session_id] = session
        return session
    
    def complete_session(
        self,
        session_id: str,
        drawing_data: str,
        ai_result: Dict,
        time_spent: float
    ) -> Dict:
        """
        Completa uma sessão e calcula recompensas
        
        Returns:
            Dict com session, rewards, achievements, level_up
        """
        session = self.sessions.get(session_id)
        if not session:
            raise ValueError("Sessão não encontrada")
        
        player = session.player
        
        # Atualiza sessão
        session.drawing_data = drawing_data
        session.ai_guesses = ai_result.get("guesses", [])
        session.correct = ai_result.get("correct", False)
        session.time_spent = time_spent
        
        # Calcula pontuação
        base_score = 100 if session.correct else 20
        time_bonus = max(0, int((session.prompt.time_limit - time_spent) * 5))
        confidence_bonus = int(ai_result.get("confidence", 0) / 2)
        
        session.score = base_score + time_bonus + confidence_bonus
        
        # Atualiza estatísticas do jogador
        player.total_drawings += 1
        player.last_played = datetime.now()
        
        if session.correct:
            player.correct_guesses += 1
            player.streak += 1
        else:
            player.streak = 0
        
        # Adiciona XP
        level_up = player.add_xp(session.score)
        
        # Desbloqueia pincéis
        self._unlock_brushes(player)
        
        # Verifica conquistas
        new_achievements = AchievementSystem.check_achievements(
            player, session
        )        
        # XP bônus de conquistas
        for achievement_id in new_achievements:
            achievement = AchievementSystem.ACHIEVEMENTS[achievement_id]
            player.add_xp(achievement["xp"])
        
        return {
            "session": session,
            "rewards": {
                "score": session.score,
                "xp": session.score,
                "breakdown": {
                    "base": base_score,
                    "time_bonus": time_bonus,
                    "confidence_bonus": confidence_bonus
                }
            },
            "achievements": [
                {
                    "id": aid,
                    **AchievementSystem.ACHIEVEMENTS[aid]
                }
                for aid in new_achievements
            ],
            "level_up": level_up,
            "new_level": player.level if level_up else None
        }
    
    def _unlock_brushes(self, player: Player):
        """Desbloqueia pincéis baseado no nível"""
        unlocks = {
            3: BrushType.NEON,
            5: BrushType.SPRAY,
            7: BrushType.MARKER,
            10: BrushType.SPARKLE
        }
        
        for level, brush in unlocks.items():
            if player.level >= level:
                player.unlock_brush(brush)
    
    def create_multiplayer_room(self, player_id: str) -> str:
        """Cria sala multiplayer"""
        room_id = str(uuid.uuid4())[:8]
        self.multiplayer_rooms[room_id] = [player_id]
        return room_id
    
    def join_multiplayer_room(self, room_id: str, player_id: str) -> bool:
        """Entra em sala multiplayer"""
        if room_id in self.multiplayer_rooms:
            if player_id not in self.multiplayer_rooms[room_id]:
                self.multiplayer_rooms[room_id].append(player_id)
            return True
        return False
    
    def get_room_players(self, room_id: str) -> List[Player]:
        """Retorna jogadores em uma sala"""
        player_ids = self.multiplayer_rooms.get(room_id, [])
        return [self.get_player(pid) for pid in player_ids if self.get_player(pid)]
    
    def get_leaderboard(self, limit: int = 10) -> List[Dict]:
        """Retorna ranking dos melhores jogadores"""
        sorted_players = sorted(
            self.players.values(),
            key=lambda p: (p.level, p.correct_guesses),
            reverse=True
        )
        
        return [
            {
                "rank": i + 1,
                "name": p.name,
                "level": p.level,
                "xp": p.xp,
                "total_drawings": p.total_drawings,
                "accuracy": round((p.correct_guesses / p.total_drawings * 100) if p.total_drawings > 0 else 0, 1),
                "streak": p.streak
            }
            for i, p in enumerate(sorted_players[:limit])
        ]