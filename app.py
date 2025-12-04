# force redeploy
import os
import requests
from flask import (
    Flask,
    request,
    render_template,
    session,
    redirect,
    url_for
)
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

# Password global de la app (para login)
APP_PASSWORD = os.getenv("APP_PASSWORD")

app = Flask(__name__)

# Clave para firmar las cookies de sesión
app.secret_key = os.getenv("FLASK_SECRET_KEY", "dev-secret-change-me")


# ==========================
# Autenticación simple global
# ==========================

@app.before_request
def require_login():
    """
    Fuerza login para toda la app, excepto:
      - /login  (pantalla de login)
      - /callback  (callback de Mercado Libre)
      - /static/...  (archivos estáticos)
    Si APP_PASSWORD no está definida, no aplica protección (modo desarrollo).
    """
    if not APP_PASSWORD:
        # Si no hay password configurada, no exigimos login
        return

    path = request.path

    # Rutas exentas de protección
    if path.startswith("/static"):
        return
    if path == "/login":
        return
    if path == "/callback":
        return

    # Si ya está logueado, OK
    if session.get("logged_in"):
        return

    # Si no está logueado, redirigimos a /login
    return redirect(url_for("login", next=path))


# ==========================
# Ruta de Login
# ==========================

@app.route("/login", methods=["GET", "POST"])
def login():
    """
    Login muy simple con una sola contraseña global (APP_PASSWORD).
    Guarda en sesión un flag logged_in = True.
    """
    if request.method == "POST":
        password = request.form.get("password", "")
        if APP_PASSWORD and password == APP_PASSWORD:
            session["logged_in"] = True
            # Si vino con ?next=/algo, lo respetamos
            next_url = request.args.get("next") or url_for("perfil")
            return redirect(next_url)
        else:
            error = "Contraseña incorrecta"
    else:
        error = None

    return f"""
    <!doctype html>
    <html lang="es">
    <head>
        <meta charset="utf-8">
        <title>Login - Panel Mercado Libre</title>
        <link rel="stylesheet"
              href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css">
    </head>
    <body class="bg-light">
        <div class="container py-5" style="max-width: 400px;">
            <h3 class="mb-4">Acceso al panel de Mercado Libre</h3>
            <form method="post" class="card card-body shadow-sm">
                <div class="mb-3">
                    <label class="form-label">Contraseña</label>
                    <input type="password" name="password" class="form-control"
                           autofocus required>
                </div>
                {"<div class='alert alert-danger py-2 mb-2'>" + error + "</div>" if error else ""}
                <button type="submit" class="btn btn-primary w-100">Ingresar</button>
            </form>
        </div>
    </body>
    </html>
    """


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
    Esta ruta está exenta del login en require_login().
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

    # Obtener publicaciones (IDs)
    items_response = requests.get(
        f"https://api.mercadolibre.com/users/{user['id']}/items/search",
        headers=headers
    )
    items = items_response.json().get("results", []) if items_response.status_code == 200 else []

    html = f"""
    <html>
    <head>
        <meta charset="utf-8">
        <title>Perfil Mercado Libre</title>
    </head>
    <body>
        ✅ Bienvenido, <strong>{user.get('nickname')}</strong><br>
        ID de usuario: {user.get('id')}<br>
        Tipo de cuenta: {user.get('user_type')}<br><br>
        <a href="/buscar_items">🔍 Buscar ítems con fotos</a><br><br>
        <strong>📦 Publicaciones activas (IDs):</strong><br>
    """
    if items:
        for item in items:
            html += f"- ID publicación: {item}<br>"
    else:
        html += "No tenés publicaciones activas.<br>"

    html += "</body></html>"
    return html


@app.route('/buscar_items')
def buscar_items():
    """
    Busca ítems de la cuenta conectada que coincidan con un criterio 'q'
    y muestra hasta los primeros 10 en cards con foto, título, precio, estado y link.
    """
    criterio = request.args.get('q', '').strip()

    # Si no hay criterio, muestro un formulario simple y prolijo
    if not criterio:
        return """
        <!doctype html>
        <html lang="es">
        <head>
            <meta charset="utf-8">
            <title>Buscar ítems</title>
            <link rel="stylesheet"
                  href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css">
        </head>
        <body class="bg-light">
            <div class="container py-4">
                <h2 class="mb-3">Buscar ítems en Mercado Libre</h2>
                <form method="get" action="/buscar_items" class="row g-2">
                    <div class="col-auto">
                        <input type="text" name="q" class="form-control"
                               placeholder="Ej: batería, filtro, bujía..." required>
                    </div>
                    <div class="col-auto">
                        <button type="submit" class="btn btn-primary">Buscar</button>
                    </div>
                </form>
                <hr>
                <a href="/perfil" class="btn btn-link">⬅ Volver a /perfil</a>
            </div>
        </body>
        </html>
        """

    access_token = obtener_access_token()
    if not access_token:
        return ("❌ No se pudo obtener un ACCESS_TOKEN válido. "
                "Revisá que la variable REFRESH_TOKEN esté configurada en Render."), 401

    headers = {"Authorization": f"Bearer {access_token}"}

    # Primero obtengo el usuario para conocer su ID
    user_response = requests.get("https://api.mercadolibre.com/users/me", headers=headers)
    if user_response.status_code != 200:
        return f"❌ Error al obtener datos del usuario:<br>{user_response.text}", 500

    user = user_response.json()
    user_id = user.get("id")

    # Buscar items del usuario con el criterio
    search_url = f"https://api.mercadolibre.com/users/{user_id}/items/search"
    params = {
        "q": criterio,
        "limit": 10
    }

    items_response = requests.get(search_url, headers=headers, params=params)
    if items_response.status_code != 200:
        return f"❌ Error al buscar ítems:<br>{items_response.text}", 500

    results = items_response.json().get("results", [])

    # Para cada ID, traigo más info (título, precio, thumbnail, permalink, status)
    detalles = []
    for item_id in results[:10]:
        item_resp = requests.get(f"https://api.mercadolibre.com/items/{item_id}", headers=headers)
        if item_resp.status_code == 200:
            info = item_resp.json()
            detalles.append({
                "id": item_id,
                "title": info.get("title"),
                "price": info.get("price"),
                "thumbnail": info.get("thumbnail"),
                "permalink": info.get("permalink"),
                "status": info.get("status"),  # estado de la publicación
            })
        else:
            detalles.append({
                "id": item_id,
                "title": "(No se pudo obtener detalle)",
                "price": None,
                "thumbnail": None,
                "permalink": None,
                "status": None
            })

    # Armo HTML con Bootstrap cards
    html = f"""
    <!doctype html>
    <html lang="es">
    <head>
        <meta charset="utf-8">
        <title>Resultados de búsqueda</title>
        <link rel="stylesheet"
              href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css">
    </head>
    <body class="bg-light">
        <div class="container py-4">
            <h2 class="mb-3">Resultados de búsqueda para: <em>{criterio}</em></h2>
            <p>Cuenta conectada: <strong>{user.get('nickname')}</strong> (ID: {user_id})</p>
            <div class="row g-3">
    """

    if detalles:
        for d in detalles:
            thumb = d.get("thumbnail") or "https://via.placeholder.com/180x180?text=Sin+Imagen"
            price = d.get("price")
            price_txt = (
                f"${price:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
                if price is not None else "N/D"
            )
            permalink = d.get("permalink") or "#"

            estado = d.get("status") or "desconocido"
            if estado == "active":
                badge_class = "success"
            elif estado == "paused":
                badge_class = "warning"
            elif estado == "closed":
                badge_class = "secondary"
            else:
                badge_class = "dark"

            html += f"""
                <div class="col-12 col-sm-6 col-md-4 col-lg-3">
                    <div class="card h-100 shadow-sm">
                        <img src="{thumb}" class="card-img-top" alt="{d.get('title', '')}"
                             style="object-fit: contain; width: 100%; height: 180px; background-color: #f8f9fa;">
                        <div class="card-body d-flex flex-column">
                            <h6 class="card-title" style="min-height: 3em;">{d.get('title', '')}</h6>
                            <p class="card-text"><strong>{price_txt}</strong></p>
                            <p class="card-text mb-1">
                                <small class="text-muted">ID: {d['id']}</small>
                            </p>
                            <p class="card-text">
                                <span class="badge bg-{badge_class}">Estado: {estado}</span>
                            </p>
                            <a href="{permalink}" target="_blank" class="btn btn-sm btn-primary mt-auto">
                                Ver en Mercado Libre
                            </a>
                        </div>
                    </div>
                </div>
            """
    else:
        html += """
            <div class="col-12">
                <div class="alert alert-info">
                    No se encontraron ítems que coincidan con el criterio.
                </div>
            </div>
        """

    html += """
            </div> <!-- row -->
            <hr class="mt-4">
            <a href="/buscar_items" class="btn btn-secondary">🔎 Nueva búsqueda</a>
            <a href="/perfil" class="btn btn-link">⬅ Volver a /perfil</a>
        </div> <!-- container -->
    </body>
    </html>
    """

    return html


@app.route('/probar_edicion/<item_id>')
def probar_edicion(item_id):
    access_token = obtener_access_token()
    if not access_token:
        return "❌ No se pudo obtener un access token.", 401

    headers = {"Authorization": f"Bearer {access_token}"}

    # 1) Traigo el ítem para saber el precio actual
    get_url = f"https://api.mercadolibre.com/items/{item_id}"
    get_resp = requests.get(get_url, headers=headers)

    if get_resp.status_code != 200:
        return f"❌ No se pudo obtener el ítem {item_id}: ({get_resp.status_code})<br>{get_resp.text}"

    item_data = get_resp.json()

    # Tomo un precio "actual" para enviar en el dry_run
    price = item_data.get("price")

    # Si tiene variaciones, uso el precio de la primera variación
    if price is None and item_data.get("variations"):
        first_var = item_data["variations"][0]
        price = first_var.get("price")

    if price is None:
        return ("⚠️ No se pudo determinar un precio actual para el ítem, "
                "pero el token igualmente permite acceder al recurso (GET exitoso).")

    # 2) Hago un PUT en dry_run con el mismo precio
    put_url = f"https://api.mercadolibre.com/items/{item_id}?dry_run=true"
    put_body = {"price": price}
    put_headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }

    put_resp = requests.put(put_url, headers=put_headers, json=put_body)

    if put_resp.status_code in (200, 202):
        return (f"✅ Tenés permiso para editar el ítem {item_id}.<br>"
                f"Dry-run OK enviando el mismo precio actual ({price}).<br>"
                f"No se modificó nada en Mercado Libre.")
    elif put_resp.status_code == 403:
        return f"❌ El token NO tiene permisos para editar el ítem {item_id} (403 Forbidden)."
    else:
        return (f"⚠️ Resultado inesperado ({put_resp.status_code}) en el dry-run:<br>"
                f"{put_resp.text}")


# ==========================
# Ejecutar app localmente
# ==========================
if __name__ == '__main__':
    app.run(debug=True)
