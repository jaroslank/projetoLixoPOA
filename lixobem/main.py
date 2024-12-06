from kivy import Config

# Configurar Kivy antes de qualquer outra importação
Config.set('graphics', 'multisamples', '0')
Config.set('graphics', 'width', '800')
Config.set('graphics', 'height', '600')
Config.set('graphics', 'fullscreen', '0')

from kivy.app import App
from kivy.lang import Builder
from kivy.uix.screenmanager import ScreenManager, Screen
from kivy.core.window import Window
from kivy.clock import Clock
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.image import Image
from kivymd.app import MDApp
from kivymd.uix.button import MDRaisedButton
from kivy.utils import platform

# Permissões Android
from android.permissions import request_permissions, Permission
request_permissions([Permission.CAMERA, Permission.INTERNET])

import requests
import sqlite3
from datetime import datetime

# Importação do ZBarCam para leitura de QR Codes
from kivy_garden.zbarcam import ZBarCam

Window.clearcolor = (0.1, 0.1, 0.1, 1)

conn = sqlite3.connect('local_data.db')
c = conn.cursor()

c.execute('''
    CREATE TABLE IF NOT EXISTS coletas (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        lixeira_id INTEGER,
        tipo_lixo TEXT,
        data_coleta TEXT,
        sincronizado INTEGER DEFAULT 0
    )
''')
conn.commit()

def is_connected(url='https://www.google.com/', timeout=5):
    try:
        _ = requests.get(url, timeout=timeout)
        return True
    except requests.ConnectionError:
        return False

def save_coleta_local(lixeira_id, tipo_lixo):
    data_coleta = datetime.utcnow().isoformat()
    c.execute('INSERT INTO coletas (lixeira_id, tipo_lixo, data_coleta) VALUES (?, ?, ?)',
              (lixeira_id, tipo_lixo, data_coleta))
    conn.commit()
    print("Coleta salva localmente.")

def sync_coletas():
    c.execute('SELECT * FROM coletas WHERE sincronizado = 0')
    coletas = c.fetchall()
    for coleta in coletas:
        _, lixeira_id, tipo_lixo, data_coleta, _ = coleta
        payload = {
            'lixeira_id': lixeira_id,
            'tipo_lixo': tipo_lixo,
            'data_coleta': data_coleta
        }
        try:
            response = requests.post('https://198b-2804-389-f280-39c8-2ba-adcd-396f-25ab.ngrok-free.app/api/registrar_coleta', json=payload)
            if response.status_code == 201:
                c.execute('UPDATE coletas SET sincronizado = 1 WHERE id = ?', (coleta[0],))
                conn.commit()
                print(f"Coleta {coleta[0]} sincronizada com sucesso.")
            else:
                print(f"Falha ao sincronizar coleta {coleta[0]}. Status Code: {response.status_code}")
        except requests.exceptions.RequestException as e:
            print(f"Erro ao sincronizar coleta {coleta[0]}: {e}")

class QRCodeScreen(Screen):
    def __init__(self, **kwargs):
        super(QRCodeScreen, self).__init__(**kwargs)
        layout = BoxLayout(orientation='vertical')

        self.zbarcam = ZBarCam(size_hint=(1, 0.9))
        layout.add_widget(self.zbarcam)

        self.info_label = Label(
            text="Aponte a câmera para o QR Code da lixeira",
            size_hint=(1, 0.1),
            color=(1, 1, 1, 1),
            halign='center',
            valign='middle'
        )
        self.info_label.bind(size=self.info_label.setter('text_size'))
        layout.add_widget(self.info_label)

        # Quando símbolos (QR Codes) são detectados
        self.zbarcam.bind(symbols=self.on_symbols)

        self.add_widget(layout)

    def on_symbols(self, instance, symbols):
        if symbols:
            # Pega o primeiro QR code
            qr_data = symbols[0].data.decode("utf-8")
            self.info_label.text = f"QR Code Detectado: {qr_data}"

            # Aqui você pode usar o qr_data para registrar a coleta
            # Por exemplo, se o qr_data representar o ID da lixeira:
            # Exemplo: lixeira_id = int(qr_data) se o QR code for só um número
            # Aqui estamos assumindo que o QR code contém o ID da lixeira
            try:
                lixeira_id = int(qr_data)
                # Salvamos a coleta localmente com tipo_lixo por ex: "papel"
                save_coleta_local(lixeira_id, "papel")

                # Tenta sincronizar se online
                if is_connected():
                    sync_coletas()

                # Volta pra tela principal depois de registrar
                self.manager.current = 'main'
            except ValueError:
                self.info_label.text = "QR Code inválido"
                # Aguarda alguns segundos e volta
                Clock.schedule_once(lambda dt: setattr(self.manager, 'current', 'main'), 2)

class MainScreen(Screen):
    def __init__(self, **kwargs):
        super(MainScreen, self).__init__(**kwargs)
        self.layout = BoxLayout(orientation='vertical')

        self.bg = Image(
            source='static/background.jpg',
            allow_stretch=True,
            keep_ratio=False,
            size_hint=(1, 1),
            pos_hint={'x': 0, 'y': 0}
        )
        self.layout.add_widget(self.bg)

        phrases_layout = BoxLayout(
            orientation='vertical',
            size_hint=(1, 0.4),
            spacing=10,
            padding=(20, 50, 20, 20)
        )
        phrases = [
            "Conservar, Preservar, Reutilizar, Reciclar e Repetir.",
            "Pequenas ações criam grandes mudanças.",
            "O planeta depende de você. Cuide dele!",
        ]
        for phrase in phrases:
            label = Label(
                text=phrase,
                size_hint=(1, None),
                height=50,
                color=(0.0, 1.0, 1.0, 1),
                font_size='18sp',
                halign='center',
                valign='middle'
            )
            label.bind(size=label.setter('text_size'))
            phrases_layout.add_widget(label)
        self.layout.add_widget(phrases_layout)

        buttons_layout = BoxLayout(
            orientation='vertical',
            spacing=20,
            size_hint=(0.4, 0.4),
            padding=(20, 20, 20, 20),
            pos_hint={'center_x': 0.5, 'y': 0.05}
        )

        button_bg_color = (0.2, 0.2, 0.2, 1)
        button_text_color = (0.0, 1.0, 1.0, 1)
        button_font_size = '20sp'

        def create_button(text, action):
            btn = MDRaisedButton(
                text=text,
                size_hint=(1, None),
                height=60,
                md_bg_color=button_bg_color,
                text_color=button_text_color,
                font_size=button_font_size
            )
            btn.bind(on_release=action)
            return btn

        def open_login(instance):
            if is_connected():
                import webbrowser
                webbrowser.open("https://198b-2804-389-f280-39c8-2ba-adcd-396f-25ab.ngrok-free.app/login")
            else:
                self.manager.current = 'offline_login'

        def open_register(instance):
            if is_connected():
                import webbrowser
                webbrowser.open("https://198b-2804-389-f280-39c8-2ba-adcd-396f-25ab.ngrok-free.app/cadastrar")
            else:
                self.manager.current = 'offline_register'

        def open_home(instance):
            if is_connected():
                import webbrowser
                webbrowser.open("https://198b-2804-389-f280-39c8-2ba-adcd-396f-25ab.ngrok-free.app/principal")
            else:
                self.manager.current = 'offline_home'

        def open_qrcode(instance):
            # Vai para a tela de QRCode para registrar a coleta
            self.manager.current = 'qrcode'

        btn_login = create_button("Login", open_login)
        btn_register = create_button("Cadastrar", open_register)
        btn_home = create_button("Inicial", open_home)
        btn_qrcode = create_button("Registrar Coleta", open_qrcode)

        buttons_layout.add_widget(btn_login)
        buttons_layout.add_widget(btn_register)
        buttons_layout.add_widget(btn_home)
        buttons_layout.add_widget(btn_qrcode)

        self.layout.add_widget(buttons_layout)

        self.status_label = Label(
            text='Verificando conexão...',
            size_hint=(1, None),
            height=30,
            color=(1, 1, 1, 1),
            font_size='14sp',
            halign='center',
            valign='middle'
        )
        self.status_label.bind(size=self.status_label.setter('text_size'))
        self.layout.add_widget(self.status_label)

        self.add_widget(self.layout)

        Clock.schedule_interval(self.check_connection, 30)
        self.check_connection(0)

    def check_connection(self, dt):
        if is_connected():
            self.status_label.text = 'Conectado'
            sync_coletas()
        else:
            self.status_label.text = 'Offline'

class OfflineLoginScreen(Screen):
    def __init__(self, **kwargs):
        super(OfflineLoginScreen, self).__init__(**kwargs)
        layout = BoxLayout(orientation='vertical', padding=20, spacing=20)
        lbl = Label(
            text='Modo Offline: Login não disponível.',
            size_hint=(1, 0.8),
            color=(1, 0, 0, 1),
            font_size='20sp',
            halign='center',
            valign='middle'
        )
        lbl.bind(size=lbl.setter('text_size'))
        layout.add_widget(lbl)

        btn_back = MDRaisedButton(
            text="Voltar",
            size_hint=(0.3, 0.1),
            pos_hint={'center_x': 0.5},
            md_bg_color=(0.2, 0.2, 0.2, 1),
            text_color=(0.0, 1.0, 1.0, 1),
            font_size='16sp'
        )
        btn_back.bind(on_release=self.go_back)
        layout.add_widget(btn_back)

        self.add_widget(layout)

    def go_back(self, instance):
        self.manager.current = 'main'

class OfflineRegisterScreen(Screen):
    def __init__(self, **kwargs):
        super(OfflineRegisterScreen, self).__init__(**kwargs)
        layout = BoxLayout(orientation='vertical', padding=20, spacing=20)
        lbl = Label(
            text='Modo Offline: Cadastro não disponível.',
            size_hint=(1, 0.8),
            color=(1, 0, 0, 1),
            font_size='20sp',
            halign='center',
            valign='middle'
        )
        lbl.bind(size=lbl.setter('text_size'))
        layout.add_widget(lbl)

        btn_back = MDRaisedButton(
            text="Voltar",
            size_hint=(0.3, 0.1),
            pos_hint={'center_x': 0.5},
            md_bg_color=(0.2, 0.2, 0.2, 1),
            text_color=(0.0, 1.0, 1.0, 1),
            font_size='16sp'
        )
        btn_back.bind(on_release=self.go_back)
        layout.add_widget(btn_back)

        self.add_widget(layout)

    def go_back(self, instance):
        self.manager.current = 'main'

class OfflineHomeScreen(Screen):
    def __init__(self, **kwargs):
        super(OfflineHomeScreen, self).__init__(**kwargs)
        layout = BoxLayout(orientation='vertical', padding=20, spacing=20)
        lbl = Label(
            text='Modo Offline: Inicial não disponível.',
            size_hint=(1, 0.8),
            color=(1, 0, 0, 1),
            font_size='20sp',
            halign='center',
            valign='middle'
        )
        lbl.bind(size=lbl.setter('text_size'))
        layout.add_widget(lbl)

        btn_back = MDRaisedButton(
            text="Voltar",
            size_hint=(0.3, 0.1),
            pos_hint={'center_x': 0.5},
            md_bg_color=(0.2, 0.2, 0.2, 1),
            text_color=(0.0, 1.0, 1.0, 1),
            font_size='16sp'
        )
        btn_back.bind(on_release=self.go_back)
        layout.add_widget(btn_back)

        self.add_widget(layout)

    def go_back(self, instance):
        self.manager.current = 'main'

class DescarteCertoApp(MDApp):
    def build(self):
        self.theme_cls.theme_style = "Dark"
        self.theme_cls.primary_palette = "Blue"

        sm = ScreenManager()
        sm.add_widget(MainScreen(name='main'))
        sm.add_widget(OfflineLoginScreen(name='offline_login'))
        sm.add_widget(OfflineRegisterScreen(name='offline_register'))
        sm.add_widget(OfflineHomeScreen(name='offline_home'))
        sm.add_widget(QRCodeScreen(name='qrcode'))
        return sm

if __name__ == '__main__':
    DescarteCertoApp().run()

