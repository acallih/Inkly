"""
Inkly - Sistema de Desenho com IA
Models: Classes principais do sistema
"""

# Importações necessárias
from dataclasses import dataclass, field  # Para criar classes de dados simplificadas
from typing import List, Dict, Optional  # Para tipagem estática
from datetime import datetime  # Para trabalhar com datas e horários
from enum import Enum  # Para criar enumerações
import random  # Para gerar valores aleatórios


# Enumeração para definir os níveis de dificuldade do jogo
class Difficulty(Enum):
    EASY = "easy"      # Fácil - prompts simples
    MEDIUM = "medium"  # Médio - prompts moderados
    HARD = "hard"      # Difícil - prompts abstratos


# Enumeração para os diferentes tipos de pincel disponíveis
class BrushType(Enum):
    NORMAL = "normal"    # Pincel padrão
    NEON = "neon"        # Pincel neon (brilhante)
    SPRAY = "spray"      # Spray (efeito disperso)
    MARKER = "marker"    # Marcador (traço mais grosso)
    SPARKLE = "sparkle"  # Brilhante (efeito de partículas)


# Classe que representa um desafio/prompt de desenho
@dataclass
class Prompt:
    """Desafio de desenho"""
    text: str              # Texto do prompt que o jogador deve desenhar
    difficulty: Difficulty  # Nível de dificuldade do prompt
    time_limit: int = 20   # Tempo limite em segundos (padrão: 20s)
    
    
# Classe que representa um jogador do Inkly
@dataclass
class Player:
    """Jogador do Inkly"""
    id: str                    # Identificador único do jogador
    name: str                  # Nome do jogador
    level: int = 1             # Nível atual do jogador (começa em 1)
    xp: int = 0                # Pontos de experiência acumulados
    streak: int = 0            # Sequência de acertos consecutivos
    total_drawings: int = 0    # Total de desenhos feitos
    correct_guesses: int = 0   # Quantidade de desenhos que a IA acertou
    # Lista de pincéis desbloqueados (começa apenas com o normal)
    brushes_unlocked: List[BrushType] = field(default_factory=lambda: [BrushType.NORMAL])
    achievements: List[str] = field(default_factory=list)  # Lista de conquistas desbloqueadas
    last_played: Optional[datetime] = None  # Data/hora da última partida
    
    # Método para adicionar XP e verificar se o jogador subiu de nível
    def add_xp(self, points: int) -> bool:
        """Adiciona XP e verifica level up"""
        self.xp += points  # Adiciona os pontos de XP
        xp_needed = self.level * 100  # Calcula XP necessário para próximo nível (nível * 100)
        
        # Se atingiu XP suficiente, sobe de nível
        if self.xp >= xp_needed:
            self.level += 1  # Aumenta o nível
            self.xp -= xp_needed  # Remove o XP usado (mantém o excedente)
            return True  # Retorna True indicando que subiu de nível
        return False  # Retorna False se não subiu de nível
    
    # Método para desbloquear um novo tipo de pincel
    def unlock_brush(self, brush: BrushType):
        """Desbloqueia novo pincel"""
        # Só adiciona se o pincel ainda não foi desbloqueado
        if brush not in self.brushes_unlocked:
            self.brushes_unlocked.append(brush)
    
    # Método para adicionar uma conquista ao jogador
    def add_achievement(self, achievement: str):
        """Adiciona conquista"""
        # Só adiciona se a conquista ainda não foi obtida
        if achievement not in self.achievements:
            self.achievements.append(achievement)
            

# Classe que representa uma sessão de desenho em andamento
@dataclass
class DrawingSession:
    """Sessão de desenho"""
    session_id: str            # ID único da sessão
    player: Player             # Referência ao jogador
    prompt: Prompt             # Prompt/desafio da sessão
    started_at: datetime       # Data/hora de início da sessão
    drawing_data: Optional[str] = None  # Dados do desenho em Base64 (imagem)
    ai_guesses: List[str] = field(default_factory=list)  # Lista de palpites feitos pela IA
    correct: bool = False      # Se a IA acertou o desenho
    time_spent: float = 0.0    # Tempo gasto desenhando em segundos
    score: int = 0             # Pontuação obtida nesta sessão
    

# Classe responsável por gerar prompts/desafios de desenho
class PromptGenerator:
    """Gerador de prompts inteligentes"""
    
    # Lista de prompts fáceis - objetos e conceitos simples do dia-a-dia
    EASY_PROMPTS = [
        "cachorro", "gato", "casa", "árvore", "sol", "lua", "estrela",
        "coração", "flor", "carro", "bicicleta", "pássaro", "peixe"
    ]
    
    # Lista de prompts médios - criaturas fantásticas e personagens
    MEDIUM_PROMPTS = [
        "dragão", "robô", "castelo", "foguete", "dinossauro", "sereia",
        "unicórnio", "pirata", "ninja", "bruxa", "vampiro", "zumbi"
    ]
    
    # Lista de prompts difíceis - conceitos abstratos e filosóficos
    HARD_PROMPTS = [
        "felicidade", "liberdade", "solidão", "caos", "harmonia",
        "tempo", "memória", "sonho", "impossível", "infinito"
    ]
    
    # Lista de prompts surpresa - combinações inusitadas e criativas
    SURPRISE_PROMPTS = [
        "um gato astronauta", "pizza voadora", "robô jardineiro",
        "dragão dormindo", "árvore de doces", "nuvem com pernas",
        "peixe-guitarra", "cachorro-unicórnio", "casa flutuante"
    ]
    
    # Método de classe para gerar um prompt baseado na dificuldade
    @classmethod
    def generate(cls, difficulty: Difficulty, surprise: bool = False) -> Prompt:
        """Gera um prompt baseado na dificuldade"""
        # 30% de chance de gerar um prompt surpresa se a opção estiver ativa
        if surprise and random.random() > 0.7:
            text = random.choice(cls.SURPRISE_PROMPTS)  # Escolhe prompt surpresa aleatório
            return Prompt(text, Difficulty.MEDIUM, time_limit=30)  # Dificuldade média, 30 segundos
        
        # Gera prompt normal baseado na dificuldade escolhida
        if difficulty == Difficulty.EASY:
            text = random.choice(cls.EASY_PROMPTS)  # Escolhe da lista fácil
            time_limit = 20  # 20 segundos para desenhos fáceis
        elif difficulty == Difficulty.MEDIUM:
            text = random.choice(cls.MEDIUM_PROMPTS)  # Escolhe da lista média
            time_limit = 25  # 25 segundos para desenhos médios
        else:  # HARD
            text = random.choice(cls.HARD_PROMPTS)  # Escolhe da lista difícil
            time_limit = 30  # 30 segundos para desenhos difíceis
            
        return Prompt(text, difficulty, time_limit)


# Sistema de conquistas e achievements do jogo
class AchievementSystem:
    """Sistema de conquistas"""
    
    # Dicionário com todas as conquistas disponíveis no jogo
    ACHIEVEMENTS = {
        "first_draw": {
            "name": "Primeiro Traço",  # Nome da conquista
            "description": "Complete seu primeiro desenho",  # Descrição
            "xp": 50  # XP ganho ao desbloquear
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
    
    # Método de classe para verificar e desbloquear conquistas
    @classmethod
    def check_achievements(cls, player: Player, session: DrawingSession) -> List[str]:
        """Verifica e retorna conquistas desbloqueadas"""
        new_achievements = []  # Lista para armazenar novas conquistas desbloqueadas
        
        # Conquista: Primeiro Traço - completar o primeiro desenho
        if player.total_drawings == 1 and "first_draw" not in player.achievements:
            player.add_achievement("first_draw")
            new_achievements.append("first_draw")
        
        # Conquista: Demônio da Velocidade - completar em menos de 5 segundos
        if session.time_spent < 5 and session.correct and "speed_demon" not in player.achievements:
            player.add_achievement("speed_demon")
            new_achievements.append("speed_demon")
        
        # Conquista: Perfeccionista - acertar 10 desenhos consecutivos
        if player.streak >= 10 and "perfectionist" not in player.achievements:
            player.add_achievement("perfectionist")
            new_achievements.append("perfectionist")
        
        # Conquista: Artista Dedicado - alcançar nível 10
        if player.level >= 10 and "level_10" not in player.achievements:
            player.add_achievement("level_10")
            new_achievements.append("level_10")
        
        # Conquista: Mestre Abstrato - confundir a IA 5 vezes
        if "abstract_master" not in player.achievements:
            # Calcula quantas vezes a IA errou (total de desenhos - acertos)
            confused_count = player.total_drawings - player.correct_guesses
            if confused_count >= 5:
                player.add_achievement("abstract_master")
                new_achievements.append("abstract_master")
        
        return new_achievements  # Retorna lista de conquistas recém-desbloqueadas
