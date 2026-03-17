import os
import logging
from flask import Flask, render_template, jsonify, request, redirect, url_for
from dotenv import load_dotenv
import cohere
from newsapi import NewsApiClient

# Cargar variables de entorno
load_dotenv()

# Configurar logging
logging.basicConfig(level=logging.DEBUG)

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev-key-please-change')

# Inicializar APIs con manejo de errores
cohere_api_key = os.getenv('COHERE_API_KEY')
news_api_key = os.getenv('NEWS_API_KEY')

cohere_client = None
newsapi = None

if cohere_api_key:
    try:
        cohere_client = cohere.Client(cohere_api_key)
        app.logger.info("Cohere client initialized")
    except Exception as e:
        app.logger.error(f"Error initializing Cohere: {e}")
else:
    app.logger.warning("COHERE_API_KEY not set")

if news_api_key:
    try:
        newsapi = NewsApiClient(api_key=news_api_key)
        app.logger.info("NewsAPI client initialized")
    except Exception as e:
        app.logger.error(f"Error initializing NewsAPI: {e}")
else:
    app.logger.warning("NEWS_API_KEY not set")

# Datos de ejemplo
PAQUETES = [
    {
        'id': 1,
        'nombre': 'Básico',
        'precio': 5000,
        'descripcion': 'Ideal para eventos pequeños',
        'servicios': ['Sesión de fotos 2 hrs', 'Video resumen 3 min']
    },
    {
        'id': 2,
        'nombre': 'Esencial',
        'precio': 10000,
        'descripcion': 'Cobertura completa',
        'servicios': ['Sesión de fotos 4 hrs', 'Video documental 10 min', 'Entrevistas']
    },
    {
        'id': 3,
        'nombre': 'Premium',
        'precio': 15000,
        'descripcion': 'Incluye drone',
        'servicios': ['Fotos 6 hrs', 'Video 15 min', 'Drone', 'Entrevistas']
    },
    {
        'id': 4,
        'nombre': 'Élite',
        'precio': 25000,
        'descripcion': 'Transmisión en vivo incluida',
        'servicios': ['Fotos 8 hrs', 'Video 20 min', 'Drone', 'Live Streaming', 'Álbum digital']
    },
    {
        'id': 5,
        'nombre': 'Platino',
        'precio': 35000,
        'descripcion': 'Experiencia VIP',
        'servicios': ['Fotos 10 hrs', 'Video 30 min', 'Drone', 'Live Streaming', 'Video 360', 'Álbum impreso']
    }
]

SERVICIOS_INDIVIDUALES = [
    {'id': 101, 'nombre': 'Sesión de fotos (hora)', 'precio': 1200},
    {'id': 102, 'nombre': 'Video (hora)', 'precio': 1500},
    {'id': 103, 'nombre': 'Grabación con drone (hora)', 'precio': 2500},
    {'id': 104, 'nombre': 'Transmisión en vivo (evento)', 'precio': 3000},
    {'id': 105, 'nombre': 'Video 360 (evento)', 'precio': 4000},
    {'id': 106, 'nombre': 'Álbum digital', 'precio': 800},
    {'id': 107, 'nombre': 'Álbum impreso', 'precio': 1500},
    {'id': 108, 'nombre': 'Sesión de compromiso', 'precio': 1800},
    {'id': 109, 'nombre': 'Video same day edit', 'precio': 3500},
    {'id': 110, 'nombre': 'Fotografía con impresión instantánea', 'precio': 2000}
]

@app.route('/')
def index():
    """Redirige a la página de paquetes por defecto"""
    return redirect(url_for('paquetes'))

@app.route('/paquetes')
def paquetes():
    """Página de paquetes"""
    return render_template('paquetes.html',
                           paquetes=PAQUETES,
                           ga_id=os.getenv('GA_MEASUREMENT_ID'),
                           twitch_channel=os.getenv('TWITCH_CHANNEL', 'Eventos Pro'))

@app.route('/servicios')
def servicios():
    """Página de servicios individuales"""
    return render_template('servicios.html',
                           servicios=SERVICIOS_INDIVIDUALES,
                           ga_id=os.getenv('GA_MEASUREMENT_ID'),
                           twitch_channel=os.getenv('TWITCH_CHANNEL', 'Eventos Pro'))

@app.route('/noticias')
def noticias():
    """Página de noticias"""
    return render_template('noticias.html',
                           ga_id=os.getenv('GA_MEASUREMENT_ID'),
                           twitch_channel=os.getenv('TWITCH_CHANNEL', 'Eventos Pro'))

@app.route('/api/chat', methods=['POST'])
def chat():
    """Endpoint para el chatbot"""
    if not cohere_client:
        return jsonify({'error': 'Chatbot no configurado'}), 503

    data = request.get_json()
    mensaje = data.get('message', '')
    if not mensaje:
        return jsonify({'error': 'Mensaje vacío'}), 400

    try:
        response = cohere_client.chat(
            message=mensaje,
            preamble="Eres un asistente virtual de EventosPro, una empresa de fotografía y video para eventos sociales. Responde de forma amable y breve, ayudando a los clientes a elegir paquetes o servicios."
        )
        return jsonify({'respuesta': response.text})
    except Exception as e:
        app.logger.error(f"Error en Cohere: {e}")
        return jsonify({'error': 'Error al procesar la solicitud'}), 500

@app.route('/api/noticias')
def api_noticias():
    """Obtener noticias de eventos sociales (para la página de noticias)"""
    if not newsapi:
        return jsonify({'error': 'API de noticias no configurada'}), 503

    try:
        noticias = newsapi.get_everything(
            q='bodas OR "XV años" OR "eventos sociales" OR quinceañera OR wedding',
            language='es',
            sort_by='relevancy',
            page_size=5
        )
        articulos = noticias.get('articles', [])
        # Limpiar datos sensibles o nulos
        for art in articulos:
            art.pop('source', None)  # opcional
        return jsonify(articulos)
    except Exception as e:
        app.logger.error(f"Error en NewsAPI: {e}")
        return jsonify({'error': 'Error al obtener noticias'}), 500

if __name__ == '__main__':
    app.run(debug=True, port=5000)
    app.run(host="0.0.0.0", port=port)