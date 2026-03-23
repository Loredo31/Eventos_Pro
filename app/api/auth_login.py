from flask import Blueprint, jsonify, request, session
from werkzeug.security import check_password_hash
from bson import ObjectId

# Crear blueprint para login
login_bp = Blueprint('auth_login', __name__, url_prefix='/api/auth')

def init_login_routes(mongo):
    """Inicializar rutas de login con la conexión MongoDB"""
    
    @login_bp.route('/login', methods=['POST'])
    def login():
        """Iniciar sesión"""
        try:
            data = request.get_json()
            
            # Validar datos requeridos
            if not data or not data.get('email') or not data.get('password'):
                return jsonify({
                    'success': False,
                    'error': 'Correo y contraseña son requeridos'
                }), 400
            
            email = data.get('email').lower()
            password = data.get('password')
            
            # Buscar usuario en la base de datos
            user = mongo.db.users.find_one({'email': email, 'activo': True})
            
            if not user:
                return jsonify({
                    'success': False,
                    'error': 'Credenciales inválidas'
                }), 401
            
            # Verificar contraseña
            if not check_password_hash(user['password'], password):
                return jsonify({
                    'success': False,
                    'error': 'Credenciales inválidas'
                }), 401
            
            # Crear access_token JWT
            from flask_jwt_extended import create_access_token
            additional_claims = {'rol': user.get('rol', 'cliente')}
            access_token = create_access_token(
                identity=str(user['_id']),
                additional_claims=additional_claims
            )
            
            # Crear respuesta con cookies
            response = jsonify({
                'success': True,
                'message': 'Inicio de sesión exitoso',
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
            
            return response, 200
            
        except Exception as e:
            return jsonify({
                'success': False,
                'error': f'Error en el servidor: {str(e)}'
            }), 500
    
    @login_bp.route('/logout', methods=['POST'])
    def logout():
        """Cerrar sesión"""
        try:
            # Crear respuesta limpiando cookies
            response = jsonify({
                'success': True,
                'message': 'Sesión cerrada exitosamente'
            })
            
            # Eliminar cookies
            response.delete_cookie('access_token', path='/')
            response.delete_cookie('user_nombre', path='/')
            response.delete_cookie('user_rol', path='/')
            
            # Limpiar sesión
            session.clear()
            
            return response, 200
        except Exception as e:
            return jsonify({
                'success': False,
                'error': f'Error al cerrar sesión: {str(e)}'
            }), 500
    
    return login_bp