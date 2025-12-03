import os
import requests
from flask import Flask, request, render_template
from dotenv import load_dotenv

# ==========================
# Configuración
# ==========================
load_dotenv()  # útil en local; en Render se usan las env del panel

CLIENT_ID = os.getenv("CLIENT_ID")
CLIENT_SECRET = os.getenv("CLIENT_SECRET")
REDIRECT_URI = os.getenv("REDIRECT_URI")

# Solo usamos REFRESH_TOKEN desde el entorno
REFRESH_TOKEN_ENV = os.getenv("REFRESH_TOKEN")

app = Flask(__name__)

# ==========================
# Funciones auxiliares
# ==========================

def obtener_access_token():
    """
    Genera SIEMPRE un ACCESS_TOKEN nuevo usando REFRESH_TOKEN_ENV.
    No usamos ACCESS_TOKEN fijo ni tokens.json.
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

    tokens = response.json()
    access_token = tokens.get("access_token")
    if not access_token:
        print("❌ No se obtuvo access_token en la respuesta:", tokens)
        return None

    print("✅ ACCESS_TOKEN generado correctamente desde REFRESH_TOKEN.")
    return access_token


# ==========================
# Rutas
# ==========================

@app.route('/')
def index():
    auth_url = (
        "https://auth.mercadolibre.com.ar/authorization"
        f"?response_type=code"
        f"&client_id={CLIENT_ID}"
        f"&redirect_uri={REDIRECT_URI}"
    )
    return render_template("index.html", auth_url=auth_url)


@app.route("/callback")
def callback():
    """
    Se usa SOLO para la primera autorización.
    Muestra ACCESS_TOKEN y REFRESH_TOKEN para que el usuario te pase el REFRESH_TOKEN.
    """
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
    🔐 <strong>ACCESS_TOKEN (NO es necesario que lo guardes):</strong><br>
    <code>{access_token}</code><br><br>
    ♻️ <strong>REFRESH_TOKEN (ESTE SÍ DEBÉS GUARDAR):</strong><br>
    <code>{refresh_token}</code><br><br>
    👉 Copiá solo el valor de <strong>REFRESH_TOKEN</strong> y enviáselo al desarrollador.<br>
    El desarrollador lo guardará en un lugar seguro y lo configurará como variable
    de entorno <code>REFRESH_TOKEN</code> en Render.<br><br>
    Luego podrá usar la API de Mercado Libre sin necesidad de que vuelvas a autorizar.
    """


@app.route('/perfil')
def perfil():
    """
    Ejemplo de uso de la API con un access_token generado desde el refresh_token.
    """
    access_token = obtener_access_token()
    if not access_token:
        return ("❌ No se pudo obtener un ACCESS_TOKEN válido. "
                "Revisá que la variable REFRESH_TOKEN esté configurada en Render."), 401

    headers = {"Authorization": f"Bearer {access_token}"}

    # Obtener datos del usuario
    user_response = requests.get("https://api.mercadolibre.com/users/me", headers=headers)
    if user_response.status_code != 200:
        return f"❌ Error al obtener datos del usuario:<br>{user_response.text}", 500
    user = user_response.json()

    # Obtener publicaciones
    items_response = requests.get(
        f"https://api.mercadolibre.com/users/{user['id']}/items/search",
        headers=headers
    )
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
