from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required, get_jwt
from functools import wraps
from datetime import datetime
from bson import ObjectId

eventos_bp = Blueprint('eventos', __name__, url_prefix='/api/eventos')

def admin_required(f):
    @wraps(f)
    @jwt_required()
    def decorated_function(*args, **kwargs):
        claims = get_jwt()
        if claims.get('rol') != 'admin':
            return jsonify({'error': 'Se requieren permisos de administrador'}), 403
        return f(*args, **kwargs)
    return decorated_function

def init_eventos_routes(mongo):
    """Inicializar rutas de eventos con la conexión MongoDB"""

    def obtener_info_usuario(user_id):
        """Buscar nombre y email del usuario por su user_id numérico o _id string"""
        usuario = None
        # Primero intenta buscar por el campo numérico 'id'
        if isinstance(user_id, int) or (isinstance(user_id, str) and user_id.isdigit()):
            usuario = mongo.db.users.find_one({'id': int(user_id)}, {'nombre': 1, 'email': 1})
        # Si no lo encontró, intenta por _id (ObjectId)
        if not usuario and isinstance(user_id, str):
            try:
                usuario = mongo.db.users.find_one({'_id': ObjectId(user_id)}, {'nombre': 1, 'email': 1})
            except Exception:
                pass
        if usuario:
            return {
                'nombre': usuario.get('nombre'),
                'email': usuario.get('email')
            }
        return {'nombre': None, 'email': None}

    @eventos_bp.route('/', methods=['POST'])
    @jwt_required()
    def crear_evento():
        """Crear una nueva solicitud de evento (usuario autenticado)"""
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No se enviaron datos'}), 400

        required_fields = ['fecha_evento', 'tipo_evento']
        for field in required_fields:
            if field not in data:
                return jsonify({'error': f'El campo {field} es obligatorio'}), 400

        tipo = data.get('tipo')
        if tipo not in ['paquete', 'servicios']:
            return jsonify({'error': 'El campo "tipo" debe ser "paquete" o "servicios"'}), 400

        claims = get_jwt()
        user_id = claims.get('user_id')

        # Obtener nombre y email del usuario que hace la solicitud
        info_usuario = obtener_info_usuario(user_id)

        evento = {
            'user_id': user_id,
            'user_nombre': info_usuario['nombre'],   # ← nombre del solicitante
            'user_email': info_usuario['email'],     # ← correo del solicitante
            'fecha_evento': data['fecha_evento'],
            'tipo_evento': data['tipo_evento'],
            'lugar': data.get('lugar'),
            'comentarios': data.get('comentarios'),
            'estado': None,
            'comentario_rechazo': None,
            'created_at': datetime.utcnow(),
            'updated_at': datetime.utcnow()
        }

        if tipo == 'paquete':
            paquete_id = data.get('paquete_id')
            if not paquete_id:
                return jsonify({'error': 'Se requiere paquete_id'}), 400
            paquete = mongo.db.paquetes.find_one({'id': paquete_id, 'activo': True})
            if not paquete:
                return jsonify({'error': 'Paquete no encontrado'}), 404
            evento['paquete_id'] = paquete_id
        else:  # servicios
            servicios_ids = data.get('servicios_ids', [])
            if not servicios_ids:
                return jsonify({'error': 'Se requiere lista de servicios_ids'}), 400
            servicios = list(mongo.db.servicios.find({'id': {'$in': servicios_ids}, 'activo': True}))
            if len(servicios) != len(servicios_ids):
                return jsonify({'error': 'Uno o más servicios no existen'}), 400
            evento['servicios_ids'] = servicios_ids

        ultimo_evento = mongo.db.eventos.find_one(sort=[('id', -1)])
        nuevo_id = (ultimo_evento.get('id') if ultimo_evento else 0) + 1
        evento['id'] = nuevo_id

        result = mongo.db.eventos.insert_one(evento)
        evento['_id'] = str(result.inserted_id)

        return jsonify({'success': True, 'evento': evento}), 201

    def enriquecer_evento(evento):
        """Agrega paquete/servicios y nombre+email del usuario al evento"""
        if 'paquete_id' in evento:
            paquete = mongo.db.paquetes.find_one({'id': evento['paquete_id']}, {'_id': 0})
            evento['paquete'] = paquete
        if 'servicios_ids' in evento:
            servicios = list(mongo.db.servicios.find({'id': {'$in': evento['servicios_ids']}}, {'_id': 0}))
            evento['servicios'] = servicios

        # Si el evento ya tiene nombre y email guardados, los usamos directamente.
        # Si no (eventos creados antes de este cambio), hacemos el lookup como fallback.
        if not evento.get('user_nombre') or not evento.get('user_email'):
            info_usuario = obtener_info_usuario(evento.get('user_id'))
            evento['user_nombre'] = evento.get('user_nombre') or info_usuario['nombre']
            evento['user_email'] = evento.get('user_email') or info_usuario['email']

        return evento

    @eventos_bp.route('/', methods=['GET'])
    @admin_required
    def listar_eventos_pendientes():
        """Obtener todas las solicitudes pendientes (estado = null)"""
        eventos = list(mongo.db.eventos.find({'estado': None}, {'_id': 0}))
        eventos = [enriquecer_evento(e) for e in eventos]
        return jsonify(eventos), 200

    @eventos_bp.route('/todos', methods=['GET'])
    @admin_required
    def listar_todos_eventos():
        """Obtener todas las solicitudes (incluyendo aprobadas/rechazadas)"""
        eventos = list(mongo.db.eventos.find({}, {'_id': 0}).sort('created_at', -1))
        eventos = [enriquecer_evento(e) for e in eventos]
        return jsonify(eventos), 200

    @eventos_bp.route('/<int:evento_id>', methods=['PUT'])
    @admin_required
    def actualizar_evento(evento_id):
        """Aprobar o rechazar una solicitud y enviar correo al cliente"""
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No se enviaron datos'}), 400

        nuevo_estado = data.get('estado')
        if nuevo_estado not in [True, False]:
            return jsonify({'error': 'El campo "estado" debe ser true o false'}), 400

        update_data = {
            'estado':     nuevo_estado,
            'updated_at': datetime.utcnow()
        }

        if nuevo_estado is False:
            motivo = data.get('comentario_rechazo', '').strip()
            if not motivo:
                return jsonify({'error': 'Se requiere comentario de rechazo'}), 400
            update_data['comentario_rechazo'] = motivo
        else:
            update_data['comentario_rechazo'] = None

        result = mongo.db.eventos.update_one(
            {'id': evento_id},
            {'$set': update_data}
        )

        if result.matched_count == 0:
            return jsonify({'error': 'Evento no encontrado'}), 404

        # Obtener el evento completo para el correo
        evento_actualizado = mongo.db.eventos.find_one({'id': evento_id}, {'_id': 0})
        evento_actualizado = enriquecer_evento(evento_actualizado)

        # Enviar correo según la decisión
        from api.email_service import correo_aceptacion, correo_rechazo
        if nuevo_estado is True:
            resultado_correo = correo_aceptacion(evento_actualizado)
        else:
            resultado_correo = correo_rechazo(evento_actualizado, motivo)

        return jsonify({
            'success':        True,
            'message':        'Solicitud actualizada',
            'correo_enviado': resultado_correo.get('success', False),
            'evento':         evento_actualizado
        }), 200
    return eventos_bp  