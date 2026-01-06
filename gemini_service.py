"""
Script de teste para verificar conexão com Google Gemini API
"""

import os
import sys
import requests
from dotenv import load_dotenv
import base64
import json
from typing import List, Dict, Any

# Carregar variáveis de ambiente
load_dotenv()


class GeminiService:
    """Integração com Google Gemini (Generative Language API).

    - Usa `GEMINI_API_KEY` a partir do ambiente.
    - Faz uma requisição simples ao endpoint `:generateContent` e tenta
      extrair texto com palpites e confidências.
    - Se não houver `GEMINI_API_KEY`, retorna um stub local.
    """

    DEFAULT_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.0")

    def __init__(self):
        self.api_key = os.getenv("GEMINI_API_KEY")
        self.model = self.DEFAULT_MODEL

    def _extract_text_from_response(self, result: Dict[str, Any]) -> str:
        # suportar formas diferentes de resposta
        # formato antigo: candidates -> content -> parts -> text
        try:
            candidates = result.get("candidates")
            if candidates and isinstance(candidates, list):
                return candidates[0].get("content", {}).get("parts", [{}])[0].get("text", "")
        except Exception:
            pass

        # novo formato possível: outputs -> content -> [text]
        try:
            outputs = result.get("outputs")
            if outputs and isinstance(outputs, list):
                # procurar o primeiro campo textual
                for out in outputs:
                    if isinstance(out, dict):
                        if "content" in out:
                            content = out["content"]
                            if isinstance(content, list) and content:
                                return content[0].get("text", "") if isinstance(content[0], dict) else str(content[0])
                        if "text" in out:
                            return out.get("text", "")
        except Exception:
            pass

        # fallback: tentar serializar tudo
        try:
            return json.dumps(result)
        except Exception:
            return ""

    def analyze_drawing(self, img_data: str, prompt_text: str) -> dict:
        """Analisa uma imagem codificada em base64 junto ao prompt.

        Retorna dicionário com chaves esperadas pelo `game_manager`/`main.py`:
        - `guesses`: lista de strings
        - `confidence`: inteiro 0-100
        - `feedback`: texto
        - `reaction`: texto curto
        - `correct`: boolean
        """
        # Se não houver API key, retorna um stub previsível
        if not self.api_key:
            return {
                "guesses": [],
                "confidence": 50,
                "feedback": "No API key provided; returning stub result.",
                "reaction": "no-api-key",
                "correct": False,
            }

        # modo de API: 'rest' usa o endpoint :generate, 'compat' tenta generateContent/generateText
        api_mode = os.getenv("GEMINI_API_MODE", "compat")

        # (payload/model setup continues below after composing the prompt)
        # Se não houver API key, retorna um stub previsível
        if not self.api_key:
            return {
                "guesses": [],
                "confidence": 50,
                "feedback": "No API key provided; returning stub result.",
                "reaction": "no-api-key",
                "correct": False,
            }

        # modo de API: 'rest' usa o endpoint :generate, 'compat' tenta generateContent/generateText
        api_mode = os.getenv("GEMINI_API_MODE", "compat")

        # tentar combinações de modelo/endpoint como fallback
        models_to_try = [self.model, f"{self.model}-mini", os.getenv("GEMINI_MODEL_ALT", "text-bison-001")]
        actions = ["generateContent", "generateText"]

        user_prompt = (
            "Você recebe um desenho codificado em base64 e um prompt alvo. "
            "Retorne um JSON com a chave 'guesses' contendo até 5 objetos {label, confidence}, "
            "a chave 'feedback' com comentário breve e 'reaction' com uma palavra curta.\n"
            f"Prompt alvo: {prompt_text}\n"
            "Desenho(base64): "
            f"{img_data[:200]}"
        )

        payload_candidates = [
            {"contents": [{"parts": [{"text": user_prompt}]}], "generationConfig": {"temperature": 0.2, "maxOutputTokens": 300}},
            {"text": user_prompt},
            {"input": user_prompt},
            {"prompt": user_prompt},
            {"instances": [{"text": user_prompt}]},
        ]

        # REST-specific payload shapes for newer generate endpoint
        payload_candidates_rest = [
            {"instances": [{"input": user_prompt}]},
            {"instances": [{"content": [{"type": "text", "text": user_prompt}]}]},
            {"input": user_prompt},
            {"prompt": user_prompt},
        ]

        last_exception = None
        result = None
        used_model = None
        used_action = None

        if api_mode == "rest":
            actions = ["generate", "generateContent", "generateText"]
            payloads_to_try = payload_candidates_rest
        else:
            payloads_to_try = payload_candidates

        for model_try in models_to_try:
            if not model_try:
                continue
            for action in actions:
                for base in ("https://generativelanguage.googleapis.com/v1beta", "https://generativelanguage.googleapis.com/v1"):
                    url = f"{base}/models/{model_try}:{action}?key={self.api_key}"
                    for payload in payloads_to_try:
                        try:
                            resp = requests.post(url, json=payload, timeout=15)
                            if resp.status_code == 200:
                                result = resp.json()
                                used_model = model_try
                                used_action = action
                                break
                            else:
                                last_exception = requests.exceptions.HTTPError(f"{resp.status_code} {resp.text}")
                                continue
                        except requests.exceptions.RequestException as e:
                            last_exception = e
                            continue
                    if result is not None:
                        break
                if result is not None:
                    break
            if result is not None:
                break

        if result is None:
            # tentar buscar modelos disponíveis na conta e reexecutar tentativa com eles
            try:
                models_url = f"https://generativelanguage.googleapis.com/v1/models?key={self.api_key}"
                ml = requests.get(models_url, timeout=10)
                if ml.status_code == 200:
                    available = ml.json().get("models", [])
                    fallback_models = []
                    for m in available:
                        name = m.get("name")
                        if not name:
                            continue
                        # remover prefixo 'models/' se presente
                        fallback_models.append(name.replace("models/", ""))

                    # tentar novamente com modelos descobertos
                    for model_try in fallback_models:
                        if not model_try:
                            continue
                        for action in actions:
                            for base in ("https://generativelanguage.googleapis.com/v1beta", "https://generativelanguage.googleapis.com/v1"):
                                url = f"{base}/models/{model_try}:{action}?key={self.api_key}"
                                for payload in payloads_to_try:
                                    try:
                                        resp = requests.post(url, json=payload, timeout=15)
                                        if resp.status_code == 200:
                                            result = resp.json()
                                            used_model = model_try
                                            used_action = action
                                            break
                                        else:
                                            last_exception = requests.exceptions.HTTPError(f"{resp.status_code} {resp.text}")
                                            continue
                                    except requests.exceptions.RequestException as e:
                                        last_exception = e
                                        continue
                                if result is not None:
                                    break
                            if result is not None:
                                break
                        if result is not None:
                            break
            except Exception:
                # ignorar falha na listagem e cair para retorno de erro abaixo
                pass

        if result is None:
            # nenhum endpoint funcionou
            return {
                "guesses": [],
                "confidence": 0,
                "feedback": f"Request error: {last_exception}",
                "reaction": "error",
                "correct": False,
            }

        # opcional: logar modelo/ação usados (não print aqui para não poluir)

        text = self._extract_text_from_response(result).strip()

        # tentar extrair JSON do texto retornado
        parsed = None
        try:
            parsed = json.loads(text)
        except Exception:
            # tentativa de extrair JSON dentro do texto
            start = text.find("{")
            end = text.rfind("}")
            if start != -1 and end != -1 and end > start:
                snippet = text[start:end+1]
                try:
                    parsed = json.loads(snippet)
                except Exception:
                    parsed = None

        guesses: List[str] = []
        confidence = 50
        feedback = ""
        reaction = "thinking"
        correct = False

        if isinstance(parsed, dict):
            g = parsed.get("guesses") or parsed.get("predictions")
            if isinstance(g, list):
                guesses = [str(item.get("label") if isinstance(item, dict) else str(item)) for item in g[:5]]
                # tentar pegar confidence do primeiro
                first = g[0] if g else None
                if isinstance(first, dict) and first.get("confidence") is not None:
                    try:
                        confidence = int(first.get("confidence"))
                    except Exception:
                        pass
            feedback = parsed.get("feedback", "") or parsed.get("comment", "")
            reaction = parsed.get("reaction", reaction)
            # avaliar acerto comparando rótulo principal com prompt_text simples
            if guesses:
                correct = prompt_text.lower() in guesses[0].lower() or guesses[0].lower() in prompt_text.lower()
        else:
            # fallback: split por linhas e pegar possíveis guesses
            lines = [l.strip() for l in text.splitlines() if l.strip()]
            if lines:
                guesses = [lines[0]]
                feedback = "\n".join(lines[1:4])

        return {
            "guesses": guesses,
            "confidence": confidence,
            "feedback": feedback,
            "reaction": reaction,
            "correct": correct,
        }
