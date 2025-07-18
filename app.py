import os
import requests
from flask import Flask, request, render_template_string
from dotenv import load_dotenv

# Cargar variables desde .env (para local)
load_dotenv()

# Configuración desde entorno
CLIENT_ID = os.getenv("CLIENT_ID")
CLIENT_SECRET = os.getenv("CLIENT_SECRET")
REDIRECT_URI = os.getenv("REDIRECT_URI")

app = Flask(__name__)

@app.route('/')
def index():
    auth_url = (
        "https://auth.mercadolibre.com.ar/authorization"
        f"?response_type=code"
        f"&client_id={CLIENT_ID}"
        f"&redirect_uri={REDIRECT_URI}"
    )
    return f'<a href="{auth_url}">🔐 Autorizar con Mercado Libre</a>'

@app.route('/callback')
def callback():
    code = request.args.get('code')
    if not code:
        return "❌ No se recibió código de autorización", 400

    # Obtener access_token
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

    access_token = token_response.json().get("access_token")

    # Consultar info del usuario
    user_response = requests.get(
        "https://api.mercadolibre.com/users/me",
        headers={"Authorization": f"Bearer {access_token}"}
    )

    if user_response.status_code != 200:
        return f"❌ Error al obtener datos de usuario:<br>{user_response.text}", 500

    user = user_response.json()
    address = user.get("address", {})
    reputation = user.get("seller_reputation", {})
    registration = user.get("registration_date", "")[:10]  # solo YYYY-MM-DD

    # Renderizar resumen con HTML simple
    return render_template_string(f"""
        <h2>✅ Bienvenido, <strong>{user.get('nickname')}</strong></h2>
        <ul>
            <li><strong>ID de usuario:</strong> {user.get('id')}</li>
            <li><strong>Tipo de cuenta:</strong> {user.get('user_type')}</li>
            <li><strong>Fecha de registro:</strong> {registration}</li>
            <li><strong>Ubicación:</strong> {address.get('city', '')}, {address.get('state', '')}</li>
            <li><strong>Sitio:</strong> {user.get('site_id')}</li>
            <li><strong>Reputación:</strong> {reputation.get('level_id', 'Sin actividad')}</li>
        </ul>
    """)

if __name__ == '__main__':
    app.run(debug=True)
