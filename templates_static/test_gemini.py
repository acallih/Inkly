# Importações necessárias para o script de teste
import os  # Para acessar variáveis de ambiente
import requests  # Para fazer requisições HTTP à API do Gemini
import json  # Para serializar/desserializar dados JSON
from dotenv import load_dotenv  # Para carregar variáveis do arquivo .env

# 1. Carrega as variáveis do .env
# O arquivo .env deve conter a chave GEMINI_API_KEY
load_dotenv()
API_KEY = os.getenv("GEMINI_API_KEY")  # Recupera a chave da API do Gemini

def test_gemini_connection():
    """
    Função de teste para verificar a conexão com a API do Google Gemini.
    
    Esta função:
    - Verifica se a chave API está configurada
    - Faz uma requisição simples à API do Gemini
    - Valida a resposta recebida
    - Retorna True se tudo funcionar corretamente
    """
    print("🔍 Testando conexão com Google Gemini API...")

    # Verifica se a chave API foi carregada do arquivo .env
    if not API_KEY:
        print("❌ ERRO: GEMINI_API_KEY não encontrada no arquivo .env!")
        return False

    # Exibe os primeiros e últimos caracteres da chave para confirmação (sem expor a chave completa)
    print(f"✅ API Key encontrada: {API_KEY[:5]}...{API_KEY[-4:]}")

    # 2. Configuração da URL (Usando o modelo gemini-1.5-flash)
    # Se quiser usar o pro, mude para 'gemini-pro'
    # Nota: O modelo gemini-2.5-flash é mais recente e pode oferecer melhor desempenho
    # 3. Cabeçalhos
    # A URL inclui o modelo a ser usado e a chave API como parâmetro de query
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={API_KEY}"
    
    # Headers HTTP necessários para a requisição
    headers = {
        "Content-Type": "application/json"  # Indica que estamos enviando JSON
    }

    # 4. O Corpo da requisição (Payload) DEVE seguir esta estrutura exata
    # A estrutura é específica da API do Gemini e não pode ser alterada
    payload = {
        "contents": [{  # Array de conteúdos a serem processados
            "parts": [{  # Array de partes do conteúdo
                "text": "Olá! Responda com apenas uma frase: O sistema está funcionando?"
                # Prompt simples para testar se a API responde corretamente
            }]
        }]
    }

    try:
        print("🌐 Enviando requisição...")
        # Faz a requisição POST para a API do Gemini
        response = requests.post(url, headers=headers, data=json.dumps(payload))
        
        # Verifica se deu erro (400, 401, 500, etc)
        # Status 200 indica sucesso
        if response.status_code == 200:
            print("✅ Conexão bem-sucedida! (Status 200)")
            
            # Converte a resposta JSON em dicionário Python
            result = response.json()
            
            # Navegação segura pelo JSON para pegar a resposta
            # A estrutura da resposta é: candidates[0].content.parts[0].text
            try:
                # Extrai o texto da resposta seguindo a estrutura específica da API
                text = result['candidates'][0]['content']['parts'][0]['text']
                print(f"🤖 Resposta da IA: '{text.strip()}'")  # Remove espaços em branco extras
                print("\n🚀 Tudo pronto! Sua integração está funcionando.")
                return True  # Teste passou com sucesso
                
            except (KeyError, IndexError):
                # Se a estrutura JSON for diferente do esperado
                print("⚠️ Resposta recebida, mas formato inesperado:")
                print(result)  # Exibe a resposta completa para debug
                return False  # Teste falhou
                
        else:
            # Se o status não for 200 (erro na requisição)
            print(f"❌ ERRO: Status {response.status_code}")
            print("Detalhes do erro:", response.text)  # Mostra a mensagem de erro da API
            return False

    except Exception as e:
        # Captura qualquer outro erro (rede, timeout, etc)
        print(f"❌ ERRO de Execução: {e}")
        return False

# Ponto de entrada do script
# Este bloco só executa se o arquivo for rodado diretamente (não importado)
if __name__ == "__main__":
    test_gemini_connection()  # Executa o teste de conexão
