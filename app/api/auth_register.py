from flask import Blueprint, jsonify, request, session
from werkzeug.security import generate_password_hash
import re

# Crear blueprint para registro
register_bp = Blueprint('auth_register', __name__, url_prefix='/api/auth')

def init_register_routes(mongo):
    """Inicializar rutas de registro con la conexión MongoDB"""
    
    @register_bp.route('/register', methods=['POST'])
    def register():
        """Registrar un nuevo usuario"""
        try:
            data = request.get_json()
            
            # Validar datos requeridos
            if not data or not data.get('nombre') or not data.get('email') or not data.get('password'):
                return jsonify({
                    'success': False,
                    'error': 'Todos los campos son requeridos'
                }), 400
            
            nombre = data.get('nombre')
            email = data.get('email').lower()
            password = data.get('password')
            
            # Validar formato de email
            email_regex = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
            if not re.match(email_regex, email):
                return jsonify({
                    'success': False,
                    'error': 'Formato de correo inválido'
                }), 400
            
            # Validar longitud de contraseña
            if len(password) < 6:
                return jsonify({
                    'success': False,
                    'error': 'La contraseña debe tener al menos 6 caracteres'
                }), 400
            
            # Verificar si el usuario ya existe
            existing_user = mongo.db.users.find_one({'email': email})
            if existing_user:
                return jsonify({
                    'success': False,
                    'error': 'El correo ya está registrado'
                }), 400
            
            # Crear nuevo usuario
            hashed_password = generate_password_hash(password)
            
            user_data = {
                'nombre': nombre,
                'email': email,
                'password': hashed_password,
                'rol': 'cliente',  # Rol por defecto (usando 'rol' como en tu app)
                'activo': True,
                'created_at': mongo.db.command('serverStatus')['localTime']
            }
            
            # Insertar en la base de datos
            result = mongo.db.users.insert_one(user_data)
            
            # Crear sesión automáticamente después del registro
            user = mongo.db.users.find_one({'_id': result.inserted_id})
            
            # Crear access_token JWT para el nuevo usuario
            from flask_jwt_extended import create_access_token
            additional_claims = {'rol': user.get('rol', 'cliente')}
            access_token = create_access_token(
                identity=str(user['_id']),
                additional_claims=additional_claims
            )
            
            # Crear respuesta con cookie
            response = jsonify({
                'success': True,
                'message': 'Usuario registrado exitosamente',
                'user': {
                    'id': str(user['_id']),
                    'nombre': user['nombre'],
                    'email': user['email'],
                    'rol': user.get('rol', 'cliente')
                }
            })
            
            # Establecer cookies
            response.set_cookie('access_token', access_token, httponly=True, max_age=86400)
            response.set_cookie('user_nombre', user['nombre'], max_age=86400)
            response.set_cookie('user_rol', user.get('rol', 'cliente'), max_age=86400)
            
            return response, 201
            
        except Exception as e:
            return jsonify({
                'success': False,
                'error': f'Error en el servidor: {str(e)}'
            }), 500
    
    return register_bp