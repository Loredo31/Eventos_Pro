from flask import Blueprint, jsonify, request, session
from flask_jwt_extended import create_access_token
from werkzeug.security import check_password_hash
from bson import ObjectId

login_bp = Blueprint('auth_login', __name__, url_prefix='/api/auth')

def init_login_routes(mongo):
    """Inicializar rutas de login con la conexión MongoDB"""

    @login_bp.route('/login', methods=['POST'])
    def login():
        """Iniciar sesión"""
        try:
            data = request.get_json()
            if not data or not data.get('email') or not data.get('password'):
                return jsonify({
                    'success': False,
                    'error': 'Correo y contraseña son requeridos'
                }), 400

            email = data.get('email').lower()
            password = data.get('password')

            user = mongo.db.users.find_one({'email': email, 'activo': True})
            if not user:
                return jsonify({
                    'success': False,
                    'error': 'Credenciales inválidas'
                }), 401

            if not check_password_hash(user['password'], password):
                return jsonify({
                    'success': False,
                    'error': 'Credenciales inválidas'
                }), 401

            # Obtener user_id (prioriza campo numérico 'id', si no, usa string de _id)
            user_id_value = user.get('id')
            if user_id_value is None:
                user_id_value = str(user['_id'])

            additional_claims = {
                'rol': user.get('rol', 'cliente'),
                'user_id': user_id_value
            }

            access_token = create_access_token(
                identity=str(user['_id']),
                additional_claims=additional_claims
            )

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

            # Establecer cookies (httponly=False para que JavaScript pueda leer)
            response.set_cookie('access_token', access_token,
                                httponly=False,
                                max_age=86400,
                                path='/',
                                samesite='Lax')
            response.set_cookie('user_nombre', user['nombre'],
                                max_age=86400, path='/')
            response.set_cookie('user_rol', user.get('rol', 'cliente'),
                                max_age=86400, path='/')

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
            response = jsonify({
                'success': True,
                'message': 'Sesión cerrada exitosamente'
            })
            response.delete_cookie('access_token', path='/')
            response.delete_cookie('user_nombre', path='/')
            response.delete_cookie('user_rol', path='/')
            session.clear()
            return response, 200
        except Exception as e:
            return jsonify({
                'success': False,
                'error': f'Error al cerrar sesión: {str(e)}'
            }), 500

    return login_bp