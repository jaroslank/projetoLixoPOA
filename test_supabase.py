# test_supabase.py

import os
import logging
from supabase import create_client, Client
from upload_avatar import upload_avatar
from dotenv import load_dotenv

# Configurar logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

# Carregar variáveis de ambiente do arquivo .env
load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
AVATAR_BUCKET = "avatars"

if not SUPABASE_URL or not SUPABASE_KEY:
    logging.error("SUPABASE_URL e SUPABASE_KEY devem estar definidas no arquivo .env.")
    exit(1)

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

class MockFile:
    def __init__(self, filename, content, content_type):
        self.filename = filename
        self.content_type = content_type
        self.content = content

    def read(self):
        return self.content

def main():
    # Substitua pelos valores apropriados
    test_user_id = 50  # ID de um usuário existente
    test_file_path = "/home/poseidon/Documents/atual/GESTAOAGILAPP/LIXOBOM/test_avatar.png"  # Caminho para um arquivo de teste

    if not os.path.exists(test_file_path):
        logging.error(f"Arquivo de teste não encontrado: {test_file_path}")
        return

    with open(test_file_path, 'rb') as f:
        content = f.read()
        mock_file = MockFile(filename='test_avatar.png', content=content, content_type='image/png')
        avatar_url = upload_avatar(mock_file, supabase, AVATAR_BUCKET, test_user_id)
        if avatar_url:
            logging.info(f"Avatar carregado com sucesso: {avatar_url}")
        else:
            logging.error("Falha ao carregar o avatar.")

if __name__ == "__main__":
    main()

