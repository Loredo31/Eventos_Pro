from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required, get_jwt
from functools import wraps
from datetime import datetime
from bson import ObjectId

solicitudes_bp = Blueprint('solicitudes', __name__, url_prefix='/api/solicitudes')

def admin_required(f):
    @wraps(f)
    @jwt_required()
    def decorated_function(*args, **kwargs):
        claims = get_jwt()
        if claims.get('rol') != 'admin':
            return jsonify({'error': 'Se requieren permisos de administrador'}), 403
        return f(*args, **kwargs)
    return decorated_function


def init_solicitudes_routes(mongo):

    @solicitudes_bp.route('/', methods=['GET'])
    @admin_required
    def obtener_solicitudes():
        solicitudes = list(mongo.db.solicitudes.find({}, {'_id': 1, 'nombre_cliente': 1,
            'email_cliente': 1, 'telefono': 1, 'paquete_id': 1, 'fecha_evento': 1,
            'mensaje': 1, 'estado': 1, 'fecha_solicitud': 1, 'motivo_rechazo': 1}))
        for s in solicitudes:
            s['_id'] = str(s['_id'])
            if s.get('paquete_id'):
                paquete = mongo.db.paquetes.find_one({'id': s['paquete_id']}, {'nombre': 1, '_id': 0})
                s['paquete_nombre'] = paquete.get('nombre', 'Sin paquete') if paquete else 'Sin paquete'
        return jsonify(solicitudes), 200

    @solicitudes_bp.route('/<solicitud_id>', methods=['GET'])
    @admin_required
    def obtener_solicitud(solicitud_id):
        try:
            s = mongo.db.solicitudes.find_one({'_id': ObjectId(solicitud_id)})
        except Exception:
            return jsonify({'error': 'ID inválido'}), 400
        if not s:
            return jsonify({'error': 'Solicitud no encontrada'}), 404
        s['_id'] = str(s['_id'])
        if s.get('paquete_id'):
            paquete = mongo.db.paquetes.find_one({'id': s['paquete_id']}, {'_id': 0})
            if paquete:
                servicios_ids = paquete.get('servicios_ids', [])
                servicios = list(mongo.db.servicios.find(
                    {'id': {'$in': servicios_ids}, 'activo': True},
                    {'_id': 0, 'nombre': 1, 'precio': 1}
                ))
                paquete['servicios_detalle'] = servicios
                s['paquete_detalle'] = paquete
        return jsonify(s), 200

    @solicitudes_bp.route('/', methods=['POST'])
    @jwt_required()
    def crear_solicitud():
        data = request.get_json()
        required = ['nombre_cliente', 'email_cliente', 'telefono', 'paquete_id', 'fecha_evento']
        for campo in required:
            if not data or not data.get(campo):
                return jsonify({'error': f'Campo {campo} es requerido'}), 400
        paquete = mongo.db.paquetes.find_one({'id': data['paquete_id'], 'activo': True})
        if not paquete:
            return jsonify({'error': 'Paquete no encontrado'}), 404
        nueva = {
            'nombre_cliente':  data['nombre_cliente'],
            'email_cliente':   data['email_cliente'],
            'telefono':        data['telefono'],
            'paquete_id':      data['paquete_id'],
            'fecha_evento':    data['fecha_evento'],
            'mensaje':         data.get('mensaje', ''),
            'estado':          'pendiente',
            'fecha_solicitud': datetime.utcnow().isoformat(),
            'motivo_rechazo':  None
        }
        result = mongo.db.solicitudes.insert_one(nueva)
        return jsonify({'success': True, 'id': str(result.inserted_id)}), 201

    @solicitudes_bp.route('/<solicitud_id>/aceptar', methods=['PUT'])
    @admin_required
    def aceptar_solicitud(solicitud_id):
        try:
            sol = mongo.db.solicitudes.find_one({'_id': ObjectId(solicitud_id)})
        except Exception:
            return jsonify({'error': 'ID inválido'}), 400
        if not sol:
            return jsonify({'error': 'Solicitud no encontrada'}), 404

        mongo.db.solicitudes.update_one(
            {'_id': ObjectId(solicitud_id)},
            {'$set': {'estado': True, 'motivo_rechazo': None}}
        )

        paquete = mongo.db.paquetes.find_one({'id': sol.get('paquete_id')}, {'_id': 0})
        paquete_nombre = paquete.get('nombre', 'Paquete contratado') if paquete else 'Paquete contratado'
        precio = paquete.get('precio_total', 0) if paquete else 0

        from api.email_service import enviar_correo
        html_contrato = f"""
        <html><body style="font-family:Arial,sans-serif;background:#f4f4f4;padding:20px;">
          <div style="max-width:650px;margin:auto;background:#fff;border-radius:8px;padding:30px;">
            <div style="text-align:center;margin-bottom:24px;">
              <h1 style="color:#1565C0;font-size:26px;">📸 Eventos Pro</h1>
              <p style="color:#888;font-size:13px;">Contrato de servicios fotográficos</p>
            </div>
            <h2 style="color:#333;border-bottom:2px solid #BBDEFB;padding-bottom:10px;">
              ¡Tu solicitud fue aceptada, {sol['nombre_cliente']}!
            </h2>
            <p style="margin:16px 0;">Nos da mucho gusto confirmar la contratación de nuestros servicios para tu evento.</p>
            <table style="width:100%;border-collapse:collapse;margin:20px 0;">
              <tr style="background:#E3F2FD;">
                <td style="padding:10px;font-weight:bold;width:40%;">Cliente</td>
                <td style="padding:10px;">{sol['nombre_cliente']}</td>
              </tr>
              <tr>
                <td style="padding:10px;font-weight:bold;">Correo</td>
                <td style="padding:10px;">{sol['email_cliente']}</td>
              </tr>
              <tr style="background:#E3F2FD;">
                <td style="padding:10px;font-weight:bold;">Teléfono</td>
                <td style="padding:10px;">{sol['telefono']}</td>
              </tr>
              <tr>
                <td style="padding:10px;font-weight:bold;">Paquete</td>
                <td style="padding:10px;">{paquete_nombre}</td>
              </tr>
              <tr style="background:#E3F2FD;">
                <td style="padding:10px;font-weight:bold;">Fecha del evento</td>
                <td style="padding:10px;">{sol['fecha_evento']}</td>
              </tr>
              <tr>
                <td style="padding:10px;font-weight:bold;">Inversión total</td>
                <td style="padding:10px;color:#1565C0;font-weight:bold;">${precio:,} MXN</td>
              </tr>
            </table>
            <div style="background:#E8F5E9;border-left:4px solid #4CAF50;padding:14px;border-radius:4px;margin:20px 0;">
              <strong>Próximo paso:</strong> Nuestro equipo se pondrá en contacto contigo en las próximas 24 horas.
            </div>
            <p style="color:#888;font-size:12px;margin-top:30px;text-align:center;">
              Eventos Pro • eventospro37@gmail.com
            </p>
          </div>
        </body></html>
        """
        resultado_correo = enviar_correo(
            sol['email_cliente'],
            f"✅ Contrato confirmado - {paquete_nombre} | Eventos Pro",
            html_contrato,
            f"Hola {sol['nombre_cliente']}, tu solicitud fue aceptada. Paquete: {paquete_nombre}, Fecha: {sol['fecha_evento']}."
        )
        return jsonify({'success': True, 'message': 'Solicitud aceptada', 'correo_enviado': resultado_correo['success']}), 200

    @solicitudes_bp.route('/<solicitud_id>/rechazar', methods=['PUT'])
    @admin_required
    def rechazar_solicitud(solicitud_id):
        data = request.get_json()
        if not data or not data.get('motivo'):
            return jsonify({'error': 'El motivo de rechazo es requerido'}), 400
        try:
            sol = mongo.db.solicitudes.find_one({'_id': ObjectId(solicitud_id)})
        except Exception:
            return jsonify({'error': 'ID inválido'}), 400
        if not sol:
            return jsonify({'error': 'Solicitud no encontrada'}), 404

        mongo.db.solicitudes.update_one(
            {'_id': ObjectId(solicitud_id)},
            {'$set': {'estado': False, 'motivo_rechazo': data['motivo']}}
        )

        from api.email_service import enviar_correo
        html_rechazo = f"""
        <html><body style="font-family:Arial,sans-serif;background:#f4f4f4;padding:20px;">
          <div style="max-width:600px;margin:auto;background:#fff;border-radius:8px;padding:30px;">
            <h2 style="color:#C62828;">Actualización sobre tu solicitud</h2>
            <p>Hola <strong>{sol['nombre_cliente']}</strong>,</p>
            <p>Lamentamos informarte que en esta ocasión no podemos proceder con tu solicitud.</p>
            <div style="background:#FFEBEE;border-left:4px solid #E53935;padding:14px;border-radius:4px;margin:20px 0;">
              <strong>Motivo:</strong> {data['motivo']}
            </div>
            <p>Si tienes dudas, no dudes en contactarnos.</p>
            <p style="color:#888;font-size:12px;margin-top:30px;">Eventos Pro • eventospro37@gmail.com</p>
          </div>
        </body></html>
        """
        enviar_correo(sol['email_cliente'], "Actualización sobre tu solicitud - Eventos Pro", html_rechazo)
        return jsonify({'success': True, 'message': 'Solicitud rechazada'}), 200

    @solicitudes_bp.route('/<solicitud_id>', methods=['DELETE'])
    @admin_required
    def eliminar_solicitud(solicitud_id):
        try:
            result = mongo.db.solicitudes.delete_one({'_id': ObjectId(solicitud_id)})
        except Exception:
            return jsonify({'error': 'ID inválido'}), 400
        if result.deleted_count == 0:
            return jsonify({'error': 'Solicitud no encontrada'}), 404
        return jsonify({'success': True, 'message': 'Solicitud eliminada'}), 200

    return solicitudes_bp