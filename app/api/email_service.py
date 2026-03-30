import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required, get_jwt

SMTP_SERVER   = "smtp.gmail.com"
SMTP_PORT     = 587
SMTP_USER     = "eventospro37@gmail.com"
SMTP_PASSWORD = "yzyp etrf ufpz hbyv"

email_bp = Blueprint('email_service', __name__, url_prefix='/api/email')


def enviar_correo(destinatario, asunto, cuerpo_html, cuerpo_texto=None):
    try:
        msg = MIMEMultipart('alternative')
        msg['Subject'] = asunto
        msg['From']    = f"Eventos Pro <{SMTP_USER}>"
        msg['To']      = destinatario

        if cuerpo_texto:
            msg.attach(MIMEText(cuerpo_texto, 'plain', 'utf-8'))
        msg.attach(MIMEText(cuerpo_html, 'html', 'utf-8'))

        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.ehlo()
            server.starttls()
            server.ehlo()
            server.login(SMTP_USER, SMTP_PASSWORD)
            server.sendmail(SMTP_USER, destinatario, msg.as_string())

        return {'success': True, 'message': f'Correo enviado a {destinatario}'}

    except smtplib.SMTPAuthenticationError:
        return {'success': False, 'message': 'Error de autenticación SMTP.'}
    except Exception as e:
        return {'success': False, 'message': f'Error: {str(e)}'}


def _template_bienvenida(nombre):
    return f"""
    <html><body style="font-family:Arial,sans-serif;background:#f4f4f4;padding:20px;">
      <div style="max-width:600px;margin:auto;background:#fff;border-radius:8px;padding:30px;">
        <h2 style="color:#6c63ff;">¡Bienvenido a Eventos Pro, {nombre}!</h2>
        <p>Tu cuenta ha sido creada exitosamente.</p>
        <p>Ya puedes explorar nuestros paquetes y servicios.</p>
        <hr style="border:none;border-top:1px solid #eee;">
        <p style="font-size:12px;color:#999;">Eventos Pro • eventospro37@gmail.com</p>
      </div>
    </body></html>
    """

def _template_contacto(nombre, mensaje):
    return f"""
    <html><body style="font-family:Arial,sans-serif;background:#f4f4f4;padding:20px;">
      <div style="max-width:600px;margin:auto;background:#fff;border-radius:8px;padding:30px;">
        <h2 style="color:#6c63ff;">Nuevo mensaje de contacto</h2>
        <p><strong>De:</strong> {nombre}</p>
        <p><strong>Mensaje:</strong></p>
        <blockquote style="border-left:4px solid #6c63ff;padding-left:12px;color:#555;">{mensaje}</blockquote>
        <hr style="border:none;border-top:1px solid #eee;">
        <p style="font-size:12px;color:#999;">Eventos Pro • Panel de administración</p>
      </div>
    </body></html>
    """

def _template_reservacion(nombre, paquete, fecha):
    return f"""
    <html><body style="font-family:Arial,sans-serif;background:#f4f4f4;padding:20px;">
      <div style="max-width:600px;margin:auto;background:#fff;border-radius:8px;padding:30px;">
        <h2 style="color:#6c63ff;">Confirmación de Reservación</h2>
        <p>Hola <strong>{nombre}</strong>, tu reservación ha sido registrada.</p>
        <table style="width:100%;border-collapse:collapse;margin-top:16px;">
          <tr style="background:#f0eeff;">
            <td style="padding:8px;font-weight:bold;">Paquete</td>
            <td style="padding:8px;">{paquete}</td>
          </tr>
          <tr>
            <td style="padding:8px;font-weight:bold;">Fecha del evento</td>
            <td style="padding:8px;">{fecha}</td>
          </tr>
        </table>
        <p style="margin-top:20px;">Nos pondremos en contacto para coordinar los detalles.</p>
        <hr style="border:none;border-top:1px solid #eee;">
        <p style="font-size:12px;color:#999;">Eventos Pro • eventospro37@gmail.com</p>
      </div>
    </body></html>
    """


def init_email_routes():

    @email_bp.route('/bienvenida', methods=['POST'])
    def correo_bienvenida():
        data = request.get_json()
        if not data or not data.get('destinatario') or not data.get('nombre'):
            return jsonify({'success': False, 'error': 'destinatario y nombre son requeridos'}), 400
        html = _template_bienvenida(data['nombre'])
        resultado = enviar_correo(data['destinatario'], "¡Bienvenido a Eventos Pro!", html,
                                  f"Bienvenido {data['nombre']}, tu cuenta fue creada.")
        return jsonify(resultado), 200 if resultado['success'] else 500

    @email_bp.route('/contacto', methods=['POST'])
    def correo_contacto():
        data = request.get_json()
        if not data or not data.get('nombre') or not data.get('email_remitente') or not data.get('mensaje'):
            return jsonify({'success': False, 'error': 'nombre, email_remitente y mensaje son requeridos'}), 400
        html = _template_contacto(data['nombre'], data['mensaje'])
        resultado = enviar_correo(SMTP_USER, f"Nuevo contacto de {data['nombre']} - Eventos Pro", html)
        return jsonify(resultado), 200 if resultado['success'] else 500

    @email_bp.route('/reservacion', methods=['POST'])
    @jwt_required()
    def correo_reservacion():
        data = request.get_json()
        for campo in ['destinatario', 'nombre', 'paquete', 'fecha']:
            if not data or not data.get(campo):
                return jsonify({'success': False, 'error': f'Campo {campo} es requerido'}), 400
        html = _template_reservacion(data['nombre'], data['paquete'], data['fecha'])
        resultado = enviar_correo(data['destinatario'], "Confirmación de tu reservación - Eventos Pro", html)
        return jsonify(resultado), 200 if resultado['success'] else 500

    @email_bp.route('/personalizado', methods=['POST'])
    @jwt_required()
    def correo_personalizado():
        claims = get_jwt()
        if claims.get('rol') != 'admin':
            return jsonify({'success': False, 'error': 'Se requieren permisos de administrador'}), 403
        data = request.get_json()
        if not data or not data.get('destinatario') or not data.get('asunto') or not data.get('cuerpo_html'):
            return jsonify({'success': False, 'error': 'destinatario, asunto y cuerpo_html son requeridos'}), 400
        resultado = enviar_correo(data['destinatario'], data['asunto'], data['cuerpo_html'], data.get('cuerpo_texto', ''))
        return jsonify(resultado), 200 if resultado['success'] else 500

    return email_bp