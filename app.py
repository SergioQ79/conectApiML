import os
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

# En Render: seteá estos manualmente después de autorizar
ACCESS_TOKEN_ENV = os.getenv("ACCESS_TOKEN")
REFRESH_TOKEN_ENV = os.getenv("REFRESH_TOKEN")

app = Flask(__name__)

# ==========================
# Funciones auxiliares
# ==========================

def renovar_token():
    """
    Intenta renovar el ACCESS_TOKEN usando el REFRESH_TOKEN
    """
    if not REFRESH_TOKEN_ENV:
        print("⚠️ REFRESH_TOKEN no definido en entorno.")
        return None

    response = requests.post(
        "https://api.mercadolibre.com/oauth/token",
        data={
            "grant_type": "refresh_token",
            "client_id": CLIENT_ID,
            "client_secret": CLIENT_SECRET,
            "refresh_token": REFRESH_TOKEN_ENV
        }
    )

    if response.status_code != 200:
        print("❌ Error al renovar el token:", response.text)
        return None

    nuevos_tokens = response.json()
    print("✅ Token renovado exitosamente.")
    return nuevos_tokens.get("access_token")


def obtener_access_token():
    """
    Devuelve un token válido. Primero intenta renovar, si falla usa el fijo de entorno.
    """
    nuevo = renovar_token()
    return nuevo or ACCESS_TOKEN_ENV


# ==========================
# Rutas
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
        return "❌ No se pudo obtener un token válido.", 401

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
# Ejecutar app localmente
# ==========================
if __name__ == '__main__':
    app.run(debug=True)
