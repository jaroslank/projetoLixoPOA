# geocode_lixeiras.py

import os
import requests
from supabase import create_client, Client
from dotenv import load_dotenv
import time
import logging
from datetime import datetime, timedelta

# Carrega as variáveis de ambiente
load_dotenv()

# Configurar logging
logging.basicConfig(level=logging.INFO)

# Configuração do Supabase
SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_KEY')

if not SUPABASE_URL or not SUPABASE_KEY:
    logging.error("SUPABASE_URL e SUPABASE_KEY devem estar definidas no arquivo .env.")
    exit(1)

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# Função de geocodificação
def geocode_address(address):
    url = "https://nominatim.openstreetmap.org/search"
    params = {
        'q': address,
        'format': 'json',
        'limit': 1
    }
    headers = {
        'User-Agent': 'LixobemApp/1.0 (prodeusimar@gmail.com)'  # Personalize com seu email
    }
    response = requests.get(url, params=params, headers=headers)
    if response.status_code == 200:
        data = response.json()
        if data:
            return float(data[0]['lat']), float(data[0]['lon'])
    return None, None

# Atualizar coordenadas das lixeiras
def atualizar_coordenadas_lixeiras():
    try:
        # Buscar todas as lixeiras sem coordenadas
        response = supabase.table("lixeiras").select("*").is_("latitude", None).is_("longitude", None).execute()
        lixeiras = response.data
        logging.info(f"Encontradas {len(lixeiras)} lixeiras sem coordenadas.")

        for lixeira in lixeiras:
            id_lixeira = lixeira['id']
            localizacao = lixeira['localizacao']
            lat, lon = geocode_address(localizacao)
            if lat and lon:
                # Atualizar a lixeira com as coordenadas
                update_response = supabase.table("lixeiras").update({
                    "latitude": lat,
                    "longitude": lon
                }).eq("id", id_lixeira).execute()
                logging.debug(f"Resposta da Atualização: {update_response}")

                # Verificar se há erro na resposta
                if hasattr(update_response, 'error') and update_response.error:
                    logging.error(f"Erro ao atualizar lixeira {id_lixeira}: {update_response.error}")
                elif hasattr(update_response, 'status_code') and update_response.status_code >= 400:
                    logging.error(f"Erro ao atualizar lixeira {id_lixeira}: Status Code {update_response.status_code}")
                    logging.error(f"Detalhes: {update_response.json()}")
                else:
                    logging.info(f"Lixeira {id_lixeira} atualizada com sucesso.")
            else:
                logging.warning(f"Não foi possível geocodificar a localização: {localizacao}")

            # Respeitar os limites de taxa da API
            time.sleep(1)  # Aguardar 1 segundo entre as requisições

    except Exception as e:
        logging.exception(f"Erro ao atualizar coordenadas das lixeiras: {e}")

if __name__ == "__main__":
    atualizar_coordenadas_lixeiras()

