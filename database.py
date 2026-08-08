import os
from dotenv import load_dotenv
from supabase import create_client, Client

# Carrega as variáveis do arquivo .env (uso local)
load_dotenv()

# Pega as chaves (variáveis de ambiente locais ou st.secrets em produção, ex: Streamlit Cloud)
url: str = os.environ.get("SUPABASE_URL")
key: str = os.environ.get("SUPABASE_KEY")

if not url or not key:
    try:
        import streamlit as st
        url = url or st.secrets.get("SUPABASE_URL")
        key = key or st.secrets.get("SUPABASE_KEY")
    except Exception:
        pass

# Inicializa o cliente do Supabase
if not url or not key:
    raise ValueError("Credenciais do Supabase não encontradas (.env ou st.secrets)")

supabase: Client = create_client(url, key)