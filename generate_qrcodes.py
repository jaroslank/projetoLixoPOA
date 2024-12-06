# generate_qrcodes.py

import os
import qrcode
from supabase import create_client, Client
from dotenv import load_dotenv
from pathlib import Path

load_dotenv()

# Configuração do Supabase
SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_KEY')

if not SUPABASE_URL or not SUPABASE_KEY:
    print("Por favor, defina SUPABASE_URL e SUPABASE_KEY no arquivo .env")
    exit(1)

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

def generate_qr_codes():
    # Buscar todas as lixeiras
    response = supabase.table("lixeiras").select("*").execute()
    
    # Verificar se a requisição foi bem-sucedida
    if not response.data:
        print(f"Erro ao buscar lixeiras ou nenhuma lixeira encontrada: {response}")
        return

    lixeiras = response.data
    if not lixeiras:
        print("Nenhuma lixeira encontrada.")
        return

    for lixeira in lixeiras:
        lixeira_id = lixeira.get('id')
        if not lixeira_id:
            print("Lixeira sem ID encontrada. Pulando...")
            continue

        qr_data = str(lixeira_id)  # Codifica apenas o ID

        # Gerar o QR code
        qr = qrcode.QRCode(
            version=1,
            box_size=10,
            border=5
        )
        qr.add_data(qr_data)
        qr.make(fit=True)

        img = qr.make_image(fill='black', back_color='white')

        # Salvar o QR code na pasta static/qrcodes/
        qr_filename = f"lixeira_{lixeira_id}.png"
        qr_directory = Path('static') / 'qrcodes'
        qr_directory.mkdir(parents=True, exist_ok=True)
        qr_path = qr_directory / qr_filename
        img.save(qr_path)
        print(f"QR code gerado para a lixeira {lixeira_id}: {qr_path}")

if __name__ == "__main__":
    generate_qr_codes()

