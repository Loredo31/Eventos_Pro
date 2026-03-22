from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required, get_jwt
from functools import wraps
from bson import ObjectId

# Crear blueprint para endpoints de admin
admin_api = Blueprint('admin_api', __name__, url_prefix='/api/admin')

# Decorador para verificar rol de admin
def admin_required(f):
    """Decorador que verifica que el usuario sea administrador"""
    @wraps(f)
    @jwt_required()
    def decorated_function(*args, **kwargs):
        claims = get_jwt()
        if claims.get('rol') != 'admin':
            return jsonify({'error': 'Se requieren permisos de administrador'}), 403
        return f(*args, **kwargs)
    return decorated_function

# ============================================
# ENDPOINTS PARA PAQUETES
# ============================================

@admin_api.route('/paquetes', methods=['GET'])
@admin_required
def obtener_paquetes():
    """Obtener todos los paquetes"""
    from app import mongo
    paquetes = list(mongo.db.paquetes.find({}, {'_id': 0}))
    return jsonify(paquetes), 200

@admin_api.route('/paquetes/insert', methods=['POST'])
@admin_required
def insertar_paquetes():
    """Insertar múltiples paquetes"""
    from app import mongo
    data = request.get_json()
    
    if not data:
        return jsonify({'error': 'Se requiere un array de paquetes'}), 400
    
    # Eliminar paquetes existentes
    mongo.db.paquetes.delete_many({})
    
    # Insertar nuevos paquetes
    result = mongo.db.paquetes.insert_many(data)
    
    return jsonify({
        'success': True,
        'message': f'{len(result.inserted_ids)} paquetes insertados'
    }), 201

@admin_api.route('/paquetes/<int:paquete_id>', methods=['PUT'])
@admin_required
def actualizar_paquete(paquete_id):
    """Actualizar un paquete por ID"""
    from app import mongo
    data = request.get_json()
    
    result = mongo.db.paquetes.update_one(
        {'id': paquete_id},
        {'$set': data}
    )
    
    if result.modified_count:
        return jsonify({'success': True, 'message': 'Paquete actualizado'})
    return jsonify({'error': 'Paquete no encontrado'}), 404

@admin_api.route('/paquetes/<int:paquete_id>', methods=['DELETE'])
@admin_required
def eliminar_paquete(paquete_id):
    """Eliminar un paquete por ID"""
    from app import mongo
    result = mongo.db.paquetes.delete_one({'id': paquete_id})
    
    if result.deleted_count:
        return jsonify({'success': True, 'message': 'Paquete eliminado'})
    return jsonify({'error': 'Paquete no encontrado'}), 404

# ============================================
# ENDPOINTS PARA SERVICIOS
# ============================================

@admin_api.route('/servicios', methods=['GET'])
@admin_required
def obtener_servicios():
    """Obtener todos los servicios"""
    from app import mongo
    servicios = list(mongo.db.servicios.find({}, {'_id': 0}))
    return jsonify(servicios), 200

@admin_api.route('/servicios/insert', methods=['POST'])
@admin_required
def insertar_servicios():
    """Insertar múltiples servicios"""
    from app import mongo
    data = request.get_json()
    
    if not data:
        return jsonify({'error': 'Se requiere un array de servicios'}), 400
    
    # Eliminar servicios existentes
    mongo.db.servicios.delete_many({})
    
    # Insertar nuevos servicios
    result = mongo.db.servicios.insert_many(data)
    
    return jsonify({
        'success': True,
        'message': f'{len(result.inserted_ids)} servicios insertados'
    }), 201

@admin_api.route('/servicios/<int:servicio_id>', methods=['PUT'])
@admin_required
def actualizar_servicio(servicio_id):
    """Actualizar un servicio por ID"""
    from app import mongo
    data = request.get_json()
    
    result = mongo.db.servicios.update_one(
        {'id': servicio_id},
        {'$set': data}
    )
    
    if result.modified_count:
        return jsonify({'success': True, 'message': 'Servicio actualizado'})
    return jsonify({'error': 'Servicio no encontrado'}), 404

@admin_api.route('/servicios/<int:servicio_id>', methods=['DELETE'])
@admin_required
def eliminar_servicio(servicio_id):
    """Eliminar un servicio por ID"""
    from app import mongo
    result = mongo.db.servicios.delete_one({'id': servicio_id})
    
    if result.deleted_count:
        return jsonify({'success': True, 'message': 'Servicio eliminado'})
    return jsonify({'error': 'Servicio no encontrado'}), 404