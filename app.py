# Requisitos previos:
# 1. Crea una cuenta en Unsplash y genera una API Key en https://unsplash.com/developers
# 2. Instala las bibliotecas necesarias con el comando: pip install requests flask python-dotenv

import os
import requests
from flask import Flask, request, render_template

# Cargar variables de entorno desde un archivo .env
# Reemplazando el valor directo con la clave proporcionada
UNSPLASH_API_KEY = "wNkuIw-UT0DkVAaOrPyAKPV25K8OJjcVy5suuDo2JEw"
UNSPLASH_API_URL = "https://api.unsplash.com/search/photos"

if not UNSPLASH_API_KEY:
    raise ValueError("La variable de entorno 'UNSPLASH_API_KEY' no está configurada.")

# Configuración de Flask
app = Flask(__name__)

@app.route("/", methods=["GET"])
def home():
    return render_template("index.html")

@app.route("/search", methods=["POST"])
def search():
    keyword = request.form.get("keyword")
    if not keyword:
        return "Por favor, ingresa una palabra clave para buscar imágenes.", 400

    response = requests.get(
        UNSPLASH_API_URL,
        headers={"Authorization": f"Client-ID {UNSPLASH_API_KEY}"},
        params={"query": keyword, "per_page": 10}
    )

    if response.status_code != 200:
        return f"Error al consultar la API de Unsplash: {response.status_code}", response.status_code

    data = response.json()
    images = [result["urls"]["regular"] for result in data.get("results", [])]

    return render_template("results.html", keyword=keyword, images=images)

if __name__ == "__main__":
    app.run(debug=True)