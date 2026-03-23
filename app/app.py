import os
import logging
from flask import Flask, render_template, jsonify, request, redirect, url_for, session
from dotenv import load_dotenv
from flask_jwt_extended import JWTManager, verify_jwt_in_request, get_jwt, get_jwt_identity
from flask_pymongo import PyMongo
from flask_cors import CORS
from functools import wraps
import cohere
from newsapi import NewsApiClient
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

# Inicializar rutas
auth_bp = init_auth_routes(mongo)
servicios_bp = init_servicios_routes(mongo)
paquetes_bp = init_paquetes_routes(mongo)
register_bp = init_register_routes(mongo)
login_bp = init_login_routes(mongo) 

# Registrar blueprints
app.register_blueprint(auth_bp)
app.register_blueprint(servicios_bp)
app.register_blueprint(paquetes_bp)
app.register_blueprint(register_bp)
app.register_blueprint(login_bp)

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

@app.route('/noticias')
@login_required_page
def noticias():
    """Página de noticias - Usuarios autenticados (admin y cliente)"""
    return render_template('user/noticias.html',
                           ga_id=os.getenv('GA_MEASUREMENT_ID'),
                           twitch_channel=os.getenv('TWITCH_CHANNEL', 'Eventos Pro'))

# ============================================
# RUTAS DE ADMINISTRACIÓN
# ============================================

@app.route('/admin')
@login_required_page
@role_required('admin')
def admin_panel():
    """Panel de administración (solo admin)"""
    user_id = get_jwt_identity()
    user = mongo.db.users.find_one({'_id': ObjectId(user_id)})
    
    # Obtener estadísticas
    total_servicios = mongo.db.servicios.count_documents({'activo': True})
    total_paquetes = mongo.db.paquetes.count_documents({'activo': True})
    total_usuarios = mongo.db.users.count_documents({'activo': True})
    
    return render_template('admin/dashboard.html',
                         user_nombre=user.get('nombre'),
                         user_email=user.get('email'),
                         total_servicios=total_servicios,
                         total_paquetes=total_paquetes,
                         total_usuarios=total_usuarios,
                         ga_id=os.getenv('GA_MEASUREMENT_ID'),
                         twitch_channel=os.getenv('TWITCH_CHANNEL', 'Eventos Pro'))

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
        response = cohere_client.chat(
            message=mensaje,
            preamble="Eres un asistente virtual de EventosPro, una empresa de fotografía y video para eventos sociales. Responde de forma amable y breve, ayudando a los clientes a elegir paquetes o servicios."
        )
        return jsonify({'respuesta': response.text})
    except Exception as e:
        app.logger.error(f"Error en Cohere: {e}")
        return jsonify({'error': 'Error al procesar la solicitud'}), 500

@app.route('/api/noticias')
def api_noticias():
    """Obtener noticias de eventos sociales"""
    if not newsapi:
        return jsonify({'error': 'API de noticias no configurada'}), 503

    try:
        noticias = newsapi.get_everything(
            q='bodas OR "XV años" OR "eventos sociales" OR quinceañera OR wedding',
            language='es',
            sort_by='relevancy',
            page_size=5
        )
        articulos = noticias.get('articles', [])
        for art in articulos:
            art.pop('source', None)
        return jsonify(articulos)
    except Exception as e:
        app.logger.error(f"Error en NewsAPI: {e}")
        return jsonify({'error': 'Error al obtener noticias'}), 500

# ============================================
# EJECUCIÓN
# ============================================

if __name__ == '__main__':
    app.run(debug=True, port=5000)