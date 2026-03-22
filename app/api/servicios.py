from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required, get_jwt
from functools import wraps

# Crear blueprint para servicios
servicios_bp = Blueprint('servicios', __name__, url_prefix='/api/servicios')

# Decorador para verificar rol de admin
def admin_required(f):
    @wraps(f)
    @jwt_required()
    def decorated_function(*args, **kwargs):
        claims = get_jwt()
        if claims.get('rol') != 'admin':
            return jsonify({'error': 'Se requieren permisos de administrador'}), 403
        return f(*args, **kwargs)
    return decorated_function

def init_servicios_routes(mongo):
    """Inicializar rutas de servicios con la conexión MongoDB"""
    
    @servicios_bp.route('/', methods=['GET'])
    def obtener_servicios():
        """Obtener todos los servicios"""
        servicios = list(mongo.db.servicios.find({'activo': True}, {'_id': 0}))
        return jsonify(servicios), 200

    @servicios_bp.route('/<int:servicio_id>', methods=['GET'])
    def obtener_servicio(servicio_id):
        """Obtener un servicio por ID"""
        servicio = mongo.db.servicios.find_one({'id': servicio_id, 'activo': True}, {'_id': 0})
        if not servicio:
            return jsonify({'error': 'Servicio no encontrado'}), 404
        return jsonify(servicio), 200

    @servicios_bp.route('/', methods=['POST'])
    @admin_required
    def crear_servicio():
        """Crear un nuevo servicio (solo admin)"""
        data = request.get_json()
        
        required_fields = ['nombre', 'descripcion', 'precio']
        for field in required_fields:
            if field not in data:
                return jsonify({'error': f'Campo {field} es requerido'}), 400
        
        ultimo_servicio = mongo.db.servicios.find_one(sort=[('id', -1)])
        nuevo_id = (ultimo_servicio.get('id') if ultimo_servicio else 0) + 1
        
        nuevo_servicio = {
            'id': nuevo_id,
            'nombre': data['nombre'],
            'descripcion': data['descripcion'],
            'precio': data['precio'],
            'activo': True
        }
        
        result = mongo.db.servicios.insert_one(nuevo_servicio)
        nuevo_servicio['_id'] = str(result.inserted_id)
        
        return jsonify({'success': True, 'servicio': nuevo_servicio}), 201

    @servicios_bp.route('/<int:servicio_id>', methods=['PUT'])
    @admin_required
    def actualizar_servicio(servicio_id):
        """Actualizar un servicio (solo admin)"""
        data = request.get_json()
        
        campos_permitidos = ['nombre', 'descripcion', 'precio', 'activo']
        update_data = {k: v for k, v in data.items() if k in campos_permitidos}
        
        if not update_data:
            return jsonify({'error': 'No hay campos válidos para actualizar'}), 400
        
        result = mongo.db.servicios.update_one(
            {'id': servicio_id},
            {'$set': update_data}
        )
        
        if result.matched_count == 0:
            return jsonify({'error': 'Servicio no encontrado'}), 404
        
        return jsonify({'success': True, 'message': 'Servicio actualizado'}), 200

    @servicios_bp.route('/<int:servicio_id>', methods=['DELETE'])
    @admin_required
    def eliminar_servicio(servicio_id):
        """Eliminar un servicio (soft delete - solo admin)"""
        result = mongo.db.servicios.update_one(
            {'id': servicio_id},
            {'$set': {'activo': False}}
        )
        
        if result.matched_count == 0:
            return jsonify({'error': 'Servicio no encontrado'}), 404
        
        return jsonify({'success': True, 'message': 'Servicio eliminado'}), 200
    
    return servicios_bp