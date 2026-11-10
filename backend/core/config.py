import os

from dotenv import load_dotenv

load_dotenv()

# ==========================================
# CONFIGURACIÓN JWT (cargada desde .env, nunca hardcodeada)
# ==========================================
SECRET_KEY = os.getenv("JWT_SECRET_KEY")
if not SECRET_KEY:
    raise RuntimeError(
        "JWT_SECRET_KEY no está configurada en el .env. "
        "Genera una con `python -c \"import secrets; print(secrets.token_hex(32))\"` "
        "y agrégala como JWT_SECRET_KEY=... en tu archivo .env."
    )
ALGORITHM = "HS256"
# Sesión deslizante: el token dura 30 días y la app lo cambia por uno nuevo (POST /auth/refresh) cada vez
# que se abre o pasa un rato, así que quien la usa no vuelve a iniciar sesión; solo quien pasa 30 días sin
# abrirla. Es seguro porque el token sigue atado a token_version: cerrar sesión lo revoca al instante.
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 30

# En producción (.env: ENVIRONMENT=production) se ocultan /docs, /redoc y el schema OpenAPI:
# expuestos sin autenticación, revelan toda la superficie de la API a cualquiera.
ENVIRONMENT = os.getenv("ENVIRONMENT", "development")
DOCS_ENABLED = ENVIRONMENT != "production"

# CORS: orígenes permitidos configurables desde .env (por defecto, solo el frontend local)
CORS_ORIGINS = [
    o.strip()
    for o in os.getenv("CORS_ORIGINS", "http://localhost:8501,http://127.0.0.1:8501").split(",")
    if o.strip()
]

# Correo (recuperar contraseña). Sin EMAIL_API_KEY no se envía nada: en desarrollo el enlace sale en el log;
# en producción se avisa en el log de que falta configurarlo. Proveedor: Resend (https://resend.com).
EMAIL_API_KEY = os.getenv("EMAIL_API_KEY", "")
EMAIL_FROM = os.getenv("EMAIL_FROM", "NeuroLift <no-reply@neurolift.app>")
# URL pública del front, para los enlaces de los correos. Por defecto, el primer origen de CORS.
FRONTEND_URL = os.getenv("FRONTEND_URL", "").strip().rstrip("/") or (CORS_ORIGINS[0] if CORS_ORIGINS else "")
# El enlace para restablecer la contraseña sirve una sola vez y vence a la hora.
RESET_TOKEN_MINUTES = 60

# Monitoreo de errores (Sentry). Sin SENTRY_DSN no se envía nada.
SENTRY_DSN = os.getenv("SENTRY_DSN", "")

# Cuántos proxies de confianza hay delante de la API (Render, un CDN...). Detrás de un proxy, la IP que ve el
# servidor es la del proxy, así que TODOS los usuarios compartirían los límites por IP (intentos de login,
# registros...). Con PROXY_HOPS=N se toma como IP del cliente la N-ésima desde la derecha de X-Forwarded-For
# (la que añadió tu proxy, que no se puede falsear desde fuera). 0 = sin proxy: se usa la IP de la conexión.
# Cómo saber el valor: en el log "Login exitoso ... desde X", X debe ser distinta para cada dispositivo.
PROXY_HOPS = int(os.getenv("PROXY_HOPS", "0"))

# La IA es lo más lento y caro: cuántas peticiones de IA procesa a la vez CADA proceso (las demás esperan hasta
# IA_ESPERA_MAXIMA_SEGUNDOS y, si no hay lugar, reciben un 503 que pide reintentar). Así unas pocas generaciones
# largas no dejan al resto de los usuarios sin servidor. Ver core/ia_limite.py.
MAX_IA_SIMULTANEAS = int(os.getenv("MAX_IA_SIMULTANEAS", "3"))
IA_ESPERA_MAXIMA_SEGUNDOS = float(os.getenv("IA_ESPERA_MAXIMA_SEGUNDOS", "20"))
# Quien espera un lugar de IA también ocupa una plaza del servidor: solo se deja esperar a este número; el resto
# recibe el 503 de inmediato (así la cola de IA nunca se queda con todas las plazas).
MAX_IA_EN_ESPERA = int(os.getenv("MAX_IA_EN_ESPERA", "5"))

# Cuántas peticiones HTTP procesa a la vez CADA proceso de la API; las demás esperan en cola (y
# si esperan más de HTTP_QUEUE_TIMEOUT_SECONDS reciben 503). Se recorta al tamaño del pool de
# conexiones. 0 lo desactiva. Ver core/concurrency.py.
MAX_CONCURRENT_REQUESTS = int(os.getenv("MAX_CONCURRENT_REQUESTS", "20"))
HTTP_QUEUE_TIMEOUT_SECONDS = float(os.getenv("HTTP_QUEUE_TIMEOUT_SECONDS", "15"))
