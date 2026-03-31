import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

SMTP_SERVER   = "smtp.gmail.com"
SMTP_PORT     = 587
SMTP_USER     = "eventospro37@gmail.com"
SMTP_PASSWORD = "yzyp etrf ufpz hbyv"


def enviar_correo(destinatario, asunto, cuerpo_html, cuerpo_texto=""):
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
        return {'success': True}
    except smtplib.SMTPAuthenticationError:
        return {'success': False, 'error': 'Error de autenticación SMTP'}
    except Exception as e:
        return {'success': False, 'error': str(e)}


def correo_aceptacion(evento):
    nombre  = evento.get('user_nombre', 'Cliente')
    email   = evento.get('user_email', '')
    fecha   = evento.get('fecha_evento', '—')
    lugar   = evento.get('lugar') or '—'
    tipo_ev = evento.get('tipo_evento', '—')
    coment  = evento.get('comentarios') or '—'

    if evento.get('paquete'):
        p = evento['paquete']
        precio = int(p.get('precio_total', 0))
        contratado_html = f"""
        <tr style="background:#E3F2FD;">
          <td style="padding:10px;font-weight:bold;">Paquete</td>
          <td style="padding:10px;">{p.get('nombre','—')}</td>
        </tr>
        <tr>
          <td style="padding:10px;font-weight:bold;">Descripción</td>
          <td style="padding:10px;">{p.get('descripcion','—')}</td>
        </tr>
        <tr style="background:#E3F2FD;">
          <td style="padding:10px;font-weight:bold;">Precio total</td>
          <td style="padding:10px;color:#1565C0;font-weight:bold;">${precio:,} MXN</td>
        </tr>"""
        precio_texto = f"${precio:,} MXN"
    elif evento.get('servicios'):
        total = 0
        filas = ""
        for s in evento['servicios']:
            filas += f"""
            <tr>
              <td style="padding:8px 10px;">• {s.get('nombre','—')}</td>
              <td style="padding:8px 10px;">${int(s.get('precio',0)):,} MXN</td>
            </tr>"""
            total += s.get('precio', 0)
        contratado_html = f"""
        <tr style="background:#E3F2FD;">
          <td colspan="2" style="padding:10px;font-weight:bold;">Servicios contratados</td>
        </tr>
        {filas}
        <tr style="background:#E3F2FD;">
          <td style="padding:10px;font-weight:bold;">Total</td>
          <td style="padding:10px;color:#1565C0;font-weight:bold;">${total:,} MXN</td>
        </tr>"""
        precio_texto = f"${total:,} MXN"
    else:
        contratado_html = ""
        precio_texto = "—"

    html = f"""
    <html><body style="font-family:Arial,sans-serif;background:#f4f4f4;padding:20px;">
      <div style="max-width:650px;margin:auto;background:#fff;border-radius:10px;padding:36px;
                  box-shadow:0 4px 20px rgba(0,0,0,0.08);">
        <div style="text-align:center;margin-bottom:28px;">
          <h1 style="color:#1565C0;font-size:26px;margin:0;">📸 Eventos Pro</h1>
          <p style="color:#888;font-size:13px;margin:4px 0 0;">Confirmación de contrato</p>
        </div>
        <h2 style="color:#2E7D32;border-bottom:2px solid #C8E6C9;padding-bottom:10px;">
          ✅ ¡Tu solicitud fue aceptada, {nombre}!
        </h2>
        <p style="color:#444;margin:16px 0;">
          Confirmamos la contratación de nuestros servicios para tu evento.
          Aquí está el resumen de tu contrato:
        </p>
        <h3 style="color:#1565C0;margin:24px 0 10px;">📅 Datos del evento</h3>
        <table style="width:100%;border-collapse:collapse;">
          <tr style="background:#E3F2FD;">
            <td style="padding:10px;font-weight:bold;width:40%;">Cliente</td>
            <td style="padding:10px;">{nombre}</td>
          </tr>
          <tr>
            <td style="padding:10px;font-weight:bold;">Tipo de evento</td>
            <td style="padding:10px;">{tipo_ev}</td>
          </tr>
          <tr style="background:#E3F2FD;">
            <td style="padding:10px;font-weight:bold;">Fecha del evento</td>
            <td style="padding:10px;">{fecha}</td>
          </tr>
          <tr>
            <td style="padding:10px;font-weight:bold;">Lugar</td>
            <td style="padding:10px;">{lugar}</td>
          </tr>
          <tr style="background:#E3F2FD;">
            <td style="padding:10px;font-weight:bold;">Comentarios</td>
            <td style="padding:10px;">{coment}</td>
          </tr>
        </table>
        <h3 style="color:#1565C0;margin:24px 0 10px;">📦 Lo que contrataste</h3>
        <table style="width:100%;border-collapse:collapse;">
          {contratado_html}
        </table>
        <div style="background:#E8F5E9;border-left:4px solid #4CAF50;
                    padding:14px 18px;border-radius:6px;margin:28px 0;">
          <strong>¿Qué sigue?</strong><br>
          Nuestro equipo se pondrá en contacto contigo en las próximas
          <strong>24 horas</strong> para coordinar los últimos detalles.
        </div>
        <p style="color:#888;font-size:12px;text-align:center;margin-top:30px;
                  border-top:1px solid #eee;padding-top:16px;">
          Eventos Pro &bull; eventospro37@gmail.com<br>
          Este correo es la confirmación oficial de tu contratación.
        </p>
      </div>
    </body></html>"""

    return enviar_correo(
        email,
        f"✅ Contrato confirmado — {tipo_ev} | Eventos Pro",
        html,
        f"Hola {nombre}, tu solicitud fue ACEPTADA. Evento: {tipo_ev} | Fecha: {fecha} | {precio_texto}"
    )


def correo_rechazo(evento, motivo):
    nombre  = evento.get('user_nombre', 'Cliente')
    email   = evento.get('user_email', '')
    fecha   = evento.get('fecha_evento', '—')
    tipo_ev = evento.get('tipo_evento', '—')

    html = f"""
    <html><body style="font-family:Arial,sans-serif;background:#f4f4f4;padding:20px;">
      <div style="max-width:620px;margin:auto;background:#fff;border-radius:10px;padding:36px;
                  box-shadow:0 4px 20px rgba(0,0,0,0.08);">
        <div style="text-align:center;margin-bottom:28px;">
          <h1 style="color:#1565C0;font-size:26px;margin:0;">📸 Eventos Pro</h1>
          <p style="color:#888;font-size:13px;margin:4px 0 0;">Actualización sobre tu solicitud</p>
        </div>
        <h2 style="color:#C62828;border-bottom:2px solid #FFCDD2;padding-bottom:10px;">
          ❌ Actualización sobre tu solicitud
        </h2>
        <p style="color:#444;margin:16px 0;">
          Hola <strong>{nombre}</strong>, lamentamos informarte que en esta ocasión
          no podemos proceder con tu solicitud.
        </p>
        <table style="width:100%;border-collapse:collapse;margin:16px 0;">
          <tr style="background:#FFF3E0;">
            <td style="padding:10px;font-weight:bold;width:40%;">Tipo de evento</td>
            <td style="padding:10px;">{tipo_ev}</td>
          </tr>
          <tr>
            <td style="padding:10px;font-weight:bold;">Fecha solicitada</td>
            <td style="padding:10px;">{fecha}</td>
          </tr>
        </table>
        <div style="background:#FFEBEE;border-left:4px solid #E53935;
                    padding:16px 18px;border-radius:6px;margin:24px 0;">
          <strong style="color:#C62828;">Motivo del rechazo:</strong><br>
          <p style="margin:8px 0 0;color:#444;">{motivo}</p>
        </div>
        <p style="color:#444;">
          Si tienes dudas o deseas explorar otras opciones, no dudes en contactarnos.
        </p>
        <p style="color:#888;font-size:12px;text-align:center;margin-top:30px;
                  border-top:1px solid #eee;padding-top:16px;">
          Eventos Pro &bull; eventospro37@gmail.com
        </p>
      </div>
    </body></html>"""

    return enviar_correo(
        email,
        "Actualización sobre tu solicitud — Eventos Pro",
        html,
        f"Hola {nombre}, tu solicitud fue RECHAZADA. Motivo: {motivo}"
    )