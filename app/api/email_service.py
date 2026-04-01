import smtplib
import io
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
from datetime import datetime

from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
from reportlab.lib.units import cm

SMTP_SERVER   = "smtp.gmail.com"
SMTP_PORT     = 587
SMTP_USER     = "eventospro37@gmail.com"
SMTP_PASSWORD = "yzyp etrf ufpz hbyv"


# ============================================================
# MARCO CON BORDE Y NÚMERO DE PÁGINA
# ============================================================
class MarcoConBorde:
    def __init__(self, evento_id):
        self.evento_id = evento_id

    def __call__(self, canv, doc):
        canv.saveState()
        w, h = letter

        # Borde exterior negro grueso
        canv.setStrokeColor(colors.black)
        canv.setLineWidth(2)
        canv.rect(1.2*cm, 1.2*cm, w - 2.4*cm, h - 2.4*cm)

        # Línea interior delgada
        canv.setLineWidth(0.5)
        canv.rect(1.5*cm, 1.5*cm, w - 3*cm, h - 3*cm)

        # Número de página centrado al pie
        canv.setFont('Helvetica', 9)
        canv.setFillColor(colors.HexColor('#555555'))
        canv.drawCentredString(
            w / 2,
            0.6 * cm,
            f"Página {doc.page}  •  Contrato #{self.evento_id}  •  Eventos Pro"
        )

        canv.restoreState()


# ============================================================
# GENERAR PDF DEL CONTRATO EN MEMORIA
# ============================================================
def generar_pdf_contrato(evento):
    """Genera el PDF del contrato con diseño formal y lo retorna como bytes."""
    buffer = io.BytesIO()
    evento_id = evento.get('id', 'XX')

    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        rightMargin=2.8*cm,
        leftMargin=2.8*cm,
        topMargin=3.2*cm,
        bottomMargin=3*cm
    )

    styles = getSampleStyleSheet()
    story  = []

    # ---- Estilos ----
    titulo_style = ParagraphStyle(
        'Titulo',
        parent=styles['Title'],
        fontSize=20,
        textColor=colors.HexColor('#0D2B5E'),
        spaceAfter=2,
        alignment=1
    )
    subtitulo_style = ParagraphStyle(
        'Subtitulo',
        parent=styles['Normal'],
        fontSize=10,
        textColor=colors.HexColor('#666666'),
        spaceAfter=6,
        alignment=1
    )
    normal = ParagraphStyle(
        'NormalCustom',
        parent=styles['Normal'],
        fontSize=10,
        textColor=colors.HexColor('#222222'),
        leading=15
    )
    seccion_style = ParagraphStyle(
        'Seccion',
        parent=styles['Normal'],
        fontSize=11,
        textColor=colors.white,
        spaceBefore=14,
        spaceAfter=6
    )
    pie_style = ParagraphStyle(
        'Pie',
        parent=styles['Normal'],
        fontSize=8,
        textColor=colors.HexColor('#888888'),
        alignment=1
    )

    # ---- Encabezado ----
    story.append(Spacer(1, 0.2*cm))
    story.append(Paragraph("EVENTOS PRO", titulo_style))
    story.append(Paragraph("Servicios Fotográficos Profesionales", subtitulo_style))
    story.append(Spacer(1, 0.3*cm))
    story.append(HRFlowable(width="100%", thickness=2,
                             color=colors.HexColor('#0D2B5E'), spaceAfter=2))
    story.append(HRFlowable(width="100%", thickness=0.5,
                             color=colors.HexColor('#0D2B5E'), spaceAfter=12))

    # ---- Folio y fecha de emisión ----
    fecha_hoy = datetime.now().strftime("%d de %B de %Y")
    folio_id  = f"EP-{evento_id:04d}" if isinstance(evento_id, int) else f"EP-{evento_id}"
    folio_data = [[
        Paragraph(f"<b>Folio de contrato:</b>  {folio_id}", normal),
        Paragraph(f"<b>Fecha de emisión:</b>  {fecha_hoy}", normal)
    ]]
    tabla_folio = Table(folio_data, colWidths=[9*cm, 8*cm])
    tabla_folio.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#F0F4FF')),
        ('BOX',        (0,0), (-1,-1), 0.8, colors.HexColor('#0D2B5E')),
        ('PADDING',    (0,0), (-1,-1), 8),
    ]))
    story.append(tabla_folio)
    story.append(Spacer(1, 16))

    # ---- Helper para encabezados de sección ----
    def encabezado_seccion(texto):
        data = [[Paragraph(f"  {texto}", seccion_style)]]
        t = Table(data, colWidths=[17*cm])
        t.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#0D2B5E')),
            ('PADDING',    (0,0), (-1,-1), 7),
            ('BOX',        (0,0), (-1,-1), 0.5, colors.black),
        ]))
        return t

    # ---- I. Datos del cliente y evento ----
    story.append(encabezado_seccion("I. DATOS DEL CLIENTE Y EVENTO"))
    story.append(Spacer(1, 6))

    nombre  = evento.get('user_nombre', '—')
    email   = evento.get('user_email',  '—')
    fecha   = evento.get('fecha_evento','—')
    lugar   = evento.get('lugar') or '—'
    tipo_ev = evento.get('tipo_evento', '—')
    coment  = evento.get('comentarios') or '—'

    datos_cliente = [
        ("Cliente",             nombre),
        ("Correo electrónico",  email),
        ("Tipo de evento",      tipo_ev),
        ("Fecha del evento",    fecha),
        ("Lugar",               lugar),
        ("Comentarios",         coment),
    ]
    tabla_cliente = Table(
        [[Paragraph(f"<b>{k}</b>", normal), Paragraph(str(v), normal)]
         for k, v in datos_cliente],
        colWidths=[5.5*cm, 11.5*cm]
    )
    tabla_cliente.setStyle(TableStyle([
        ('ROWBACKGROUNDS', (0,0), (-1,-1),
         [colors.HexColor('#F7F9FC'), colors.white]),
        ('BOX',      (0,0), (-1,-1), 1,   colors.black),
        ('INNERGRID',(0,0), (-1,-1), 0.4, colors.HexColor('#AAAAAA')),
        ('PADDING',  (0,0), (-1,-1), 8),
        ('VALIGN',   (0,0), (-1,-1), 'MIDDLE'),
    ]))
    story.append(tabla_cliente)
    story.append(Spacer(1, 16))

    # ---- II. Servicios contratados ----
    story.append(encabezado_seccion("II. SERVICIOS CONTRATADOS"))
    story.append(Spacer(1, 6))

    if evento.get('paquete'):
        p = evento['paquete']
        precio = int(p.get('precio_total', 0))
        datos_pkg = [
            [Paragraph("<b>Concepto</b>",    normal), Paragraph("<b>Detalle</b>", normal)],
            [Paragraph("<b>Paquete</b>",     normal), Paragraph(p.get('nombre','—'), normal)],
            [Paragraph("<b>Descripción</b>", normal), Paragraph(p.get('descripcion','—'), normal)],
            [Paragraph("<b>Precio total</b>",normal), Paragraph(f"${precio:,} MXN", normal)],
        ]
        tabla_pkg = Table(datos_pkg, colWidths=[5.5*cm, 11.5*cm])
        tabla_pkg.setStyle(TableStyle([
            ('BACKGROUND',    (0,0),  (-1,0),  colors.HexColor('#D6E4FF')),
            ('FONTNAME',      (0,0),  (-1,0),  'Helvetica-Bold'),
            ('ROWBACKGROUNDS',(0,1),  (-1,-1),
             [colors.HexColor('#F7F9FC'), colors.white]),
            ('BOX',      (0,0), (-1,-1), 1,   colors.black),
            ('INNERGRID',(0,0), (-1,-1), 0.4, colors.HexColor('#AAAAAA')),
            ('PADDING',  (0,0), (-1,-1), 8),
        ]))
        story.append(tabla_pkg)

    elif evento.get('servicios'):
        encabezado_svc = [[
            Paragraph("<b>Servicio</b>", normal),
            Paragraph("<b>Precio</b>",   normal)
        ]]
        filas_svc = [
            [Paragraph(s.get('nombre','—'), normal),
             Paragraph(f"${int(s.get('precio',0)):,} MXN", normal)]
            for s in evento['servicios']
        ]
        total = sum(s.get('precio', 0) for s in evento['servicios'])
        pie_svc = [[
            Paragraph("<b>TOTAL</b>", normal),
            Paragraph(f"<b>${total:,} MXN</b>", normal)
        ]]
        tabla_svc = Table(
            encabezado_svc + filas_svc + pie_svc,
            colWidths=[11.5*cm, 5.5*cm]
        )
        tabla_svc.setStyle(TableStyle([
            ('BACKGROUND',    (0,0),  (-1,0),  colors.HexColor('#D6E4FF')),
            ('FONTNAME',      (0,0),  (-1,0),  'Helvetica-Bold'),
            ('ROWBACKGROUNDS',(0,1),  (-1,-2),
             [colors.HexColor('#F7F9FC'), colors.white]),
            ('BACKGROUND',    (0,-1), (-1,-1), colors.HexColor('#0D2B5E')),
            ('TEXTCOLOR',     (0,-1), (-1,-1), colors.white),
            ('FONTNAME',      (0,-1), (-1,-1), 'Helvetica-Bold'),
            ('BOX',      (0,0), (-1,-1), 1,   colors.black),
            ('INNERGRID',(0,0), (-1,-1), 0.4, colors.HexColor('#AAAAAA')),
            ('PADDING',  (0,0), (-1,-1), 8),
            ('ALIGN',    (1,0), (1,-1), 'RIGHT'),
        ]))
        story.append(tabla_svc)

    story.append(Spacer(1, 20))

    # ---- III. Términos y condiciones ----
    story.append(encabezado_seccion("III. TÉRMINOS Y CONDICIONES"))
    story.append(Spacer(1, 8))
    terminos = [
        "1. El presente contrato constituye la confirmación oficial de los servicios fotográficos contratados con Eventos Pro.",
        "2. Nuestro equipo se pondrá en contacto con el cliente en un plazo máximo de 24 horas para coordinar los detalles del evento.",
        "3. El precio acordado incluye únicamente los servicios especificados en la sección II.",
        "4. Cualquier modificación al contrato deberá ser acordada por ambas partes por escrito.",
        "5. Eventos Pro se compromete a brindar un servicio profesional y de calidad en la fecha acordada.",
    ]
    for t in terminos:
        story.append(Paragraph(t, normal))
        story.append(Spacer(1, 5))

    story.append(Spacer(1, 24))

    # ---- Firmas ----
    firmas = [
        [Paragraph("_______________________", normal), Paragraph("_______________________", normal)],
        [Paragraph("<b>Cliente</b>",          normal), Paragraph("<b>Eventos Pro</b>",      normal)],
        [Paragraph(nombre,                    normal), Paragraph("Fotógrafo / Administrador", normal)],
    ]
    tabla_firmas = Table(firmas, colWidths=[8.5*cm, 8.5*cm])
    tabla_firmas.setStyle(TableStyle([
        ('ALIGN',   (0,0), (-1,-1), 'CENTER'),
        ('PADDING', (0,0), (-1,-1), 6),
    ]))
    story.append(tabla_firmas)
    story.append(Spacer(1, 20))

    # ---- Pie del documento ----
    story.append(HRFlowable(width="100%", thickness=0.5,
                             color=colors.HexColor('#AAAAAA'), spaceAfter=6))
    story.append(Paragraph(
        "Eventos Pro  •  eventospro37@gmail.com  •  Documento generado automáticamente",
        pie_style
    ))

    doc.build(
        story,
        onFirstPage=MarcoConBorde(evento_id),
        onLaterPages=MarcoConBorde(evento_id)
    )
    buffer.seek(0)
    return buffer.read()


# ============================================================
# ENVIAR CORREO (con adjunto opcional)
# ============================================================
def enviar_correo(destinatario, asunto, cuerpo_html, cuerpo_texto="", adjunto_pdf=None, nombre_pdf="contrato.pdf"):
    """Envía correo con adjunto PDF opcional."""
    try:
        msg = MIMEMultipart('mixed')
        msg['Subject'] = asunto
        msg['From']    = f"Eventos Pro <{SMTP_USER}>"
        msg['To']      = destinatario

        alternativa = MIMEMultipart('alternative')
        if cuerpo_texto:
            alternativa.attach(MIMEText(cuerpo_texto, 'plain', 'utf-8'))
        alternativa.attach(MIMEText(cuerpo_html, 'html', 'utf-8'))
        msg.attach(alternativa)

        if adjunto_pdf:
            parte = MIMEBase('application', 'pdf')
            parte.set_payload(adjunto_pdf)
            encoders.encode_base64(parte)
            parte.add_header('Content-Disposition', 'attachment', filename=nombre_pdf)
            msg.attach(parte)

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


# ============================================================
# CORREO DE ACEPTACIÓN (con PDF adjunto)
# ============================================================
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
          <td style="padding:10px;font-weight:bold;">Descripcion</td>
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
              <td style="padding:8px 10px;">- {s.get('nombre','—')}</td>
              <td style="padding:8px 10px;">${int(s.get('precio',0)):,} MXN</td>
            </tr>"""
            total += s.get('precio', 0)
        contratado_html = f"""
        <tr style="background:#E3F2FD;">
          <td colspan="2" style="padding:10px;font-weight:bold;">Servicios contratados</td>
        </tr>{filas}
        <tr style="background:#E3F2FD;">
          <td style="padding:10px;font-weight:bold;">Total</td>
          <td style="padding:10px;color:#1565C0;font-weight:bold;">${total:,} MXN</td>
        </tr>"""
        precio_texto = f"${total:,} MXN"
    else:
        contratado_html = ""
        precio_texto    = "—"

    html = f"""
    <html><body style="font-family:Arial,sans-serif;background:#f4f4f4;padding:20px;">
      <div style="max-width:650px;margin:auto;background:#fff;border-radius:10px;
                  padding:36px;box-shadow:0 4px 20px rgba(0,0,0,0.08);">
        <div style="text-align:center;margin-bottom:28px;">
          <h1 style="color:#1565C0;font-size:26px;margin:0;">Eventos Pro</h1>
          <p style="color:#888;font-size:13px;margin:4px 0 0;">Confirmacion de contrato</p>
        </div>
        <h2 style="color:#2E7D32;border-bottom:2px solid #C8E6C9;padding-bottom:10px;">
          Tu solicitud fue aceptada, {nombre}!
        </h2>
        <p style="color:#444;margin:16px 0;">
          Confirmamos la contratacion de nuestros servicios.
          Encontraras el <strong>contrato completo adjunto en PDF</strong> a este correo.
        </p>
        <h3 style="color:#1565C0;margin:24px 0 10px;">Datos del evento</h3>
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
        <h3 style="color:#1565C0;margin:24px 0 10px;">Lo contratado</h3>
        <table style="width:100%;border-collapse:collapse;">{contratado_html}</table>
        <div style="background:#E8F5E9;border-left:4px solid #4CAF50;
                    padding:14px 18px;border-radius:6px;margin:28px 0;">
          <strong>Que sigue?</strong><br>
          Nuestro equipo se pondra en contacto en las proximas <strong>24 horas</strong>.
        </div>
        <p style="color:#888;font-size:12px;text-align:center;margin-top:30px;
                  border-top:1px solid #eee;padding-top:16px;">
          Eventos Pro &bull; eventospro37@gmail.com
        </p>
      </div>
    </body></html>"""

    pdf_bytes = generar_pdf_contrato(evento)

    return enviar_correo(
        email,
        f"Contrato confirmado - {tipo_ev} | Eventos Pro",
        html,
        f"Hola {nombre}, tu solicitud fue ACEPTADA. Adjunto encontraras tu contrato en PDF. Evento: {tipo_ev} | Fecha: {fecha} | {precio_texto}",
        adjunto_pdf=pdf_bytes,
        nombre_pdf="Contrato_EventosPro.pdf"
    )


# ============================================================
# CORREO DE RECHAZO
# ============================================================
def correo_rechazo(evento, motivo):
    nombre  = evento.get('user_nombre', 'Cliente')
    email   = evento.get('user_email', '')
    fecha   = evento.get('fecha_evento', '—')
    tipo_ev = evento.get('tipo_evento', '—')

    html = f"""
    <html><body style="font-family:Arial,sans-serif;background:#f4f4f4;padding:20px;">
      <div style="max-width:620px;margin:auto;background:#fff;border-radius:10px;
                  padding:36px;box-shadow:0 4px 20px rgba(0,0,0,0.08);">
        <div style="text-align:center;margin-bottom:28px;">
          <h1 style="color:#1565C0;font-size:26px;margin:0;">Eventos Pro</h1>
          <p style="color:#888;font-size:13px;margin:4px 0 0;">Actualizacion sobre tu solicitud</p>
        </div>
        <h2 style="color:#C62828;border-bottom:2px solid #FFCDD2;padding-bottom:10px;">
          Actualizacion sobre tu solicitud
        </h2>
        <p style="color:#444;margin:16px 0;">
          Hola <strong>{nombre}</strong>, lamentamos informarte que en esta ocasion
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
        "Actualizacion sobre tu solicitud - Eventos Pro",
        html,
        f"Hola {nombre}, tu solicitud fue RECHAZADA. Motivo: {motivo}"
    )