# upload_avatar.py

import os
import time
import logging
from werkzeug.utils import secure_filename
from supabase import Client

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

def allowed_file(filename):
    """
    Verifica se a extensão do arquivo é permitida.
    """
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def upload_avatar(file, supabase: Client, bucket_name: str, user_id: int):
    """
    Faz o upload do arquivo de avatar para o Supabase Storage e retorna a URL pública.

    Args:
        file: Arquivo enviado pelo usuário.
        supabase: Cliente Supabase já autenticado.
        bucket_name: Nome do bucket no Supabase Storage.
        user_id: ID do usuário para nomear o arquivo de forma única.

    Returns:
        public_url (str): URL pública do avatar ou None se falhar.
    """
    try:
        # Assegura o nome seguro do arquivo
        filename = secure_filename(file.filename)
        logging.debug(f"Nome original do arquivo: {filename}")

        # Renomeia o arquivo para evitar conflitos, usando user_id e timestamp
        timestamp = int(time.time())
        file_extension = os.path.splitext(filename)[1]
        new_filename = f"user_{user_id}_{timestamp}{file_extension}"
        logging.debug(f"Nome novo do arquivo: {new_filename}")

        # Lê o conteúdo do arquivo como bytes
        file_content = file.read()
        logging.debug(f"Tamanho do arquivo: {len(file_content)} bytes")

        # Verificar se o arquivo está vazio
        if len(file_content) == 0:
            logging.error("Arquivo vazio enviado para upload.")
            return None

        # Faz o upload para o bucket de avatares
        response = supabase.storage.from_(bucket_name).upload(new_filename, file_content, {
            'content-type': file.content_type
        })

        # Verificar se o atributo 'path' está presente
        logging.debug(f"Upload Response Path: {response.path}")

        if not hasattr(response, 'path') or not response.path:
            logging.error("Erro no upload: caminho do arquivo não retornado.")
            return None

        # Obtém a URL pública do arquivo
        public_url = supabase.storage.from_(bucket_name).get_public_url(response.path)
        logging.debug(f"Get Public URL Response: {public_url}")

        # Verificar se public_url está presente
        if not public_url:
            logging.error("Não foi possível obter a URL pública do avatar.")
            logging.debug(f"Conteúdo de get_public_url: {public_url}")
            return None

        logging.info(f"Avatar carregado com sucesso: {public_url}")
        return public_url

    except Exception as e:
        logging.exception("Erro ao fazer upload do avatar: %s", e)
        return None  # Remover a vírgula aqui


