import os
import logging
from flask import Flask, render_template, jsonify, request, redirect, url_for, session
from dotenv import load_dotenv
from flask_jwt_extended import JWTManager, verify_jwt_in_request, get_jwt, get_jwt_identity
from flask_pymongo import PyMongo
from flask_cors import CORS
from functools import wraps
import cohere
from bson import ObjectId

# Cargar variables de entorno
load_dotenv()

# Configurar logging
logging.basicConfig(level=logging.DEBUG)

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev-key-please-change')
app.config['JWT_SECRET_KEY'] = os.getenv('JWT_SECRET_KEY', 'jwt-secret-key-change')
app.config['JWT_TOKEN_LOCATION'] = ['headers', 'cookies']
app.config['JWT_COOKIE_SECURE'] = False
app.config['JWT_COOKIE_CSRF_PROTECT'] = False
app.config['JWT_ACCESS_TOKEN_EXPIRES'] = 86400
app.config['JWT_COOKIE_HTTPONLY'] = False 
app.config['JWT_COOKIE_SAMESITE'] = 'Lax'

# Configuración MongoDB
app.config['MONGO_URI'] = os.getenv('MONGO_URI')
mongo = PyMongo(app)

# Inicializar JWT
jwt = JWTManager(app)
CORS(app)

# Inicializar APIs
cohere_api_key = os.getenv('COHERE_API_KEY')
news_api_key = os.getenv('NEWS_API_KEY')

cohere_client = None
newsapi = None

if cohere_api_key:
    try:
        cohere_client = cohere.Client(cohere_api_key)
        app.logger.info("Cohere client initialized")
    except Exception as e:
        app.logger.error(f"Error initializing Cohere: {e}")
else:
    app.logger.warning("COHERE_API_KEY not set")

if news_api_key:
    try:
        newsapi = NewsApiClient(api_key=news_api_key)
        app.logger.info("NewsAPI client initialized")
    except Exception as e:
        app.logger.error(f"Error initializing NewsAPI: {e}")
else:
    app.logger.warning("NEWS_API_KEY not set")

# ============================================
# LIMPIEZA DE COOKIES
# ============================================

@app.before_request
def clear_invalid_cookies():
    """Limpia cookies inválidas en cada request"""
    if request.endpoint and 'static' not in request.endpoint:
        access_token = request.cookies.get('access_token')
        user_nombre = request.cookies.get('user_nombre')
        
        if (access_token and not user_nombre) or (user_nombre and not access_token):
            request.environ['clear_cookies'] = True

@app.after_request
def apply_cookie_cleanup(response):
    """Aplica limpieza de cookies si fue marcado"""
    if hasattr(request.environ, 'clear_cookies') and request.environ.get('clear_cookies'):
        response.delete_cookie('access_token', path='/')
        response.delete_cookie('user_nombre', path='/')
        response.delete_cookie('user_rol', path='/')
    return response

# ============================================
# DECORADORES
# ============================================

def login_required_page(f):
    """Decorador para proteger rutas de páginas web"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        access_token = request.cookies.get('access_token')
        
        if access_token:
            request.headers.environ['HTTP_AUTHORIZATION'] = f'Bearer {access_token}'
        
        try:
            verify_jwt_in_request()
            return f(*args, **kwargs)
        except Exception as e:
            return redirect(url_for('auth.login'))
    
    return decorated_function

def es_admin():
    """Verifica si el usuario actual es administrador"""
    access_token = request.cookies.get('access_token')
    if access_token:
        request.headers.environ['HTTP_AUTHORIZATION'] = f'Bearer {access_token}'
    try:
        verify_jwt_in_request()
        claims = get_jwt()
        return claims.get('rol') == 'admin'
    except:
        return False

def redirigir_admin(f):
    """Decorador que redirige a los admins al panel de administración"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if es_admin():
            return redirect(url_for('admin_panel'))
        return f(*args, **kwargs)
    return decorated_function

# ============================================
# BLUEPRINTS
# ============================================

from auth.routes import init_auth_routes
from auth.middleware import role_required
from api.servicios import init_servicios_routes
from api.paquetes import init_paquetes_routes
from api.auth_register import init_register_routes
from api.auth_login import init_login_routes  
from api.eventos import init_eventos_routes
from api.solicitudes import init_solicitudes_routes

# Inicializar rutas
auth_bp = init_auth_routes(mongo)
servicios_bp = init_servicios_routes(mongo)
paquetes_bp = init_paquetes_routes(mongo)
register_bp = init_register_routes(mongo)
login_bp = init_login_routes(mongo) 
eventos_bp = init_eventos_routes(mongo)
solicitudes_bp = init_solicitudes_routes(mongo)

# Registrar blueprints
app.register_blueprint(auth_bp)
app.register_blueprint(servicios_bp)
app.register_blueprint(paquetes_bp)
app.register_blueprint(register_bp)
app.register_blueprint(login_bp)
app.register_blueprint(eventos_bp) 

# ============================================
# RUTAS PÚBLICAS
# ============================================

@app.route('/')
def index():
    """Página de bienvenida - Pública"""
    return render_template('index.html',
                           ga_id=os.getenv('GA_MEASUREMENT_ID'),
                           twitch_channel=os.getenv('TWITCH_CHANNEL', 'Eventos Pro'))

# ============================================
# RUTAS DE USUARIO (Todos los autenticados)
# ============================================

@app.route('/paquetes')
@login_required_page
def paquetes():
    """Página de paquetes - Usuarios autenticados (admin y cliente)"""
    paquetes = list(mongo.db.paquetes.find({'activo': True}, {'_id': 0}))
    
    # Enriquecer paquetes con detalles de servicios
    for paquete in paquetes:
        servicios_ids = paquete.get('servicios_ids', [])
        servicios = list(mongo.db.servicios.find(
            {'id': {'$in': servicios_ids}, 'activo': True},
            {'_id': 0, 'id': 1, 'nombre': 1, 'descripcion': 1, 'precio': 1}
        ))
        paquete['servicios_detalle'] = servicios
    
    return render_template('user/paquetes.html',
                           paquetes=paquetes,
                           ga_id=os.getenv('GA_MEASUREMENT_ID'),
                           twitch_channel=os.getenv('TWITCH_CHANNEL', 'Eventos Pro'))

@app.route('/servicios')
@login_required_page
def servicios():
    """Página de servicios individuales - Usuarios autenticados (admin y cliente)"""
    servicios = list(mongo.db.servicios.find({'activo': True}, {'_id': 0}))
    return render_template('user/servicios.html',
                           servicios=servicios,
                           ga_id=os.getenv('GA_MEASUREMENT_ID'),
                           twitch_channel=os.getenv('TWITCH_CHANNEL', 'Eventos Pro'))

# ============================================
# RUTAS DE ADMINISTRACIÓN
# ============================================

@app.route('/admin')
@login_required_page
@role_required('admin')
def admin_panel():
    """Redirige directo a servicios al entrar como admin"""
    return redirect(url_for('admin_servicios'))

@app.route('/admin/usuario/<user_id>/rol', methods=['PUT'])
@login_required_page
@role_required('admin')
def cambiar_rol_usuario(user_id):
    """API para cambiar rol de usuario"""
    data = request.get_json()
    nuevo_rol = data.get('rol')
    
    if nuevo_rol not in ['cliente', 'admin']:
        return jsonify({'error': 'Rol inválido'}), 400
    
    result = mongo.db.users.update_one(
        {'_id': ObjectId(user_id)},
        {'$set': {'rol': nuevo_rol}}
    )
    
    if result.modified_count:
        return jsonify({'success': True})
    return jsonify({'success': False}), 404

@app.route('/admin/usuario/<user_id>', methods=['DELETE'])
@login_required_page
@role_required('admin')
def eliminar_usuario(user_id):
    """API para eliminar usuario"""
    result = mongo.db.users.delete_one({'_id': ObjectId(user_id)})
    
    if result.deleted_count:
        return jsonify({'success': True})
    return jsonify({'success': False}), 404

# ============================================
# ENDPOINTS API (Públicos)
# ============================================

@app.route('/admin/servicios')
@login_required_page
@role_required('admin')
def admin_servicios():
    return render_template('admin/servicios.html',
                           ga_id=os.getenv('GA_MEASUREMENT_ID'),
                           twitch_channel=os.getenv('TWITCH_CHANNEL', 'Eventos Pro'))

@app.route('/admin/paquetes')
@login_required_page
@role_required('admin')
def admin_paquetes():
    return render_template('admin/paquetes.html',
                           ga_id=os.getenv('GA_MEASUREMENT_ID'),
                           twitch_channel=os.getenv('TWITCH_CHANNEL', 'Eventos Pro'))

@app.route('/admin/solicitudes')
@login_required_page
@role_required('admin')
def admin_solicitudes():
    return render_template('admin/solicitudes.html',
                           ga_id=os.getenv('GA_MEASUREMENT_ID'),
                           twitch_channel=os.getenv('TWITCH_CHANNEL', 'Eventos Pro'))

@app.route('/admin/crear-admin')
@login_required_page
@role_required('admin')
def admin_crear_admin():
    return render_template('admin/crear_admin.html',
                           ga_id=os.getenv('GA_MEASUREMENT_ID'),
                           twitch_channel=os.getenv('TWITCH_CHANNEL', 'Eventos Pro'))

@app.route('/api/admin/crear', methods=['POST'])
@login_required_page
@role_required('admin')
def api_crear_admin():
    """Crear nuevo administrador usando bcrypt igual que el sistema"""
    import bcrypt
    import re
    data = request.get_json()
    nombre   = data.get('nombre', '').strip()
    email    = data.get('email', '').strip().lower()
    password = data.get('password', '')

    if not nombre or not email or not password:
        return jsonify({'success': False, 'error': 'Todos los campos son requeridos'}), 400
    if not re.match(r'^[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}$', email):
        return jsonify({'success': False, 'error': 'Correo inválido'}), 400
    if len(password) < 6:
        return jsonify({'success': False, 'error': 'La contraseña debe tener al menos 6 caracteres'}), 400
    if mongo.db.users.find_one({'email': email}):
        return jsonify({'success': False, 'error': 'El correo ya está registrado'}), 400

    # Usar bcrypt igual que auth/routes.py
    salt = bcrypt.gensalt()
    hashed_password = bcrypt.hashpw(password.encode('utf-8'), salt)

    mongo.db.users.insert_one({
        'nombre':          nombre,
        'email':           email,
        'password':        hashed_password,   # Binary bcrypt, igual que los demás usuarios
        'rol':             'admin',
        'fecha_registro':  __import__('datetime').datetime.utcnow(),
        'activo':          True
    })
    return jsonify({'success': True}), 201


@app.route('/api/chat', methods=['POST'])
def chat():
    """Endpoint para el chatbot"""
    if not cohere_client:
        return jsonify({'error': 'Chatbot no configurado'}), 503

    data = request.get_json()
    mensaje = data.get('message', '')
    if not mensaje:
        return jsonify({'error': 'Mensaje vacío'}), 400

    try:
        import unicodedata

        def limpiar_texto(texto):
            texto = texto.lower()
            return ''.join(
                c for c in unicodedata.normalize('NFD', texto)
                if unicodedata.category(c) != 'Mn'
            )

        mensaje_limpio = limpiar_texto(mensaje)

        palabras_clave = [
            "precio", "costo", "contratar", "contacto",
            "telefono", "correo", "informacion", "reservar",
            "agenda", "cotizacion", "donde", "ubicacion"
        ]

        agregar_contacto = any(palabra in mensaje_limpio for palabra in palabras_clave)

        # 🔒 PROMPT MUCHO MÁS CONTROLADO
        preamble_base = """
Eres el asistente oficial de EventosPro.

Reglas IMPORTANTES:
- NO inventes información.
- NO generes teléfonos, correos o páginas web que no se te indiquen.
- SOLO usa la información proporcionada abajo.
- Responde de forma clara, breve y amable.
- No uses datos genéricos como "+1 (XXX)" o "info@empresa.com".

Información oficial:
Empresa: EventosPro
Servicios: Fotografía y video para eventos sociales

Datos de contacto oficiales:
Correo: eventospro37@gmail.com
Teléfono: 4152157955
"""

        if agregar_contacto:
            preamble_base += """
Instrucción adicional:
- El usuario está solicitando información de contacto o contratación.
- Incluye los datos de contacto EXACTAMENTE como están arriba.
"""
        else:
            preamble_base += """
Instrucción adicional:
- NO incluyas datos de contacto si no te los piden.
"""

        response = cohere_client.chat(
            message=mensaje,
            preamble=preamble_base
        )

        return jsonify({'respuesta': response.text})

    except Exception as e:
        app.logger.error(f"Error en Cohere: {e}")
        return jsonify({'error': 'Error al procesar la solicitud'}), 500

# ============================================
# EJECUCIÓN
# ============================================

if __name__ == '__main__':
    app.run(debug=True, port=5000)