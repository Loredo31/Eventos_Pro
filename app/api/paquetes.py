from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required, get_jwt
from functools import wraps

paquetes_bp = Blueprint('paquetes', __name__, url_prefix='/api/paquetes')

def admin_required(f):
    @wraps(f)
    @jwt_required()
    def decorated_function(*args, **kwargs):
        claims = get_jwt()
        if claims.get('rol') != 'admin':
            return jsonify({'error': 'Se requieren permisos de administrador'}), 403
        return f(*args, **kwargs)
    return decorated_function

def init_paquetes_routes(mongo):
    """Inicializar rutas de paquetes con la conexión MongoDB"""
    
    def calcular_precio_total(servicios_ids):
        servicios = mongo.db.servicios.find({'id': {'$in': servicios_ids}, 'activo': True})
        total = sum(s.get('precio', 0) for s in servicios)
        return total
    
    @paquetes_bp.route('/', methods=['GET'])
    def obtener_paquetes():
        """Obtener todos los paquetes"""
        paquetes = list(mongo.db.paquetes.find({'activo': True}, {'_id': 0}))
        
        for paquete in paquetes:
            servicios_ids = paquete.get('servicios_ids', [])
            servicios = list(mongo.db.servicios.find(
                {'id': {'$in': servicios_ids}, 'activo': True},
                {'_id': 0, 'id': 1, 'nombre': 1, 'descripcion': 1, 'precio': 1}
            ))
            paquete['servicios_detalle'] = servicios
        
        return jsonify(paquetes), 200

    @paquetes_bp.route('/<int:paquete_id>', methods=['GET'])
    def obtener_paquete(paquete_id):
        """Obtener un paquete por ID"""
        paquete = mongo.db.paquetes.find_one({'id': paquete_id, 'activo': True}, {'_id': 0})
        
        if not paquete:
            return jsonify({'error': 'Paquete no encontrado'}), 404
        
        servicios_ids = paquete.get('servicios_ids', [])
        servicios = list(mongo.db.servicios.find(
            {'id': {'$in': servicios_ids}, 'activo': True},
            {'_id': 0, 'id': 1, 'nombre': 1, 'descripcion': 1, 'precio': 1}
        ))
        paquete['servicios_detalle'] = servicios
        
        return jsonify(paquete), 200

    @paquetes_bp.route('/', methods=['POST'])
    @admin_required
    def crear_paquete():
        """Crear un nuevo paquete (solo admin)"""
        data = request.get_json()
        
        required_fields = ['nombre', 'descripcion', 'servicios_ids']
        for field in required_fields:
            if field not in data:
                return jsonify({'error': f'Campo {field} es requerido'}), 400
        
        servicios_ids = data['servicios_ids']
        servicios_existentes = list(mongo.db.servicios.find({'id': {'$in': servicios_ids}, 'activo': True}))
        
        if len(servicios_existentes) != len(servicios_ids):
            return jsonify({'error': 'Uno o más servicios no existen'}), 400
        
        precio_total = calcular_precio_total(servicios_ids)
        
        ultimo_paquete = mongo.db.paquetes.find_one(sort=[('id', -1)])
        nuevo_id = (ultimo_paquete.get('id') if ultimo_paquete else 0) + 1
        
        nuevo_paquete = {
            'id': nuevo_id,
            'nombre': data['nombre'],
            'descripcion': data['descripcion'],
            'servicios_ids': servicios_ids,
            'precio_total': precio_total,
            'activo': True
        }
        
        result = mongo.db.paquetes.insert_one(nuevo_paquete)
        nuevo_paquete['_id'] = str(result.inserted_id)
        
        return jsonify({'success': True, 'paquete': nuevo_paquete}), 201

    @paquetes_bp.route('/<int:paquete_id>', methods=['PUT'])
    @admin_required
    def actualizar_paquete(paquete_id):
        """Actualizar un paquete (solo admin)"""
        data = request.get_json()
        
        campos_permitidos = ['nombre', 'descripcion', 'servicios_ids', 'activo']
        update_data = {}
        
        for campo in campos_permitidos:
            if campo in data:
                update_data[campo] = data[campo]
        
        if not update_data:
            return jsonify({'error': 'No hay campos válidos para actualizar'}), 400
        
        if 'servicios_ids' in update_data:
            servicios_ids = update_data['servicios_ids']
            servicios_existentes = list(mongo.db.servicios.find({'id': {'$in': servicios_ids}, 'activo': True}))
            
            if len(servicios_existentes) != len(servicios_ids):
                return jsonify({'error': 'Uno o más servicios no existen'}), 400
            
            update_data['precio_total'] = calcular_precio_total(servicios_ids)
        
        result = mongo.db.paquetes.update_one(
            {'id': paquete_id},
            {'$set': update_data}
        )
        
        if result.matched_count == 0:
            return jsonify({'error': 'Paquete no encontrado'}), 404
        
        return jsonify({'success': True, 'message': 'Paquete actualizado'}), 200

    @paquetes_bp.route('/<int:paquete_id>', methods=['DELETE'])
    @admin_required
    def eliminar_paquete(paquete_id):
        """Eliminar un paquete (soft delete - solo admin)"""
        result = mongo.db.paquetes.update_one(
            {'id': paquete_id},
            {'$set': {'activo': False}}
        )
        
        if result.matched_count == 0:
            return jsonify({'error': 'Paquete no encontrado'}), 404
        
        return jsonify({'success': True, 'message': 'Paquete eliminado'}), 200
    
    return paquetes_bp