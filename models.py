"""
Inkly - Sistema de Desenho com IA
Models: Classes principais do sistema
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional
from datetime import datetime
from enum import Enum
import random


class Difficulty(Enum):
    EASY = "easy"
    MEDIUM = "medium"
    HARD = "hard"


class BrushType(Enum):
    NORMAL = "normal"
    NEON = "neon"
    SPRAY = "spray"
    MARKER = "marker"
    SPARKLE = "sparkle"


@dataclass
class Prompt:
    """Desafio de desenho"""
    text: str
    difficulty: Difficulty
    time_limit: int = 20
    
    
@dataclass
class Player:
    """Jogador do Inkly"""
    id: str
    name: str
    level: int = 1
    xp: int = 0
    streak: int = 0
    total_drawings: int = 0
    correct_guesses: int = 0
    brushes_unlocked: List[BrushType] = field(default_factory=lambda: [BrushType.NORMAL])
    achievements: List[str] = field(default_factory=list)
    last_played: Optional[datetime] = None
    
    def add_xp(self, points: int) -> bool:
        """Adiciona XP e verifica level up"""
        self.xp += points
        xp_needed = self.level * 100
        
        if self.xp >= xp_needed:
            self.level += 1
            self.xp -= xp_needed
            return True  # Level up!
        return False
    
    def unlock_brush(self, brush: BrushType):
        """Desbloqueia novo pincel"""
        if brush not in self.brushes_unlocked:
            self.brushes_unlocked.append(brush)
    
    def add_achievement(self, achievement: str):
        """Adiciona conquista"""
        if achievement not in self.achievements:
            self.achievements.append(achievement)
            

@dataclass
class DrawingSession:
    """Sessão de desenho"""
    session_id: str
    player: Player
    prompt: Prompt
    started_at: datetime
    drawing_data: Optional[str] = None  # Base64 image
    ai_guesses: List[str] = field(default_factory=list)
    correct: bool = False
    time_spent: float = 0.0
    score: int = 0
    

class PromptGenerator:
    """Gerador de prompts inteligentes"""
    
    EASY_PROMPTS = [
        "cachorro", "gato", "casa", "árvore", "sol", "lua", "estrela",
        "coração", "flor", "carro", "bicicleta", "pássaro", "peixe"
    ]
    
    MEDIUM_PROMPTS = [
        "dragão", "robô", "castelo", "foguete", "dinossauro", "sereia",
        "unicórnio", "pirata", "ninja", "bruxa", "vampiro", "zumbi"
    ]
    
    HARD_PROMPTS = [
        "felicidade", "liberdade", "solidão", "caos", "harmonia",
        "tempo", "memória", "sonho", "impossível", "infinito"
    ]
    
    SURPRISE_PROMPTS = [
        "um gato astronauta", "pizza voadora", "robô jardineiro",
        "dragão dormindo", "árvore de doces", "nuvem com pernas",
        "peixe-guitarra", "cachorro-unicórnio", "casa flutuante"
    ]
    
    @classmethod
    def generate(cls, difficulty: Difficulty, surprise: bool = False) -> Prompt:
        """Gera um prompt baseado na dificuldade"""
        if surprise and random.random() > 0.7:
            text = random.choice(cls.SURPRISE_PROMPTS)
            return Prompt(text, Difficulty.MEDIUM, time_limit=30)
        
        if difficulty == Difficulty.EASY:
            text = random.choice(cls.EASY_PROMPTS)
            time_limit = 20
        elif difficulty == Difficulty.MEDIUM:
            text = random.choice(cls.MEDIUM_PROMPTS)
            time_limit = 25
        else:
            text = random.choice(cls.HARD_PROMPTS)
            time_limit = 30
            
        return Prompt(text, difficulty, time_limit)


class AchievementSystem:
    """Sistema de conquistas"""
    
    ACHIEVEMENTS = {
        "first_draw": {
            "name": "Primeiro Traço",
            "description": "Complete seu primeiro desenho",
            "xp": 50
        },
        "speed_demon": {
            "name": "Demônio da Velocidade",
            "description": "Complete um desenho em menos de 5 segundos",
            "xp": 100
        },
        "perfectionist": {
            "name": "Perfeccionista",
            "description": "Acerte 10 desenhos seguidos",
            "xp": 200
        },
        "night_owl": {
            "name": "Coruja Noturna",
            "description": "Jogue depois da meia-noite",
            "xp": 75
        },
        "level_10": {
            "name": "Artista Dedicado",
            "description": "Alcance o nível 10",
            "xp": 500
        },
        "abstract_master": {
            "name": "Mestre Abstrato",
            "description": "Confunda a IA 5 vezes",
            "xp": 150
        }
    }
    
    @classmethod
    def check_achievements(cls, player: Player, session: DrawingSession) -> List[str]:
        """Verifica e retorna conquistas desbloqueadas"""
        new_achievements = []
        
        # Primeiro desenho
        if player.total_drawings == 1 and "first_draw" not in player.achievements:
            player.add_achievement("first_draw")
            new_achievements.append("first_draw")
        
        # Velocista
        if session.time_spent < 5 and session.correct and "speed_demon" not in player.achievements:
            player.add_achievement("speed_demon")
            new_achievements.append("speed_demon")
        
        # Perfeccionista
        if player.streak >= 10 and "perfectionist" not in player.achievements:
            player.add_achievement("perfectionist")
            new_achievements.append("perfectionist")
        
        # Nível 10
        if player.level >= 10 and "level_10" not in player.achievements:
            player.add_achievement("level_10")
            new_achievements.append("level_10")
        
        # Abstrato
        if "abstract_master" not in player.achievements:
            confused_count = player.total_drawings - player.correct_guesses
            if confused_count >= 5:
                player.add_achievement("abstract_master")
                new_achievements.append("abstract_master")
        
        return new_achievements
    
    