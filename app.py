import os
import requests
from flask import Flask, request, render_template
from dotenv import load_dotenv

# Cargar variables desde el entorno o un .env si estás corriendo local
load_dotenv()

# Leer configuración desde variables de entorno
CLIENT_ID = os.getenv("CLIENT_ID")
CLIENT_SECRET = os.getenv("CLIENT_SECRET")
REDIRECT_URI = os.getenv("REDIRECT_URI")

app = Flask(__name__)

# Página principal con botón de autorización
@app.route('/')
def index():
    auth_url = (
        f"https://auth.mercadolibre.com.ar/authorization"
        f"?response_type=code"
        f"&client_id={CLIENT_ID}"
        f"&redirect_uri={REDIRECT_URI}"
    )
    return render_template("index.html", auth_url=auth_url)

# Endpoint que Mercado Libre llama con ?code= al autorizar
@app.route('/callback')
def callback():
    code = request.args.get('code')
    if not code:
        return "❌ No se recibió código de autorización", 400

    # Intercambiar el código por un access_token
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

    # Consultar métricas de ventas (abril 2024 como ejemplo)
    metric_response = requests.get(
        "https://api.mercadolibre.com/seller/metrics/search",
        headers={"Authorization": f"Bearer {access_token}"},
        params={
            "metric_type": "sales",
            "date_from": "2024-04-01",
            "date_to": "2024-04-30"
        }
    )

    if metric_response.status_code != 200:
        return f"❌ Error al obtener métricas:<br>{metric_response.text}", 500

    metrics = metric_response.json()
    return render_template("result.html", metrics=metrics)

# Recomendado para test local
if __name__ == '__main__':
    app.run(debug=True)
