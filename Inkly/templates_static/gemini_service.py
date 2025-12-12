"""
Inkly - Serviço de integração com Google Gemini
"""

import os
import requests
from typing import List, Dict
import json


class GeminiService:
    """Serviço para analisar desenhos com Google Gemini"""
    
    def __init__(self, api_key: str = None):
        self.api_key = api_key or os.getenv("GEMINI_API_KEY")
        if not self.api_key:
            raise ValueError("GEMINI_API_KEY não encontrada")
        
        self.base_url = "https://generativelanguage.googleapis.com/v1beta/models"
        self.model = "gemini-2.0-flash-exp"
    
    def analyze_drawing(self, image_base64: str, target: str) -> Dict:
        """
        Analisa o desenho e retorna palpites
        
        Args:
            image_base64: Imagem em base64 (sem prefixo)
            target: O que deveria ser desenhado
            
        Returns:
            Dict com guesses, correct, confidence, feedback
        """
        try:
            url = f"{self.base_url}/{self.model}:generateContent?key={self.api_key}"
            
            prompt = f"""Analise este desenho e responda APENAS em formato JSON válido.

O usuário tentou desenhar: "{target}"

Retorne um JSON com:
- "guesses": lista com 3 palpites do que você acha que é (do mais provável ao menos)
- "correct": boolean se acertou o desenho esperado
- "confidence": número de 0 a 100 da sua confiança
- "feedback": string engraçada e encorajadora (em português)
- "reaction": "happy", "confused", "amazed" ou "thinking"

Seja criativo e divertido no feedback! Não explique, apenas retorne o JSON."""

            payload = {
                "contents": [{
                    "parts": [
                        {"text": prompt},
                        {
                            "inline_data": {
                                "mime_type": "image/png",
                                "data": image_base64
                            }
                        }
                    ]
                }],
                "generationConfig": {
                    "temperature": 0.9,
                    "topK": 40,
                    "topP": 0.95,
                    "maxOutputTokens": 300,
                }
            }
            
            response = requests.post(url, json=payload, timeout=30)
            response.raise_for_status()
            
            result = response.json()
            text = result['candidates'][0]['content']['parts'][0]['text']
            
            # Extrair JSON da resposta
            text = text.strip()
            if text.startswith('```json'):
                text = text[7:]
            if text.startswith('```'):
                text = text[3:]
            if text.endswith('```'):
                text = text[:-3]
            text = text.strip()
            
            data = json.loads(text)
            
            # Validar estrutura
            return {
                "guesses": data.get("guesses", ["não sei", "algo", "desenho"]),
                "correct": data.get("correct", False),
                "confidence": data.get("confidence", 50),
                "feedback": data.get("feedback", "Interessante! 🎨"),
                "reaction": data.get("reaction", "thinking")
            }
            
        except Exception as e:
            print(f"Erro na API Gemini: {e}")
            # Fallback com resposta simpática
            return {
                "guesses": ["desenho abstrato", "arte moderna", target],
                "correct": False,
                "confidence": 30,
                "feedback": "Hmm... sua criatividade me confundiu! 🤔✨",
                "reaction": "confused"
            }
    
    def generate_surprise_feedback(self, emotion: str) -> str:
        """Gera feedback surpresa baseado na emoção da IA"""
        feedbacks = {
            "happy": [
                "UAU! Isso ficou incrível! 🎉",
                "Você é um artista nato! ⭐",
                "Perfeito! Mal posso esperar pelo próximo! 🌟"
            ],
            "confused": [
                "Hmm... isso é arte abstrata? 🤔",
                "Meu cérebro de IA está confuso mas adorei! 💭",
                "Interessante... muito interessante! 🧐"
            ],
            "amazed": [
                "CARAMBA! Como você fez isso?! 😱",
                "Isso superou minhas expectativas! 🚀",
                "Sou uma IA e estou impressionado! 🤯"
            ],
            "thinking": [
                "Deixa eu pensar... 🤔",
                "Processando sua obra-prima... ⚙️",
                "Analisando cada detalhe... 🔍"
            ]
        }
        
        import random
        return random.choice(feedbacks.get(emotion, feedbacks["thinking"]))