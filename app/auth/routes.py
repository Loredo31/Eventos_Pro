from flask import Blueprint, request, jsonify, render_template, redirect, url_for
from flask_jwt_extended import create_access_token, jwt_required, get_jwt_identity, create_refresh_token
from datetime import timedelta
import bcrypt
from bson import ObjectId
from datetime import datetime

auth_bp = Blueprint('auth', __name__, url_prefix='/auth')

def init_auth_routes(mongo):
    """Inicializar rutas de autenticación"""
    
    # Funciones auxiliares que usan mongo
    def find_user_by_email(email):
        """Buscar usuario por email"""
        return mongo.db.users.find_one({'email': email})
    
    def find_user_by_id(user_id):
        """Buscar usuario por ID"""
        try:
            return mongo.db.users.find_one({'_id': ObjectId(user_id)})
        except:
            return None
    
    def create_user(nombre, email, password, rol='cliente'):
        """Crear un nuevo usuario"""
        # Verificar si el email ya existe
        if mongo.db.users.find_one({'email': email}):
            return None
        
        # Hash de la contraseña
        salt = bcrypt.gensalt()
        hashed_password = bcrypt.hashpw(password.encode('utf-8'), salt)
        
        user = {
            'nombre': nombre,
            'email': email,
            'password': hashed_password,
            'rol': rol,
            'fecha_registro': datetime.utcnow(),
            'activo': True
        }
        
        result = mongo.db.users.insert_one(user)
        return str(result.inserted_id)
    
    def verify_password(password, hashed):
        """Verificar contraseña"""
        return bcrypt.checkpw(password.encode('utf-8'), hashed)
    
    @auth_bp.route('/login', methods=['GET', 'POST'])
    def login():
        if request.method == 'GET':
            return render_template('auth/login.html', is_auth_page=True)
        
        # POST: Procesar login
        data = request.get_json() if request.is_json else request.form
        email = data.get('email')
        password = data.get('password')
        
        if not email or not password:
            if request.is_json:
                return jsonify({'error': 'Email y contraseña requeridos'}), 400
            return render_template('auth/login.html', error='Email y contraseña requeridos', is_auth_page=True)
        
        user = find_user_by_email(email)
        
        if not user or not verify_password(password, user['password']):
            if request.is_json:
                return jsonify({'error': 'Credenciales inválidas'}), 401
            return render_template('auth/login.html', error='Credenciales inválidas', is_auth_page=True)
        
        # Determinar user_id (preferir campo numérico 'id' si existe, si no usar string de _id)
        user_id_value = user.get('id')
        if user_id_value is None:
            user_id_value = str(user['_id'])
        
        # Crear tokens con claims adicionales incluyendo user_id
        additional_claims = {
            'rol': user['rol'],
            'nombre': user['nombre'],
            'user_id': user_id_value
        }
        access_token = create_access_token(
            identity=str(user['_id']),
            additional_claims=additional_claims,
            expires_delta=timedelta(hours=24)
        )
        refresh_token = create_refresh_token(identity=str(user['_id']))
        
        if request.is_json:
            return jsonify({
                'access_token': access_token,
                'refresh_token': refresh_token,
                'user': {
                    'id': str(user['_id']),
                    'nombre': user['nombre'],
                    'email': user['email'],
                    'rol': user['rol']
                }
            })
        
        # Para peticiones de formulario (HTML) - ahora httponly=False
        if user['rol'] == 'admin':
            response = redirect(url_for('admin_panel'))
        else:
            response = redirect(url_for('paquetes'))
        
        # Establecer cookies con httponly=False y samesite='Lax'
        response.set_cookie('access_token', access_token,
                            httponly=False,
                            max_age=86400,
                            path='/',
                            samesite='Lax')
        response.set_cookie('user_nombre', user['nombre'],
                            max_age=86400, path='/')
        response.set_cookie('user_rol', user['rol'],
                            max_age=86400, path='/')
        return response
    
    @auth_bp.route('/register', methods=['GET', 'POST'])
    def register():
        if request.method == 'GET':
            return render_template('auth/register.html', is_auth_page=True)
        
        # POST: Procesar registro
        data = request.get_json() if request.is_json else request.form
        nombre = data.get('nombre')
        email = data.get('email')
        password = data.get('password')
        
        if not nombre or not email or not password:
            if request.is_json:
                return jsonify({'error': 'Todos los campos son requeridos'}), 400
            return render_template('auth/register.html', error='Todos los campos son requeridos', is_auth_page=True)
        
        # Crear usuario (por defecto rol 'cliente')
        user_id = create_user(nombre, email, password, 'cliente')
        
        if not user_id:
            if request.is_json:
                return jsonify({'error': 'El email ya está registrado'}), 400
            return render_template('auth/register.html', error='El email ya está registrado', is_auth_page=True)
        
        if request.is_json:
            return jsonify({'message': 'Usuario creado exitosamente', 'user_id': user_id}), 201
        
        return redirect(url_for('auth.login'))
    
    @auth_bp.route('/logout', methods=['POST', 'GET'])
    def logout():
        response = redirect(url_for('index'))
        response.delete_cookie('access_token', path='/')
        response.delete_cookie('user_nombre', path='/')
        response.delete_cookie('user_rol', path='/')
        return response
    
    @auth_bp.route('/me', methods=['GET'])
    @jwt_required()
    def get_current_user():
        user_id = get_jwt_identity()
        user = find_user_by_id(user_id)
        
        if not user:
            return jsonify({'error': 'Usuario no encontrado'}), 404
        
        return jsonify({
            'id': str(user['_id']),
            'nombre': user['nombre'],
            'email': user['email'],
            'rol': user['rol']
        })
    
    return auth_bp