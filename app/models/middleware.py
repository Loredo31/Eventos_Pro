from functools import wraps
from flask import request, jsonify, redirect, url_for
from flask_jwt_extended import verify_jwt_in_request, get_jwt, get_jwt_identity
from flask import current_app

def login_required(f):
    """Decorador para rutas que requieren autenticación"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Verificar si hay token en cookies o header
        access_token = request.cookies.get('access_token')
        
        if access_token:
            # Poner token en el header para que JWT lo reconozca
            request.headers.environ['HTTP_AUTHORIZATION'] = f'Bearer {access_token}'
        
        try:
            verify_jwt_in_request()
            return f(*args, **kwargs)
        except Exception as e:
            # Si es petición API, devolver JSON
            if request.path.startswith('/api/'):
                return jsonify({'error': 'No autenticado'}), 401
            # Si es página web, redirigir a login
            return redirect(url_for('auth.login'))
    
    return decorated_function

def role_required(*roles):
    """Decorador para rutas que requieren roles específicos"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # Verificar autenticación primero
            access_token = request.cookies.get('access_token')
            if access_token:
                request.headers.environ['HTTP_AUTHORIZATION'] = f'Bearer {access_token}'
            
            try:
                verify_jwt_in_request()
                claims = get_jwt()
                user_rol = claims.get('rol', 'cliente')
                
                if user_rol not in roles:
                    # Si es petición API
                    if request.path.startswith('/api/'):
                        return jsonify({'error': 'No autorizado'}), 403
                    # Si es página web
                    return render_template('error.html', 
                                         error='No tienes permiso para acceder a esta página'), 403
                
                return f(*args, **kwargs)
            except Exception as e:
                if request.path.startswith('/api/'):
                    return jsonify({'error': 'No autenticado'}), 401
                return redirect(url_for('auth.login'))
        
        return decorated_function
    return decorator