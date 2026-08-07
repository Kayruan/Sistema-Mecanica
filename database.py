import os
from dotenv import load_dotenv
from supabase import create_client, Client

# Carrega as variáveis do arquivo .env
load_dotenv()

# Pega as chaves
url: str = os.environ.get("SUPABASE_URL")
key: str = os.environ.get("SUPABASE_KEY")

# Inicializa o cliente do Supabase
if not url or not key:
    raise ValueError("Credenciais do Supabase não encontradas no arquivo .env")

supabase: Client = create_client(url, key)