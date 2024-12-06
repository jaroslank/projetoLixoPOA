# app.py

import os
import logging
from flask import Flask, render_template, request, redirect, url_for, session, flash
from supabase import create_client, Client
import bcrypt
from dotenv import load_dotenv
from werkzeug.utils import secure_filename
from upload_avatar import upload_avatar  # Importa a função de upload_avatar
from datetime import datetime, timedelta, timezone
from flask import jsonify
# ---------------------------------------------------
# 1. Carregar Variáveis de Ambiente
# ---------------------------------------------------

# Carrega variáveis de ambiente do arquivo .env
load_dotenv()

# ---------------------------------------------------
# 2. Configurar Logging
# ---------------------------------------------------

# Configura o sistema de logging para registrar eventos e erros
logging.basicConfig(
    level=logging.DEBUG,  # Nível de logging (DEBUG para detalhes completos)
    format='%(asctime)s %(levelname)s %(name)s %(threadName)s : %(message)s',
    handlers=[
        logging.FileHandler("app.log"),  # Registra logs em um arquivo chamado app.log
        logging.StreamHandler()           # Exibe logs no console
    ]
)

# ---------------------------------------------------
# 3. Inicializar o Aplicativo Flask
# ---------------------------------------------------

app = Flask(__name__)

# Define a chave secreta para sessões Flask. Deve ser mantida em segredo!
app.secret_key = os.getenv('FLASK_SECRET_KEY') or 'your_default_secret_key'  # Substitua 'your_default_secret_key' por uma chave forte em produção

# ---------------------------------------------------
# 4. Configuração do Supabase
# ---------------------------------------------------

# Obtém as URLs e chaves do Supabase a partir das variáveis de ambiente
SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_KEY')

# Verifica se as variáveis de ambiente estão definidas
if not SUPABASE_URL or not SUPABASE_KEY:
    logging.error("SUPABASE_URL e SUPABASE_KEY devem estar definidas no arquivo .env.")
    exit(1)  # Encerra a aplicação se as configurações não estiverem presentes

# Cria o cliente Supabase para interagir com o banco de dados
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# Nome do bucket no Supabase para armazenar avatares
AVATAR_BUCKET = 'avatars'

# ---------------------------------------------------
# 5. Funções Auxiliares
# ---------------------------------------------------

def allowed_file(filename):
    """
    Verifica se o arquivo possui uma extensão permitida.
    """
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def cadastrar_usuario(nome, cpf, email, senha, perfil):
    """
    Cadastra um novo usuário no banco de dados Supabase.
    """
    try:
        # Verifica se o email já está cadastrado
        existing_user = supabase.table("usuarios").select("*").eq("email", email).execute()
        if existing_user.data:
            return False, "Email já está cadastrado."

        # Gera o hash da senha para segurança
        hashed_senha = bcrypt.hashpw(senha.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

        # Insere o novo usuário no banco de dados
        response = supabase.table("usuarios").insert({
            "nome": nome,
            "cpf": cpf,
            "email": email,
            "senha": hashed_senha,
            "perfil": perfil
        }).execute()

        # Verifica se a inserção foi bem-sucedida
        error = getattr(response, 'error', None)
        if error:
            error_message = error.message if hasattr(error, 'message') else 'Erro desconhecido.'
            logging.error(f"Erro ao cadastrar usuário: {error_message}")
            return False, f"Erro ao cadastrar usuário: {error_message}"
        elif not response.data:
            # Caso a inserção não retorne dados esperados
            error_message = "Nenhum dado retornado após a inserção."
            logging.error(f"Erro ao cadastrar usuário: {error_message}")
            return False, f"Erro ao cadastrar usuário: {error_message}"
        else:
            logging.debug(f"Usuário cadastrado com sucesso: {response.data}")
            return True, "Cadastro realizado com sucesso."

    except Exception as e:
        logging.exception(f"Erro ao cadastrar usuário: {e}")
        return False, f"Erro ao cadastrar usuário: {str(e)}"

def obter_coletas_por_mes(usuario_id=None):
    """
    Coleta o número de coletas por mês para um usuário específico ou para todos os usuários.
    Retorna duas listas: meses_traduzidos_lista e coletas_counts.
    """
    try:
        query = supabase.table("coletas").select("data_coleta")
        if usuario_id:
            query = query.eq("usuario_id", usuario_id)
        response_coletas = query.execute()
        
        coletas_por_mes = {}
        for coleta in response_coletas.data:
            data_coleta_str = coleta.get('data_coleta')
            if not data_coleta_str:
                continue  # Pula se não houver data_coleta
            
            try:
                # Converte a string de data para objeto datetime
                # Ajusta para remover 'Z' se presente e define o timezone como UTC
                if data_coleta_str.endswith('Z'):
                    data_coleta = datetime.fromisoformat(data_coleta_str.rstrip('Z')).replace(tzinfo=timezone.utc)
                else:
                    data_coleta = datetime.fromisoformat(data_coleta_str)
            except ValueError as ve:
                logging.error(f"Formato de data inválido: {data_coleta_str} - Erro: {ve}")
                continue  # Pula entradas com data inválida
            
            mes = data_coleta.strftime("%B %Y")  # Formato: "November 2024"
            coletas_por_mes[mes] = coletas_por_mes.get(mes, 0) + 1

        # Ordena os meses de forma cronológica
        meses_ordenados = sorted(coletas_por_mes.keys(), key=lambda x: datetime.strptime(x, "%B %Y"))
        coletas_counts = [coletas_por_mes[mes] for mes in meses_ordenados]

        # Tradução dos meses para português
        meses_traduzidos = {
            'January': 'Janeiro',
            'February': 'Fevereiro',
            'March': 'Março',
            'April': 'Abril',
            'May': 'Maio',
            'June': 'Junho',
            'July': 'Julho',
            'August': 'Agosto',
            'September': 'Setembro',
            'October': 'Outubro',
            'November': 'Novembro',
            'December': 'Dezembro'
        }
        meses_traduzidos_lista = [meses_traduzidos.get(mes.split()[0], mes) for mes in meses_ordenados]

        logging.debug(f"Meses coletados: {meses_traduzidos_lista}")
        logging.debug(f"Coletas Counts: {coletas_counts}")

        return meses_traduzidos_lista, coletas_counts
    except Exception as e:
        logging.exception("Erro ao buscar coletas por mês: %s", e)
        return [], []

def obter_lixeiras():
    """
    Obtém todas as lixeiras com suas localizações e endereços.
    Retorna uma lista de dicionários com 'id', 'localizacao', 'endereco', e 'horario'.
    """
    try:
        response = supabase.table("lixeiras").select("id, localizacao, endereco, horario").execute()
        logging.debug(f"Status Code da Resposta: {getattr(response, 'status_code', 'N/A')}")
        logging.debug(f"Erro da Resposta: {getattr(response, 'error', None)}")
        logging.debug(f"Dados da Resposta: {response.data}")

        if response.status_code >= 400:
            error_message = response.json().get('message', 'Erro desconhecido.')
            logging.error(f"Erro ao obter lixeiras: {error_message}")
            return []
        if not response.data:
            logging.error("Nenhum dado retornado ao obter lixeiras.")
            return []
        return response.data
    except Exception as e:
        logging.exception(f"Erro ao obter lixeiras: {e}")
        return []

def obter_top_regioes(limit=5):
    """
    Obtém as regiões com mais coletas.
    Retorna uma lista de dicionários com 'regiao' e 'coletas'.
    """
    try:
        response = supabase.rpc("top_regioes", {"limit_num": limit}).execute()
        if response.error:
            logging.error(f"Erro ao obter top regiões: {response.error.message}")
            return []
        return response.data
    except Exception as e:
        logging.exception(f"Erro ao obter top regiões: {e}")
        return []

# ---------------------------------------------------
# 6. Rotas do Flask
# ---------------------------------------------------

@app.route('/api/registrar_coleta', methods=['POST'])
def api_registrar_coleta():
    data = request.get_json()
    if not data:
        return jsonify({"message": "No input data provided"}), 400

    lixeira_id = data.get('lixeira_id')
    tipo_lixo = data.get('tipo_lixo')
    data_coleta = data.get('data_coleta')

    if not all([lixeira_id, tipo_lixo, data_coleta]):
        return jsonify({"message": "Missing fields"}), 400

    try:
        # Insere a coleta no banco de dados
        response = supabase.table("coletas").insert({
            "lixeira_id": lixeira_id,
            "usuario_id": None,  # Se a coleta não está associada a um usuário, defina como None ou ajuste conforme necessário
            "tipo_lixo": tipo_lixo,
            "data_coleta": data_coleta
        }).execute()

        if response.error:
            return jsonify({"message": response.error.message}), 500

        return jsonify({"message": "Coleta registrada com sucesso."}), 201

    except Exception as e:
        logging.exception(f"Erro ao registrar coleta via API: {e}")
        return jsonify({"message": "Internal server error"}), 500

@app.route('/api/minhas_coletas', methods=['GET'])
def api_minhas_coletas():
    if 'user_id' not in session:
        return jsonify({"message": "Não autorizado"}), 401
    
    # Buscar coletas do usuário
    response = supabase.table("coletas").select("id, lixeira_id, tipo_lixo, data_coleta").eq("usuario_id", session['user_id']).order("data_coleta", desc=True).execute()
    coletas = response.data
    return jsonify(coletas), 200


@app.route('/')
def index():
    """
    Rota raiz que redireciona para a página principal.
    """
    return redirect(url_for('principal'))

@app.route('/principal')
def principal():
    """
    Página principal que exibe estatísticas de coletas e uma lista de lixeiras.
    """
    current_year = datetime.now().year
    if 'user_id' in session:
        user_id = session['user_id']
        meses, coletas_counts = obter_coletas_por_mes(usuario_id=user_id)
    else:
        meses, coletas_counts = obter_coletas_por_mes()
    
    lixeiras = obter_lixeiras()  # Obtém as lixeiras com localização e endereço
    top_regioes = obter_top_regioes()  # Obtém as top regiões com mais coletas
    
    logging.debug(f"Passando para o template - Meses: {meses}, Coletas_counts: {coletas_counts}, Lixeiras: {lixeiras}, Top Regiões: {top_regioes}")
    
    return render_template(
        'principal.html',
        current_year=current_year,
        meses=meses,
        coletas_counts=coletas_counts,
        lixeiras=lixeiras,
        top_regioes=top_regioes
    )

@app.route('/cadastrar', methods=['GET', 'POST'])
def cadastrar():
    """
    Rota para cadastro de novos usuários.
    """
    if request.method == 'POST':
        nome = request.form.get('nome')
        cpf = request.form.get('cpf')
        email = request.form.get('email')
        senha = request.form.get('senha')
        perfil = request.form.get('perfil') or "cidadão"

        sucesso, mensagem = cadastrar_usuario(nome, cpf, email, senha, perfil)

        if sucesso:
            flash(mensagem, "success")
            return redirect(url_for('login'))
        else:
            flash(mensagem, "danger")

    current_year = datetime.now().year
    return render_template('cadastrar.html', current_year=current_year)

@app.route('/login', methods=['GET', 'POST'])
def login():
    """
    Rota para login de usuários.
    """
    if request.method == 'POST':
        email = request.form.get('email')
        senha = request.form.get('senha')

        try:
            # Busca usuário pelo email
            response = supabase.table("usuarios").select("*").eq("email", email).execute()
            logging.debug(f"Login Response: {response}")
            logging.debug(f"Login Response Data: {response.data}")

            if not response.data:
                logging.warning(f"Nenhum usuário encontrado com o email: {email}")
                mensagem = "Email ou senha inválidos."
                flash(mensagem, "danger")
            else:
                usuario = response.data[0]
                hashed_senha = usuario.get('senha')

                # Verifica a senha
                if bcrypt.checkpw(senha.encode('utf-8'), hashed_senha.encode('utf-8')):
                    # Senha correta, inicia sessão
                    session['user_id'] = usuario.get('id')
                    session['nome'] = usuario.get('nome')
                    session['email'] = usuario.get('email')
                    session['perfil'] = usuario.get('perfil')
                    session['avatar_url'] = usuario.get('avatar_url')  # Adicionado
                    logging.info(f"Usuário {email} autenticado com sucesso.")
                    flash("Login realizado com sucesso!", "success")
                    return redirect(url_for('dashboard'))
                else:
                    logging.warning(f"Senha incorreta para o email: {email}")
                    mensagem = "Email ou senha inválidos."
                    flash(mensagem, "danger")

        except Exception as e:
            logging.exception(f"Ocorreu um erro durante o login: {e}")
            mensagem = "Ocorreu um erro durante o login. Tente novamente mais tarde."
            flash(mensagem, "danger")

    current_year = datetime.now().year
    return render_template('login.html', current_year=current_year)

@app.route('/dashboard')
def dashboard():
    """
    Rota para o dashboard do usuário, exibindo estatísticas e informações.
    """
    if 'user_id' not in session:
        return redirect(url_for('login'))

    nome = session.get('nome')
    email = session.get('email')
    avatar_url = session.get('avatar_url')
    user_id = session.get('user_id')
    logging.debug(f"ID do Usuário na Sessão: {user_id}")
    logging.debug(f"Avatar URL na Sessão: {avatar_url}")

    try:
        # Buscar total de coletas
        response_coletas = supabase.table("coletas").select("id, data_coleta").eq("usuario_id", user_id).execute()
        total_coletas = len(response_coletas.data) if response_coletas.data else 0
        logging.debug(f"Total de coletas: {total_coletas}")

        # Buscar pontuação total
        response_pontuacao = supabase.table("pontuacao").select("pontos").eq("usuario_id", user_id).execute()
        pontuacao_total = sum([p['pontos'] for p in response_pontuacao.data]) if response_pontuacao.data else 0
        logging.debug(f"Pontuação total: {pontuacao_total}")

        # Buscar metas alcançadas (exemplo: metas com objetivo <= pontuacao_total)
        response_metas = supabase.table("metas").select("id").lte("objetivo", pontuacao_total).execute()
        metas_alcancadas = len(response_metas.data) if response_metas.data else 0
        logging.debug(f"Metas alcançadas: {metas_alcancadas}")

        # Buscar coletas recentes
        response_recents = supabase.table("coletas").select("id, lixeira_id, tipo_lixo, data_coleta, lixeiras(localizacao, tipos_lixo(tipo))") \
                            .eq("usuario_id", user_id).order("data_coleta", desc=True).limit(5).execute()
        coletas_recents = response_recents.data
        logging.debug(f"Coletas recentes: {coletas_recents}")

        # Preparando dados para o gráfico
        meses, coletas_counts = obter_coletas_por_mes(usuario_id=user_id)

    except Exception as e:
        logging.exception("Erro ao buscar estatísticas: %s", e)
        total_coletas = 0
        pontuacao_total = 0
        metas_alcancadas = 0
        coletas_recents = []
        meses = []
        coletas_counts = []

    # Definindo current_time para evitar cache do navegador
    current_time = int(datetime.now().timestamp())

    return render_template(
        'dashboard.html',
        nome=nome,
        email=email,
        avatar_url=avatar_url,
        total_coletas=total_coletas,
        pontuacao_total=pontuacao_total,
        metas_alcancadas=metas_alcancadas,
        coletas_recents=coletas_recents,
        time=current_time,
        meses=meses,
        coletas_counts=coletas_counts
    )

@app.route('/update_profile', methods=['POST'])
def update_profile():
    """
    Rota para atualizar o perfil do usuário, incluindo o avatar.
    """
    if 'user_id' not in session:
        return redirect(url_for('login'))

    nome = request.form.get('nome')
    file = request.files.get('avatar')

    avatar_url = None
    if file and file.filename != '':
        if allowed_file(file.filename):
            # Usa a função importada upload_avatar
            avatar_url = upload_avatar(file, supabase, AVATAR_BUCKET, session['user_id'])
            if not avatar_url:
                flash('Erro ao fazer upload do avatar.', 'danger')
                return redirect(url_for('dashboard'))
        else:
            flash('Tipo de arquivo inválido. Apenas imagens são permitidas.', 'danger')
            return redirect(url_for('dashboard'))

    try:
        # Atualiza o nome e o avatar_url no banco de dados
        data = {'nome': nome}
        if avatar_url:
            data['avatar_url'] = avatar_url

        response = supabase.table("usuarios").update(data).eq("id", session['user_id']).execute()

        # Verifica se a atualização foi bem-sucedida
        error = getattr(response, 'error', None)
        if error:
            error_message = error.message if hasattr(error, 'message') else 'Erro desconhecido.'
            logging.error(f"Erro ao atualizar perfil: {error_message}")
            flash(f'Erro ao atualizar perfil: {error_message}', 'danger')
            return redirect(url_for('dashboard'))
        elif not response.data:
            # Caso a atualização não retorne dados esperados
            error_message = "Nenhum dado retornado após a atualização."
            logging.error(f"Erro ao atualizar perfil: {error_message}")
            flash(f'Erro ao atualizar perfil: {error_message}', 'danger')
            return redirect(url_for('dashboard'))
        else:
            logging.debug(f"Dados retornados pela atualização: {response.data}")
            flash('Perfil atualizado com sucesso!', 'success')
            session['nome'] = nome
            if avatar_url:
                session['avatar_url'] = avatar_url
                logging.debug(f"session['avatar_url'] atualizado para: {avatar_url}")
                # Adiciona log para confirmar o valor na sessão
                logging.debug(f"Valor de session['avatar_url']: {session.get('avatar_url')}")

    except Exception as e:
        logging.exception("Erro na função update_profile: %s", e)
        flash('Erro ao atualizar perfil.', 'danger')

    return redirect(url_for('dashboard'))

@app.route('/manage_lixeiras', methods=['GET', 'POST'])
def manage_lixeiras():
    """
    Rota para gerenciar lixeiras. Apenas usuários com perfil 'admin' ou 'moderador' podem acessar.
    """
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    try:
        # Verifica se o usuário tem permissão (admin ou moderador)
        perfil = session.get('perfil')
        if perfil not in ['admin', 'moderador']:
            flash('Você não tem permissão para acessar esta página.', 'warning')
            return redirect(url_for('dashboard'))
        
        # Busca lixeiras e seus tipos de lixo
        response = supabase.table("lixeiras").select("id, tipos_lixo(tipo), localizacao").execute()
        lixeiras = response.data
        logging.debug(f"Lixeiras: {lixeiras}")
        
        current_year = datetime.now().year
        return render_template('manage_lixeiras.html', lixeiras=lixeiras, current_year=current_year)
    except Exception as e:
        logging.exception("Erro ao buscar lixeiras: %s", e)
        flash("Erro ao buscar lixeiras.", "danger")
        return redirect(url_for('dashboard'))

@app.route('/registrar_coleta', methods=['GET', 'POST'])
def registrar_coleta():
    """
    Rota para registrar uma nova coleta de lixo.
    """
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    if request.method == 'POST':
        lixeira_id = request.form.get('lixeira_id')
        tipo_lixo = request.form.get('tipo_lixo')  # Campo tipo_lixo no formulário
        logging.debug(f"Recebido lixeira_id: {lixeira_id}, tipo_lixo: {tipo_lixo}")
        
        if not lixeira_id or not tipo_lixo:
            flash("Por favor, selecione uma lixeira e o tipo de lixo.", "warning")
            return redirect(url_for('registrar_coleta'))
        
        try:
            # Converte lixeira_id para inteiro
            try:
                lixeira_id = int(lixeira_id)
                logging.debug(f"lixeira_id convertido para int: {lixeira_id}")
            except ValueError:
                logging.error(f"lixeira_id inválido: {lixeira_id}")
                flash("ID da lixeira inválido.", "danger")
                return redirect(url_for('registrar_coleta'))
            
            # Verifica se a lixeira existe
            lixeira_exists = supabase.table("lixeiras").select("id").eq("id", lixeira_id).execute()
            if not lixeira_exists.data:
                logging.error(f"Lixeira com ID {lixeira_id} não existe.")
                flash("Lixeira selecionada não existe.", "danger")
                return redirect(url_for('registrar_coleta'))
            
            # Preparar data_coleta
            data_coleta = datetime.utcnow().replace(tzinfo=timezone.utc).isoformat()
            logging.debug(f"Data da Coleta: {data_coleta}")
            
            # Inserir a coleta no Supabase
            response = supabase.table("coletas").insert({
                "lixeira_id": lixeira_id,
                "usuario_id": session['user_id'],
                "tipo_lixo": tipo_lixo,
                "data_coleta": data_coleta
            }).execute()
            
            # Logs de depuração para inspecionar a resposta
            logging.debug(f"Resposta Completa da Supabase: {response}")
            logging.debug(f"Status Code: {getattr(response, 'status_code', 'N/A')}")
            logging.debug(f"Dados da Resposta: {response.data}")

            # Verificar se a inserção foi bem-sucedida
            error = getattr(response, 'error', None)
            if error:
                error_message = error.message if hasattr(error, 'message') else 'Erro desconhecido.'
                logging.error(f"Erro ao registrar coleta: {error_message}")
                # Verificar se a exceção é relacionada à trigger
                if 'Limite de uma coleta diária para este tipo de lixo atingido' in error_message:
                    flash("Você já atingiu o limite de uma coleta diária para este tipo de lixo nesta lixeira.", "danger")
                else:
                    flash(f"Erro ao registrar coleta: {error_message}", "danger")
                return redirect(url_for('registrar_coleta'))
            elif not response.data:
                # Caso a inserção não retorne dados esperados
                error_message = "Nenhum dado retornado após a inserção."
                logging.error(f"Erro ao registrar coleta: {error_message}")
                flash(f"Erro ao registrar coleta: {error_message}", "danger")
                return redirect(url_for('registrar_coleta'))
            else:
                logging.debug(f"Registro de coleta bem-sucedido: {response.data}")
                flash("Coleta registrada com sucesso!", "success")
                return redirect(url_for('dashboard'))
            
        except Exception as e:
            logging.exception(f"Erro ao registrar coleta: {e}")
            # Verificar se a exceção é relacionada à trigger
            if 'Limite de uma coleta diária para este tipo de lixo atingido' in str(e):
                flash("Você já atingiu o limite de uma coleta diária para este tipo de lixo nesta lixeira.", "danger")
            else:
                flash("Erro ao registrar coleta.", "danger")
            return redirect(url_for('registrar_coleta'))
    
    try:
        # Busca lixeiras para seleção
        response = supabase.table("lixeiras").select("id, tipos_lixo(tipo), localizacao").execute()
        lixeiras = response.data
        logging.debug(f"Lixeiras disponíveis para coleta: {lixeiras}")
        current_year = datetime.now().year
        return render_template('registrar_coleta.html', lixeiras=lixeiras, current_year=current_year)
    except Exception as e:
        logging.exception(f"Erro ao buscar lixeiras: {e}")
        flash("Erro ao buscar lixeiras.", "danger")
        return redirect(url_for('dashboard'))
        
@app.route('/ver_pontuacao')
def ver_pontuacao():
    """
    Rota para visualizar as pontuações do usuário.
    """
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    try:
        # Busca pontuações do usuário
        response = supabase.table("pontuacao").select("*").eq("usuario_id", session['user_id']).order("data_pontuacao", desc=True).execute()
        pontuacoes = response.data
        logging.debug(f"Pontuações: {pontuacoes}")
        current_year = datetime.now().year
        return render_template('ver_pontuacao.html', pontuacoes=pontuacoes, current_year=current_year)
    except Exception as e:
        logging.exception("Erro ao buscar pontuações: %s", e)
        flash("Erro ao buscar pontuações.", "danger")
        return redirect(url_for('dashboard'))

@app.route('/minhas_coletas')
def minhas_coletas():
    """
    Rota para visualizar as coletas realizadas pelo usuário.
    """
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    try:
        # Busca coletas do usuário
        response = supabase.table("coletas").select("id, lixeira_id, tipo_lixo, data_coleta, lixeiras(localizacao, tipos_lixo(tipo))") \
                            .eq("usuario_id", session['user_id']).order("data_coleta", desc=True).limit(10).execute()
        coletas = response.data
        logging.debug(f"Minhas coletas: {coletas}")
        current_year = datetime.now().year
        return render_template('minhas_coletas.html', coletas=coletas, current_year=current_year)
    except Exception as e:
        logging.exception("Erro ao buscar coletas: %s", e)
        flash("Erro ao buscar coletas.", "danger")
        return redirect(url_for('dashboard'))

@app.route('/logout')
def logout():
    """
    Rota para deslogar o usuário.
    """
    session.clear()
    flash('Você foi deslogado com sucesso.', 'success')
    return redirect(url_for('login'))

# ---------------------------------------------------
# 7. Iniciar o Servidor Flask
# ---------------------------------------------------

if __name__ == '__main__':
    # Inicia o servidor Flask na porta 5000, acessível externamente
    app.run(host='0.0.0.0', port=5000, debug=True)

