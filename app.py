import os
import json
import requests
from flask import Flask, request, render_template
from dotenv import load_dotenv

# ==========================
# Configuración
# ==========================
load_dotenv()

CLIENT_ID = os.getenv("CLIENT_ID")
CLIENT_SECRET = os.getenv("CLIENT_SECRET")
REDIRECT_URI = os.getenv("REDIRECT_URI")
TOKEN_FILE = "tokens.json"

app = Flask(__name__)

# ==========================
# Funciones auxiliares
# ==========================

def guardar_tokens(tokens):
    with open(TOKEN_FILE, "w") as f:
        json.dump(tokens, f)

def cargar_tokens():
    if os.path.exists(TOKEN_FILE):
        with open(TOKEN_FILE, "r") as f:
            return json.load(f)
    return None

def obtener_token_desde_refresh(refresh_token):
    print("🔄 Renovando access_token con refresh_token...")
    response = requests.post(
        "https://api.mercadolibre.com/oauth/token",
        data={
            "grant_type": "refresh_token",
            "client_id": CLIENT_ID,
            "client_secret": CLIENT_SECRET,
            "refresh_token": refresh_token
        }
    )
    if response.status_code == 200:
        nuevos_tokens = response.json()
        guardar_tokens(nuevos_tokens)
        return nuevos_tokens.get("access_token")
    else:
        print("❌ Error al renovar token:", response.text)
        return None

def obtener_access_token():
    tokens = cargar_tokens()
    if tokens:
        return obtener_token_desde_refresh(tokens.get("refresh_token"))
    return None

# ==========================
# Rutas de la aplicación
# ==========================

@app.route('/')
def index():
    auth_url = (
        f"https://auth.mercadolibre.com.ar/authorization"
        f"?response_type=code"
        f"&client_id={CLIENT_ID}"
        f"&redirect_uri={REDIRECT_URI}"
    )
    return render_template("index.html", auth_url=auth_url)

@app.route("/callback")
def callback():
    code = request.args.get('code')
    if not code:
        return "❌ No se recibió código de autorización", 400

    # Obtener access_token y refresh_token
    token_response = requests.post(
        "https://api.mercadolibre.com/oauth/token",
        data={
            "grant_type": "authorization_code",
            "client_id": CLIENT_ID,
            "client_secret": CLIENT_SECRET,
            "code": code,
            "redirect_uri": REDIRECT_URI
        }
    )

    if token_response.status_code != 200:
        return f"❌ Error al obtener token:<br>{token_response.text}", 500

    tokens = token_response.json()
    access_token = tokens.get("access_token")
    refresh_token = tokens.get("refresh_token")

    # Mostramos los tokens en pantalla para copiarlos
    return f"""
    ✅ <strong>Autenticación exitosa</strong><br><br>
    🔐 <strong>ACCESS_TOKEN:</strong><br>
    <code>{access_token}</code><br><br>
    ♻️ <strong>REFRESH_TOKEN:</strong><br>
    <code>{refresh_token}</code><br><br>
    👉 Copiá estos valores y agregalos como variables de entorno en Render:<br>
    <ul>
        <li><code>ACCESS_TOKEN</code></li>
        <li><code>REFRESH_TOKEN</code></li>
    </ul>
    ⚠️ Una vez hecho eso, reiniciá la app en Render y podés ingresar normalmente a <a href='/perfil'>/perfil</a>.
    """


@app.route('/perfil')
def perfil():
    access_token = obtener_access_token()
    if not access_token:
        return "❌ No se pudo obtener token válido.", 401

    headers = {"Authorization": f"Bearer {access_token}"}

    # Obtener datos del usuario
    user_response = requests.get("https://api.mercadolibre.com/users/me", headers=headers)
    if user_response.status_code != 200:
        return f"❌ Error al obtener datos del usuario:<br>{user_response.text}", 500
    user = user_response.json()

    # Obtener publicaciones
    items_response = requests.get(f"https://api.mercadolibre.com/users/{user['id']}/items/search", headers=headers)
    items = items_response.json().get("results", []) if items_response.status_code == 200 else []

    html = f"""
    ✅ Bienvenido, <strong>{user.get('nickname')}</strong><br>
    ID de usuario: {user.get('id')}<br>
    Tipo de cuenta: {user.get('user_type')}<br><br>
    <strong>📦 Publicaciones activas:</strong><br>
    """
    if items:
        for item in items:
            html += f"- ID publicación: {item}<br>"
    else:
        html += "No tenés publicaciones activas.<br>"

    return html

# ==========================
# Ejecutar la app
# ==========================

if __name__ == '__main__':
    app.run(debug=True)

