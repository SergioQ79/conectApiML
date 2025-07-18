import os
import requests
from flask import Flask, request, render_template
from dotenv import load_dotenv

# Cargar variables desde .env
load_dotenv()

# Leer configuración desde entorno
CLIENT_ID = os.getenv("CLIENT_ID")
CLIENT_SECRET = os.getenv("CLIENT_SECRET")
REDIRECT_URI = os.getenv("REDIRECT_URI")

app = Flask(__name__)

@app.route('/')
def index():
    auth_url = (
        f"https://auth.mercadolibre.com.ar/authorization"
        f"?response_type=code"
        f"&client_id={CLIENT_ID}"
        f"&redirect_uri={REDIRECT_URI}"
    )
    return render_template("index.html", auth_url=auth_url)

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

    headers = {"Authorization": f"Bearer {access_token}"}

    # Obtener datos del usuario
    user_response = requests.get("https://api.mercadolibre.com/users/me", headers=headers)
    if user_response.status_code != 200:
        return f"❌ Error al obtener datos del usuario:<br>{user_response.text}", 500
    user = user_response.json()

    # Obtener direcciones
    addresses_response = requests.get(f"https://api.mercadolibre.com/users/{user['id']}/addresses", headers=headers)
    addresses = addresses_response.json() if addresses_response.status_code == 200 else []

    # Obtener teléfonos
    phones_response = requests.get(f"https://api.mercadolibre.com/users/{user['id']}/phones", headers=headers)
    phones = phones_response.json() if phones_response.status_code == 200 else {}

    # Obtener publicaciones
    items_response = requests.get(f"https://api.mercadolibre.com/users/{user['id']}/items/search", headers=headers)
    items = items_response.json().get("results", []) if items_response.status_code == 200 else []

    # Mostrar todo en HTML simple
    html = f"""
    ✅ Bienvenido, <strong>{user.get('nickname')}</strong><br>
    ID de usuario: {user.get('id')}<br>
    Tipo de cuenta: {user.get('user_type')}<br><br>

    <strong>📍 Direcciones:</strong><br>
    """
    if addresses:
        for addr in addresses:
            html += f"- {addr.get('address_line', 'Sin dirección completa')} ({addr.get('city', {}).get('name', '')})<br>"
    else:
        html += "Sin direcciones registradas.<br>"

    html += "<br><strong>📞 Teléfonos:</strong><br>"
    if phones:
        html += f"Número: {phones.get('area_code', '')}-{phones.get('number', '')}<br>"
    else:
        html += "Sin teléfonos registrados.<br>"

    html += "<br><strong>📦 Publicaciones activas:</strong><br>"
    if items:
        for item in items:
            html += f"- ID publicación: {item}<br>"
    else:
        html += "No tenés publicaciones activas.<br>"

    return html

if __name__ == '__main__':
    app.run(debug=True)
