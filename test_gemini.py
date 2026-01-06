import os
import requests
import json
from dotenv import load_dotenv

# 1. Carrega as variáveis do .env
load_dotenv()
API_KEY = os.getenv("GEMINI_API_KEY")

def test_gemini_connection():
    print("🔍 Testando conexão com Google Gemini API...")

    if not API_KEY:
        print("❌ ERRO: GEMINI_API_KEY não encontrada no arquivo .env!")
        return False

    print(f"✅ API Key encontrada: {API_KEY[:5]}...{API_KEY[-4:]}")

    # 2. Configuração da URL (Usando o modelo gemini-1.5-flash)
    # Se quiser usar o pro, mude para 'gemini-pro'
    # 3. Cabeçalhos
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={API_KEY}"
    headers = {
        "Content-Type": "application/json"
    }

    # 4. O Corpo da requisição (Payload) DEVE seguir esta estrutura exata
    payload = {
        "contents": [{
            "parts": [{
                "text": "Olá! Responda com apenas uma frase: O sistema está funcionando?"
            }]
        }]
    }

    try:
        print("🌐 Enviando requisição...")
        response = requests.post(url, headers=headers, data=json.dumps(payload))
        
        # Verifica se deu erro (400, 401, 500, etc)
        if response.status_code == 200:
            print("✅ Conexão bem-sucedida! (Status 200)")
            
            result = response.json()
            # Navegação segura pelo JSON para pegar a resposta
            try:
                text = result['candidates'][0]['content']['parts'][0]['text']
                print(f"🤖 Resposta da IA: '{text.strip()}'")
                print("\n🚀 Tudo pronto! Sua integração está funcionando.")
                return True
            except (KeyError, IndexError):
                print("⚠️ Resposta recebida, mas formato inesperado:")
                print(result)
                return False
        else:
            print(f"❌ ERRO: Status {response.status_code}")
            print("Detalhes do erro:", response.text)
            return False

    except Exception as e:
        print(f"❌ ERRO de Execução: {e}")
        return False

if __name__ == "__main__":
    test_gemini_connection()