"""
Inkly - Gerenciador de Jogo
Sistema de gerenciamento de sessões e jogadores em memória
"""

# Importações necessárias para tipagem, manipulação de datas e geração de IDs únicos
from typing import Dict, Optional, List
from datetime import datetime
import uuid
import random

# Importa os modelos de dados do sistema
from models import (
    Player, DrawingSession, Prompt, PromptGenerator,
    Difficulty, BrushType, AchievementSystem
)


class GameManager:
    """Gerencia jogadores e sessões de jogo"""
    
    def __init__(self):
        # Dicionário que armazena todos os jogadores ativos, indexados por ID
        self.players: Dict[str, Player] = {}
        
        # Dicionário que armazena todas as sessões de desenho ativas, indexadas por ID
        self.sessions: Dict[str, DrawingSession] = {}
        
        # Dicionário para gerenciar salas multiplayer: room_id -> lista de player_ids
        self.multiplayer_rooms: Dict[str, List[str]] = {}
        
    def create_player(self, name: str) -> Player:
        """
        Cria um novo jogador no sistema
        
        Args:
            name: Nome do jogador
            
        Returns:
            Player: Instância do jogador criado
        """
        # Gera um ID único para o jogador usando UUID
        player_id = str(uuid.uuid4())
        
        # Cria uma nova instância de Player com os dados iniciais
        player = Player(
            id=player_id,
            name=name,
            last_played=datetime.now()  # Registra o momento da criação
        )
        
        # Armazena o jogador no dicionário de jogadores
        self.players[player_id] = player
        
        return player
    
    def get_player(self, player_id: str) -> Optional[Player]:
        """
        Retorna jogador pelo ID
        
        Args:
            player_id: ID único do jogador
            
        Returns:
            Player ou None se não encontrado
        """
        return self.players.get(player_id)
    
    def start_session(
        self, 
        player_id: str, 
        difficulty: Difficulty = Difficulty.MEDIUM,
        surprise_mode: bool = True
    ) -> DrawingSession:
        """
        Inicia uma nova sessão de desenho para um jogador
        
        Args:
            player_id: ID do jogador
            difficulty: Nível de dificuldade inicial
            surprise_mode: Se True, adiciona elementos surpresa ao prompt
            
        Returns:
            DrawingSession: Nova sessão de desenho criada
        """
        # Busca o jogador pelo ID
        player = self.get_player(player_id)
        
        # Se o jogador não existir, cria um automaticamente
        if not player:
            player = self.create_player(f"Player_{player_id}")
            player.id = player_id  # Usa o ID fornecido ao invés de gerar um novo
            self.players[player_id] = player
        
        # Ajusta a dificuldade baseado no nível do jogador
        # Jogadores iniciantes (nível < 3) sempre começam no fácil
        if player.level < 3:
            difficulty = Difficulty.EASY
        # Jogadores intermediários (nível 3-6) jogam no médio
        elif player.level < 7:
            difficulty = Difficulty.MEDIUM
        # Jogadores avançados (nível 7+) alternam entre médio e difícil
        else:
            difficulty = random.choice([Difficulty.MEDIUM, Difficulty.HARD])
        
        # Gera um novo prompt (desafio de desenho) baseado na dificuldade
        prompt = PromptGenerator.generate(difficulty, surprise=surprise_mode)
        
        # Gera um ID único para a sessão
        session_id = str(uuid.uuid4())
        
        # Cria uma nova sessão de desenho
        session = DrawingSession(
            session_id=session_id,
            player=player,
            prompt=prompt,
            started_at=datetime.now()  # Registra o horário de início
        )
        
        # Armazena a sessão no dicionário de sessões ativas
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
        Completa uma sessão de desenho e calcula todas as recompensas
        
        Args:
            session_id: ID da sessão a ser completada
            drawing_data: Dados do desenho em formato string
            ai_result: Resultado da análise da IA (palpites, acurácia, etc)
            time_spent: Tempo gasto desenhando em segundos
            
        Returns:
            Dict contendo:
                - session: Sessão completada
                - rewards: Pontuação e breakdown dos bônus
                - achievements: Conquistas desbloqueadas
                - level_up: Se o jogador subiu de nível
                - new_level: Novo nível (se houver level up)
                
        Raises:
            ValueError: Se a sessão não for encontrada
        """
        # Busca a sessão pelo ID
        session = self.sessions.get(session_id)
        if not session:
            raise ValueError("Sessão não encontrada")
        
        # Referência ao jogador da sessão
        player = session.player
        
        # Atualiza os dados da sessão com o resultado
        session.drawing_data = drawing_data  # Salva o desenho
        session.ai_guesses = ai_result.get("guesses", [])  # Palpites da IA
        session.correct = ai_result.get("correct", False)  # Se acertou
        session.time_spent = time_spent  # Tempo gasto
        
        # Calcula a pontuação base (100 pontos se acertou, 20 se errou)
        base_score = 100 if session.correct else 20
        
        # Bônus de tempo: quanto mais rápido, mais pontos (5 pontos por segundo economizado)
        time_bonus = max(0, int((session.prompt.time_limit - time_spent) * 5))
        
        # Bônus de confiança da IA: quanto mais confiante a IA, mais pontos
        confidence_bonus = int(ai_result.get("confidence", 0) / 2)
        
        # Calcula a pontuação total somando base + bônus de tempo + bônus de confiança
        session.score = base_score + time_bonus + confidence_bonus
        
        # Atualiza as estatísticas do jogador
        player.total_drawings += 1  # Incrementa total de desenhos
        player.last_played = datetime.now()  # Atualiza última vez jogado
        
        # Se acertou o desenho
        if session.correct:
            player.correct_guesses += 1  # Incrementa acertos
            player.streak += 1  # Incrementa sequência de acertos
        else:
            player.streak = 0  # Reseta a sequência de acertos
        
        # Adiciona XP (experiência) ao jogador e verifica se subiu de nível
        level_up = player.add_xp(session.score)
        
        # Verifica e desbloqueia novos pincéis baseado no nível
        self._unlock_brushes(player)
        
        # Verifica se o jogador desbloqueou novas conquistas (achievements)
        new_achievements = AchievementSystem.check_achievements(
            player, session
        )
        
        # Adiciona XP bônus pelas conquistas desbloqueadas
        for achievement_id in new_achievements:
            achievement = AchievementSystem.ACHIEVEMENTS[achievement_id]
            player.add_xp(achievement["xp"])
        
        # Retorna um dicionário completo com todos os resultados
        return {
            "session": session,  # A sessão completada
            "rewards": {
                "score": session.score,  # Pontuação total
                "xp": session.score,  # XP ganho (igual à pontuação)
                "breakdown": {  # Detalhamento dos pontos
                    "base": base_score,
                    "time_bonus": time_bonus,
                    "confidence_bonus": confidence_bonus
                }
            },
            "achievements": [  # Lista de conquistas desbloqueadas
                {
                    "id": aid,
                    **AchievementSystem.ACHIEVEMENTS[aid]
                }
                for aid in new_achievements
            ],
            "level_up": level_up,  # Boolean indicando se subiu de nível
            "new_level": player.level if level_up else None  # Novo nível ou None
        }
    
    def _unlock_brushes(self, player: Player):
        """
        Desbloqueia pincéis especiais baseado no nível do jogador
        
        Args:
            player: Jogador para verificar desbloqueios
        """
        # Dicionário mapeando nível -> tipo de pincel desbloqueado
        unlocks = {
            3: BrushType.NEON,      # Nível 3 desbloqueia pincel neon
            5: BrushType.SPRAY,     # Nível 5 desbloqueia spray
            7: BrushType.MARKER,    # Nível 7 desbloqueia marcador
            10: BrushType.SPARKLE   # Nível 10 desbloqueia brilho/sparkle
        }
        
        # Itera pelos desbloqueios e adiciona os pincéis apropriados
        for level, brush in unlocks.items():
            # Se o jogador atingiu o nível necessário, desbloqueia o pincel
            if player.level >= level:
                player.unlock_brush(brush)
    
    def create_multiplayer_room(self, player_id: str) -> str:
        """
        Cria uma nova sala multiplayer
        
        Args:
            player_id: ID do jogador que está criando a sala
            
        Returns:
            str: ID da sala criada (8 caracteres)
        """
        # Gera um ID único de 8 caracteres para a sala
        room_id = str(uuid.uuid4())[:8]
        
        # Cria a sala com o criador como primeiro jogador
        self.multiplayer_rooms[room_id] = [player_id]
        
        return room_id
    
    def join_multiplayer_room(self, room_id: str, player_id: str) -> bool:
        """
        Adiciona um jogador a uma sala multiplayer existente
        
        Args:
            room_id: ID da sala
            player_id: ID do jogador que quer entrar
            
        Returns:
            bool: True se conseguiu entrar, False se a sala não existe
        """
        # Verifica se a sala existe
        if room_id in self.multiplayer_rooms:
            # Adiciona o jogador apenas se ele ainda não estiver na sala
            if player_id not in self.multiplayer_rooms[room_id]:
                self.multiplayer_rooms[room_id].append(player_id)
            return True
        
        # Retorna False se a sala não existir
        return False
    
    def get_room_players(self, room_id: str) -> List[Player]:
        """
        Retorna todos os jogadores em uma sala multiplayer
        
        Args:
            room_id: ID da sala
            
        Returns:
            List[Player]: Lista de objetos Player na sala
        """
        # Busca os IDs dos jogadores na sala (lista vazia se sala não existe)
        player_ids = self.multiplayer_rooms.get(room_id, [])
        
        # Converte IDs em objetos Player, filtrando IDs inválidos
        return [self.get_player(pid) for pid in player_ids if self.get_player(pid)]
    
    def get_leaderboard(self, limit: int = 10) -> List[Dict]:
        """
        Retorna o ranking dos melhores jogadores
        
        Args:
            limit: Número máximo de jogadores a retornar (padrão: 10)
            
        Returns:
            List[Dict]: Lista ordenada dos melhores jogadores com suas estatísticas
        """
        # Ordena todos os jogadores por nível e acertos (decrescente)
        sorted_players = sorted(
            self.players.values(),
            key=lambda p: (p.level, p.correct_guesses),  # Prioriza nível, depois acertos
            reverse=True  # Ordem decrescente (maiores primeiro)
        )
        
        # Retorna uma lista de dicionários com as informações de cada jogador
        return [
            {
                "rank": i + 1,  # Posição no ranking (começa em 1)
                "name": p.name,  # Nome do jogador
                "level": p.level,  # Nível atual
                "xp": p.xp,  # Experiência total
                "total_drawings": p.total_drawings,  # Total de desenhos feitos
                # Calcula a precisão em porcentagem (evita divisão por zero)
                "accuracy": round((p.correct_guesses / p.total_drawings * 100) if p.total_drawings > 0 else 0, 1),
                "streak": p.streak  # Sequência atual de acertos
            }
            # Itera apenas pelos primeiros 'limit' jogadores
            for i, p in enumerate(sorted_players[:limit])
        ]
