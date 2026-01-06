"""
Script de teste para verificar conexão com Google Gemini API
"""

# Importações necessárias para o funcionamento do serviço
import os  # Para acessar variáveis de ambiente
import sys  # Para operações do sistema
import requests  # Para fazer requisições HTTP à API do Gemini
from dotenv import load_dotenv  # Para carregar variáveis de ambiente do arquivo .env
import base64  # Para trabalhar com imagens codificadas em base64
import json  # Para processar respostas JSON da API
from typing import List, Dict, Any  # Para type hints

# Carregar variáveis de ambiente do arquivo .env
load_dotenv()


class GeminiService:
    """Integração com Google Gemini (Generative Language API).

    - Usa `GEMINI_API_KEY` a partir do ambiente.
    - Faz uma requisição simples ao endpoint `:generateContent` e tenta
      extrair texto com palpites e confidências.
    - Se não houver `GEMINI_API_KEY`, retorna um stub local.
    """

    # Modelo padrão a ser usado, obtido da variável de ambiente ou usando "gemini-2.0" como padrão
    DEFAULT_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.0")

    def __init__(self):
        """Inicializa o serviço do Gemini."""
        # Obtém a chave da API do ambiente
        self.api_key = os.getenv("GEMINI_API_KEY")
        # Define o modelo a ser usado
        self.model = self.DEFAULT_MODEL

    def _extract_text_from_response(self, result: Dict[str, Any]) -> str:
        """Extrai o texto da resposta da API do Gemini.
        
        A API pode retornar diferentes formatos de resposta, então tentamos
        múltiplas estratégias para extrair o texto.
        
        Args:
            result: Dicionário com a resposta da API
            
        Returns:
            String com o texto extraído ou vazio se não conseguir extrair
        """
        # Suportar formas diferentes de resposta
        # Formato antigo: candidates -> content -> parts -> text
        try:
            candidates = result.get("candidates")
            if candidates and isinstance(candidates, list):
                # Navega pela estrutura aninhada para encontrar o texto
                return candidates[0].get("content", {}).get("parts", [{}])[0].get("text", "")
        except Exception:
            # Se falhar, tenta o próximo formato
            pass

        # Novo formato possível: outputs -> content -> [text]
        try:
            outputs = result.get("outputs")
            if outputs and isinstance(outputs, list):
                # Procurar o primeiro campo textual nos outputs
                for out in outputs:
                    if isinstance(out, dict):
                        # Tenta encontrar o campo "content"
                        if "content" in out:
                            content = out["content"]
                            if isinstance(content, list) and content:
                                return content[0].get("text", "") if isinstance(content[0], dict) else str(content[0])
                        # Tenta encontrar o campo "text" diretamente
                        if "text" in out:
                            return out.get("text", "")
        except Exception:
            # Se falhar, tenta o próximo método
            pass

        # Fallback: tentar serializar tudo como JSON
        try:
            return json.dumps(result)
        except Exception:
            # Se tudo falhar, retorna string vazia
            return ""

    def analyze_drawing(self, img_data: str, prompt_text: str) -> dict:
        """Analisa uma imagem codificada em base64 junto ao prompt.

        Retorna dicionário com chaves esperadas pelo `game_manager`/`main.py`:
        - `guesses`: lista de strings com os palpites da IA
        - `confidence`: inteiro 0-100 indicando confiança da IA
        - `feedback`: texto com comentário sobre o desenho
        - `reaction`: texto curto com reação da IA
        - `correct`: boolean indicando se acertou
        
        Args:
            img_data: String com a imagem codificada em base64
            prompt_text: String com o prompt/palavra alvo do desenho
            
        Returns:
            Dicionário com os resultados da análise
        """
        # Se não houver API key configurada, retorna um resultado stub (falso)
        if not self.api_key:
            return {
                "guesses": [],
                "confidence": 50,
                "feedback": "No API key provided; returning stub result.",
                "reaction": "no-api-key",
                "correct": False,
            }

        # Modo de API: 'rest' usa o endpoint :generate, 'compat' tenta generateContent/generateText
        api_mode = os.getenv("GEMINI_API_MODE", "compat")

        # Lista de modelos para tentar em ordem de preferência
        models_to_try = [self.model, f"{self.model}-mini", os.getenv("GEMINI_MODEL_ALT", "text-bison-001")]
        # Ações/endpoints diferentes para tentar
        actions = ["generateContent", "generateText"]

        # Monta o prompt para a IA analisar o desenho
        user_prompt = (
            "Você recebe um desenho codificado em base64 e um prompt alvo. "
            "Retorne um JSON com a chave 'guesses' contendo até 5 objetos {label, confidence}, "
            "a chave 'feedback' com comentário breve e 'reaction' com uma palavra curta.\n"
            f"Prompt alvo: {prompt_text}\n"
            "Desenho(base64): "
            f"{img_data[:200]}"  # Apenas os primeiros 200 caracteres da imagem
        )

        # Diferentes formatos de payload para tentar com a API
        # Cada formato pode funcionar com diferentes versões/endpoints da API
        payload_candidates = [
            # Formato padrão com contents e generationConfig
            {"contents": [{"parts": [{"text": user_prompt}]}], "generationConfig": {"temperature": 0.2, "maxOutputTokens": 300}},
            # Formato simples com apenas text
            {"text": user_prompt},
            # Formato com input
            {"input": user_prompt},
            # Formato com prompt
            {"prompt": user_prompt},
            # Formato com instances (para alguns endpoints)
            {"instances": [{"text": user_prompt}]},
        ]

        # Payloads específicos para o endpoint REST/generate
        payload_candidates_rest = [
            {"instances": [{"input": user_prompt}]},
            {"instances": [{"content": [{"type": "text", "text": user_prompt}]}]},
            {"input": user_prompt},
            {"prompt": user_prompt},
        ]

        # Variáveis para controle de tentativas
        last_exception = None  # Armazena o último erro ocorrido
        result = None  # Armazenará o resultado bem-sucedido
        used_model = None  # Qual modelo funcionou
        used_action = None  # Qual ação/endpoint funcionou

        # Define quais payloads usar baseado no modo de API
        if api_mode == "rest":
            actions = ["generate", "generateContent", "generateText"]
            payloads_to_try = payload_candidates_rest
        else:
            payloads_to_try = payload_candidates

        # Loop triplo para tentar todas as combinações de modelo/ação/base URL/payload
        for model_try in models_to_try:
            if not model_try:
                continue
            # Tenta diferentes ações (endpoints)
            for action in actions:
                # Tenta diferentes versões da API (v1beta e v1)
                for base in ("https://generativelanguage.googleapis.com/v1beta", "https://generativelanguage.googleapis.com/v1"):
                    # Monta a URL completa com modelo, ação e chave de API
                    url = f"{base}/models/{model_try}:{action}?key={self.api_key}"
                    # Tenta diferentes formatos de payload
                    for payload in payloads_to_try:
                        try:
                            # Faz a requisição POST para a API
                            resp = requests.post(url, json=payload, timeout=15)
                            if resp.status_code == 200:
                                # Sucesso! Armazena o resultado
                                result = resp.json()
                                used_model = model_try
                                used_action = action
                                break
                            else:
                                # Falhou, armazena o erro e tenta próximo
                                last_exception = requests.exceptions.HTTPError(f"{resp.status_code} {resp.text}")
                                continue
                        except requests.exceptions.RequestException as e:
                            # Erro de rede/timeout, armazena e tenta próximo
                            last_exception = e
                            continue
                    # Se encontrou resultado, para de tentar
                    if result is not None:
                        break
                if result is not None:
                    break
            if result is not None:
                break

        # Se nenhuma tentativa funcionou, tenta descobrir modelos disponíveis
        if result is None:
            try:
                # Busca a lista de modelos disponíveis na conta
                models_url = f"https://generativelanguage.googleapis.com/v1/models?key={self.api_key}"
                ml = requests.get(models_url, timeout=10)
                if ml.status_code == 200:
                    available = ml.json().get("models", [])
                    fallback_models = []
                    # Extrai os nomes dos modelos disponíveis
                    for m in available:
                        name = m.get("name")
                        if not name:
                            continue
                        # Remove o prefixo 'models/' se presente
                        fallback_models.append(name.replace("models/", ""))

                    # Tenta novamente com os modelos descobertos
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
                # Se falhar na listagem, ignora e cai para retorno de erro abaixo
                pass

        # Se todas as tentativas falharam, retorna erro
        if result is None:
            return {
                "guesses": [],
                "confidence": 0,
                "feedback": f"Request error: {last_exception}",
                "reaction": "error",
                "correct": False,
            }

        # Opcional: logar modelo/ação usados (não print aqui para não poluir)

        # Extrai o texto da resposta usando o método auxiliar
        text = self._extract_text_from_response(result).strip()
        
        # Limpar blocos de markdown (```...```), se existirem
        import re
        # Remove blocos markdown com linguagem especificada
        text = re.sub(r"```[a-zA-Z]*\\n([\\s\\S]*?)```", r"\1", text)
        # Remove blocos markdown simples
        text = re.sub(r"```([\\s\\S]*?)```", r"\1", text)
        # Remove marcadores de código que sobraram
        text = text.replace('```', '')

        # Tenta fazer parse do texto como JSON
        parsed = None
        try:
            parsed = json.loads(text)
        except Exception:
            # Se falhar, tenta encontrar um JSON dentro do texto
            start = text.find("{")
            end = text.rfind("}")
            if start != -1 and end != -1 and end > start:
                snippet = text[start:end+1]
                try:
                    parsed = json.loads(snippet)
                except Exception:
                    parsed = None

        # Valores padrão para o retorno
        guesses: List[str] = []
        confidence = 50
        feedback = ""
        reaction = "thinking"
        correct = False

        # Se conseguiu fazer parse do JSON, extrai os dados
        if isinstance(parsed, dict):
            # Obtém a lista de palpites (pode estar em 'guesses' ou 'predictions')
            g = parsed.get("guesses") or parsed.get("predictions")
            if isinstance(g, list):
                # Extrai até 5 palpites, convertendo para string
                guesses = [str(item.get("label") if isinstance(item, dict) else str(item)) for item in g[:5]]
                # Tenta pegar o valor de confidence do primeiro palpite
                first = g[0] if g else None
                if isinstance(first, dict) and first.get("confidence") is not None:
                    try:
                        confidence = int(first.get("confidence"))
                    except Exception:
                        pass
            # Extrai feedback e reaction
            feedback = parsed.get("feedback", "") or parsed.get("comment", "")
            reaction = parsed.get("reaction", reaction)
            # Avalia se acertou comparando o primeiro palpite com o prompt
            if guesses:
                correct = prompt_text.lower() in guesses[0].lower() or guesses[0].lower() in prompt_text.lower()
        else:
            # Fallback: se não conseguiu fazer parse, tenta extrair algo do texto
            lines = [l.strip() for l in text.splitlines() if l.strip()]
            if lines:
                # Usa a primeira linha como palpite
                guesses = [lines[0]]
                # Mensagem amigável de fallback
                feedback = "A IA ficou sem palavras com sua criatividade!"
            else:
                # Se não há nada, usa mensagem padrão
                feedback = "A IA ficou sem palavras com sua criatividade!"

        # Retorna o resultado estruturado
        return {
            "guesses": guesses,
            "confidence": confidence,
            "feedback": feedback,
            "reaction": reaction,
            "correct": correct,
        }
