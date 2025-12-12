"""
Script de teste para verificar conexão com Google Gemini API
"""

import os
import sys
import requests

def test_gemini_connection():
    """Testa conexão com API Gemini"""
    
    print("🔍 Testando conexão com Google Gemini API...\n")
    
    api_key = os.getenv("GEMINI_API_KEY")
    
    if not api_key:
        print("❌ ERRO: GEMINI_API_KEY não encontrada!")
        print("\n📝 Como configurar:")
        print("   Windows (CMD):      set GEMINI_API_KEY=sua_chave")
        print("   Windows (PowerShell): $env:GEMINI_API_KEY='sua_chave'")
        print("   Mac/Linux:          export GEMINI_API_KEY=sua_chave")
        print("\n🔑 Obtenha sua chave em: https://makersuite.google.com/app/apikey")
        return False
    
    print(f"✅ API Key encontrada: {api_key[:10]}...{api_key[-4:]}")
    
    print("\n🌐 Testando requisição à API...")
    
    try:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash-exp:generateContent?key={api_key}"
        
        payload = {
            "contents": [{
                "parts": [{"text": "Responda apenas: 'OK'. Não adicione mais nada."}]
            }],
            "generationConfig": {
                "temperature": 0.1,
                "maxOutputTokens": 10
            }
        }
        
        response = requests.post(url, json=payload, timeout=10)
        
        if response.status_code == 200:
            print("✅ Conexão bem-sucedida!")
            result = response.json()
            text = result.get('candidates', [{}])[0].get('content', {}).get('parts', [{}])[0].get('text', '')
            print(f"📝 Resposta da IA: '{text.strip()}'")
            print("\n🎉 Tudo funcionando! Você pode rodar o Inkly agora!")
            return True
        elif response.status_code == 400:
            print("❌ ERRO: API Key inválida!")
            print("🔑 Verifique sua chave em: https://makersuite.google.com/app/apikey")
            return False
        elif response.status_code == 429:
            print("⚠️  AVISO: Limite de requisições excedido")
            print("⏰ Aguarde alguns minutos e tente novamente")
            return False
        else:
            print(f"❌ ERRO: Status {response.status_code}")
            print(f"📄 Resposta: {response.text}")
            return False
            
    except requests.exceptions.ConnectionError:
        print("❌ ERRO: Sem conexão com internet!")
        return False
    except Exception as e:
        print(f"❌ ERRO inesperado: {e}")
        return False


if __name__ == "__main__":
    success = test_gemini_connection()
    sys.exit(0 if success else 1)