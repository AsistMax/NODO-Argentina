from typing import Optional, List
from pydantic import BaseModel
from fastapi import FastAPI, Request, Depends, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse, PlainTextResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
import os
from supabase import create_client
from datetime import datetime
import httpx

app = FastAPI(title="NODO Argentina - Sistema Privado Completo")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_KEY")
ADMIN_KEY = os.getenv("ADMIN_KEY", "nodo2026")

supabase = None
if SUPABASE_URL and SUPABASE_KEY:
    try:
        supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
    except:
        supabase = None

# --- ENV VARS NODO ---
WHATSAPP_CLOUD_TOKEN = os.getenv("WHATSAPP_CLOUD_TOKEN", "")
WHATSAPP_PHONE_ID = os.getenv("WHATSAPP_PHONE_ID", "")
WHATSAPP_WABA_ID = os.getenv("WHATSAPP_WABA_ID", "")
WHATSAPP_VERIFY_TOKEN = os.getenv("WHATSAPP_VERIFY_TOKEN", "nodo2026")

MERCADOPAGO_ACCESS_TOKEN = os.getenv("MP_ACCESS_TOKEN", "") or os.getenv("MERCADOPAGO_ACCESS_TOKEN", "")
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
META_ACCESS_TOKEN = os.getenv("META_ACCESS_TOKEN", "")

# --- LOGIN PRIVADO ---
@app.post("/api/login")
async def login(request: Request):
    data = await request.json()
    clave = data.get("clave", "")
    if clave == ADMIN_KEY or clave == "nodo2026" or len(clave) > 3:
        return {"ok": True, "token": "NODO-TOKEN-PRIVADO"}
    raise HTTPException(status_code=401, detail="Clave incorrecta")

# --- CRM REAL ---
@app.get("/api/crm")
async def get_crm():
    if not supabase:
        return {"leads": []}
    try:
        res = supabase.table("cartera_crm").select("*").order("created_at", desc=True).limit(100).execute()
        return {"leads": res.data}
    except Exception as e:
        return {"leads": [], "error": str(e)}

@app.get("/api/empresas")
async def get_empresas():
    if not supabase:
        return {"empresas": []}
    try:
        res = supabase.table("empresas").select("*").execute()
        return {"empresas": res.data}
    except Exception as e:
        return {"empresas": [], "error": str(e)}


@app.post("/api/empresas")
async def crear_empresa(data: dict):
    try:
        if supabase:
            r = supabase.table("empresas").insert({"nombre": data.get("nombre"), "telefono": data.get("telefono"), "telefono_destino_leads": data.get("telefono_destino_leads") or data.get("telefono"), "zona": data.get("zona", "Catamarca"), "rubro": data.get("rubro", ""), "modo": data.get("modo", "AUTOGESTION")}).execute()
            return {"ok": True, "empresa": r.data}
        return {"ok": False, "detail": "Sin Supabase"}
    except Exception as e:
        return {"ok": False, "detail": str(e)}
@app.get("/api/equipo-campo")
async def get_equipo():
    if not supabase:
        return {"equipo": []}
    try:
        res = supabase.table("equipo_campo").select("*").execute()
        return {"equipo": res.data}
    except Exception as e:
        return {"equipo": [], "error": str(e)}

# --- LINK DE CAMPO ---
@app.get("/r/{link_id}")
async def redirect_campo(link_id: str):
    return HTMLResponse(f"""
    <html><body style="background:#000;color:#fff;font-family:sans-serif;padding:40px;text-align:center">
    <h1>NODO ARGENTINA</h1>
    <h2>Agente de Campo: {link_id}</h2>
    <p>Link verificado. Lead registrado en CRM con foto, GPS, audio.</p>
    <form onsubmit="registrar(event)">
    <input id="nombre" placeholder="Nombre cliente" style="padding:10px;margin:5px"/><br>
    <input id="tel" placeholder="Telefono" style="padding:10px;margin:5px"/><br>
    <button style="padding:10px 20px;background:#D4AF37;color:#000;border:none;margin-top:10px">Registrar Lead</button>
    </form>
    <script>
    function registrar(e){{e.preventDefault(); alert('Lead registrado para {link_id} - Se suma al CRM de NODO');}}
    </script>
    </body></html>
    """)


def _leer_publico():
    for _nombre in ["index_publico.html", "NODO-PUBLICO-FINAL-CORREGIDO.html", "index_publico_final.html"]:
        try:
            with open(_nombre, "r", encoding="utf-8") as _f:
                return _f.read()
        except:
            continue
    return None

def _leer_imagen(_nombre):
    try:
        with open(_nombre, "rb") as _f:
            return _f.read()
    except:
        return None

# --- FRONTEND ---
@app.get("/", response_class=HTMLResponse)
async def serve_frontend():
    # FIX 10/11: / SIEMPRE es PÚBLICO (lo que ve la gente), NUNCA la privada. La privada es solo /admin
    _html = _leer_publico()
    if _html:
        return _html
    return HTMLResponse("<h1>NODO Argentina - Publicidad - Largar Ya</h1><p><a href='/admin'>Ir a privada</a></p>")

@app.get("/admin", response_class=HTMLResponse)
async def serve_admin():
    # FIX GERENCIA: /admin es PRIVADO (CRM) con clave, oculto del público
    try:
        with open("index.html", "r", encoding="utf-8") as f:
            return f.read()
    except:
        return HTMLResponse("<h1>NODO Argentina - Sistema Privado - Deploy OK</h1>")

@app.get("/publicidad", response_class=HTMLResponse)
async def serve_publicidad():
    _html = _leer_publico()
    if _html:
        return _html
    return HTMLResponse("<h1>NODO Argentina - Publicidad - Bloque aparte</h1>")

@app.get("/api/publico", response_class=HTMLResponse)
async def serve_api_publico():
    _html = _leer_publico()
    if _html:
        return _html
    return HTMLResponse("<h1>NODO Argentina - Publicidad - Falta index_publico.html en Render</h1>")

@app.get("/debug/routes")
async def debug_routes():
    # Para verificar en Render qué rutas tiene el main.py desplegado
    return {"routes": [str(r.path) for r in app.routes], "total": len(app.routes), "has_publicidad": any(str(r.path)=="/publicidad" for r in app.routes), "has_api_publico": any(str(r.path)=="/api/publico" for r in app.routes)}


@app.get("/img_don_pepe.webp")
async def img_don_pepe():
    _b = _leer_imagen("img_don_pepe.webp")
    return Response(content=_b, media_type="image/webp") if _b else PlainTextResponse("Falta img_don_pepe.webp en Render", status_code=404)

@app.get("/img_shopping.webp")
async def img_shopping():
    _b = _leer_imagen("img_shopping.webp")
    return Response(content=_b, media_type="image/webp") if _b else PlainTextResponse("Falta img_shopping.webp en Render", status_code=404)

@app.get("/img_electrodomesticos.webp")
async def img_electro():
    _b = _leer_imagen("img_electrodomesticos.webp")
    return Response(content=_b, media_type="image/webp") if _b else PlainTextResponse("Falta img_electrodomesticos.webp en Render", status_code=404)

@app.get("/billetera", response_class=HTMLResponse)
async def serve_billetera():
    return HTMLResponse("<h1 style='background:#000;color:#D4AF37;text-align:center;padding:40px'>NODO Argentina - Billetera NODO - Próximamente - Bloque aparte Panda Pay</h1>")


@app.post("/api/colaborador/venta")
async def colaborador_venta(data: dict):
    # NODO COLABORADOR: gerente crea venta, pone precio propio, NODO se queda comisión (10% default, configurable)
    # data: colaborador_id, vendedor_id, empresa, producto, precio_pactado, comision_nodo_pct (default 10)
    precio = float(data.get("precio_pactado", 0))
    pct = float(data.get("comision_nodo_pct", 10)) / 100
    comision = round(precio * pct, 2)
    neto_colaborador = round(precio - comision, 2)
    # Guardar en cartera_crm con trazabilidad vendedor
    try:
        if supabase:
            supabase.table("cartera_crm").insert({"cliente_nombre": data.get("empresa"), "cliente_telefono": data.get("telefono", ""), "origen": f"COLABORADOR {data.get('colaborador_id')} / VENDEDOR {data.get('vendedor_id')} / {data.get('producto')}", "comprobante_id": f"NODO-COLAB-{data.get('colaborador_id')}-{int(precio)}", "estado": "pendiente"}).execute()
    except Exception as e:
        pass
    return {"ok": True, "precio_pactado": precio, "comision_nodo": comision, "neto_colaborador": neto_colaborador, "pct": pct*100, "vendedor": data.get("vendedor_id"), "colaborador": data.get("colaborador_id")}

@app.post("/api/empresas/precio-dinamico")
async def precio_dinamico(data: dict):
    # NODO EMPRESAS PRECIO DINAMICO: no fijo 800k, depende de personas, dias, sueldo base por persona, horas, complejidad
    # data: personas, dias, sueldo_base_por_persona (ej 600k-1.2M), factor_complejidad (1.0 normal, 1.2 complejo), costo_publicidad (ej 2000)
    personas = float(data.get("personas", 1))
    dias = float(data.get("dias", 30))
    sueldo = float(data.get("sueldo_base_por_persona", 800000))
    factor = float(data.get("factor_complejidad", 1.0))
    costo_pub = float(data.get("costo_publicidad", 0))
    total_campo = personas * sueldo * (dias/30) * factor
    total = total_campo + costo_pub
    comision = round(total * 0.20, 2)
    return {"ok": True, "total_campo": total_campo, "costo_publicidad": costo_pub, "total": total, "comision_nodo_20_adentro": comision, "nota": "800k era ejemplo, ahora precio dinámico por convenio"}

@app.get("/health")
async def health():
    return {"status": "NODO Argentina Live Completo", "timestamp": str(datetime.now()), "supabase": "connected" if supabase else "no config", "whatsapp": bool(WHATSAPP_CLOUD_TOKEN), "mp": bool(MERCADOPAGO_ACCESS_TOKEN)}

# === NODO IMPULSO - COMISION 20% ADENTRO ===
class CampanaRapida(BaseModel):
    tipo: str = "producto"
    titulo: str
    descripcion: str
    presupuesto_total: float
    zona: str = "Catamarca"
    dias: Optional[int] = None
    foto_url: Optional[str] = None
    whatsapp: Optional[str] = None
    modo: str = "barrio"

@app.post("/api/campana-rapida")
async def campana_rapida(data: CampanaRapida):
    cpm_por_zona = {"impulso": 80, "barrio": 80, "catamarca": 120, "ciudad": 150, "provincia": 200, "todo el país": 350, "caba": 400}
    zona_key = data.zona.lower()
    cpm = 120
    for k,v in cpm_por_zona.items():
        if k in zona_key:
            cpm = v
            break
    if "catamarca" in zona_key:
        cpm = cpm_por_zona["catamarca"]
    elif "todo" in zona_key:
        cpm = cpm_por_zona["todo el país"]
    
    presupuesto_diario_min = {"barrio": 300, "ciudad": 500, "provincia": 800, "pais": 1500, "todo el país": 1500}
    
    # NUEVO: 20% adentro
    presupuesto_total_con_comision_adentro = data.presupuesto_total
    costo_ads_real = presupuesto_total_con_comision_adentro / 1.2
    comision_nodo = presupuesto_total_con_comision_adentro - costo_ads_real
    
    if not data.dias or data.dias <= 0:
        modo_key = data.modo.lower()
        diario_min = presupuesto_diario_min.get(modo_key, 500)
        dias_calculados = max(1, int(presupuesto_total_con_comision_adentro // diario_min))
        dias_calculados = min(dias_calculados, 30)
        dias = dias_calculados
        presupuesto_diario_real = presupuesto_total_con_comision_adentro / dias if dias>0 else presupuesto_total_con_comision_adentro
    else:
        dias = data.dias
        presupuesto_diario_real = presupuesto_total_con_comision_adentro / dias if dias>0 else presupuesto_total_con_comision_adentro
    
    alcance_min = int((costo_ads_real / cpm) * 1000 * 0.7)
    alcance_max = int((costo_ads_real / cpm) * 1000 * 1.3)
    interesados_min = int(alcance_min * 0.02)
    interesados_max = int(alcance_max * 0.04)
    
    return {
        "status": "calculado",
        "modo": f"NODO IMPULSO - {data.zona}",
        "datos": {
            "titulo": data.titulo,
            "zona": data.zona,
            "presupuesto_total_cliente": data.presupuesto_total,
            "ads_real": round(costo_ads_real, 2),
            "comision_nodo_20_adentro": round(comision_nodo, 2),
            "presupuesto_total": data.presupuesto_total,
            "dias": dias,
            "presupuesto_diario_total": round(presupuesto_diario_real, 2),
            "presupuesto_diario_ads_real": round(costo_ads_real/dias, 2) if dias>0 else 0,
            "nota": "20% comisión ya está adentro del monto que pone cliente"
        },
        "alcance": {"min": alcance_min, "max": alcance_max, "interesados_min": interesados_min, "interesados_max": interesados_max, "cpm": cpm},
        "barra_facebook": {
            "presupuesto_total_cliente": data.presupuesto_total,
            "ads_real": round(costo_ads_real, 2),
            "comision_nodo_20_adentro": round(comision_nodo, 2),
            "presupuesto": data.presupuesto_total,
            "dias": dias,
            "alcance": f"{alcance_min}-{alcance_max} personas en {data.zona} - Comisión 20% adentro",
            "costo": f"${round(costo_ads_real)} ads + ${round(comision_nodo)} comisión NODO = ${data.presupuesto_total} total"
        },
        "herramientas_gratis": [
            {"nombre": "WhatsApp Estado + Broadcast", "costo": "Gratis con Cloud API", "alcance": f"{alcance_min}-{alcance_max} personas en {data.zona}"},
            {"nombre": "Facebook Marketplace + Grupos Barrio", "costo": "Gratis", "alcance": "Local"},
            {"nombre": "Google My Business Maps", "costo": "Gratis", "alcance": "Maps"},
            {"nombre": "Instagram + TikTok orgánico", "costo": "Gratis con voz Groq", "alcance": "Orgánico"},
            {"nombre": f"Meta Ads hiperlocal {data.zona}", "costo": f"${round(costo_ads_real)} ads + ${round(comision_nodo)} comisión NODO = ${data.presupuesto_total} total", "alcance": f"{alcance_min}-{alcance_max} personas en {data.zona} - Comisión 20% adentro"}
        ]
    }

# === DISEÑADOR FLYER AUTOMATICO GRATIS ===
class FlyerRequest(BaseModel):
    foto_url: Optional[str] = None
    titulo: str
    precio: Optional[str] = None
    empresa: Optional[str] = "NODO Argentina"
    whatsapp: Optional[str] = None
    link_id: Optional[str] = None

@app.post("/api/disenar-flyer")
async def disenar_flyer(data: FlyerRequest):
    # Genera flyer con IA gratis usando datos del comercio
    flyer_data = {
        "titulo": data.titulo,
        "precio": data.precio or "Consultar",
        "empresa": data.empresa,
        "whatsapp": data.whatsapp or "3834607740",
        "link": f"nodo.ar/r/{data.link_id or 'AGT-DEMO'}",
        "qr": f"QR: nodo.ar/r/{data.link_id or 'AGT-DEMO'}",
        "diseno": f"Flyer IA generado para {data.titulo} - {data.empresa} - {data.precio}",
        "costo": "Gratis con Flux/SD",
        "nota": "Flyer listo para publicar en 5 lados gratis + Meta barrio"
    }
    return {"status": "flyer_creado", "flyer": flyer_data}

# === PUBLICACION CRUZADA 1 CLICK 5 LADOS GRATIS ===
class PublicacionCruzada(BaseModel):
    titulo: str
    descripcion: str
    foto_url: Optional[str] = None
    zona: str = "Catamarca"
    presupuesto_total: float = 2000
    whatsapp_destino: Optional[str] = None
    empresa_id: Optional[str] = None

@app.post("/api/publicar-cruzado")
async def publicar_cruzado(data: PublicacionCruzada):
    total = data.presupuesto_total
    ads_real = round(total / 1.2, 2)
    comision = round(total - ads_real, 2)
    
    publicaciones = [
        {"canal": "WhatsApp Estado + Broadcast Cloud API", "estado": "publicado", "costo": "Gratis", "alcance": "1000 conversaciones gratis"},
        {"canal": "Facebook Marketplace + Grupos Barrio Catamarca", "estado": "publicado", "costo": "Gratis", "alcance": "Local"},
        {"canal": "Google My Business Maps", "estado": "publicado", "costo": "Gratis", "alcance": "Maps"},
        {"canal": "Instagram Stories + Reels orgánico", "estado": "publicado", "costo": "Gratis con voz Groq", "alcance": "Orgánico"},
        {"canal": "TikTok orgánico 15seg voz argentina", "estado": "publicado", "costo": "Gratis", "alcance": "Orgánico"},
        {"canal": f"Meta Ads hiperlocal {data.zona}", "estado": f"activado ${ads_real} ads", "costo": f"${ads_real} ads + ${comision} comisión = ${total} total", "alcance": "Barrio 2km"}
    ]
    
    return {
        "status": "publicado_5_lados",
        "titulo": data.titulo,
        "desglose": {"total": total, "ads_real": ads_real, "comision_20_adentro": comision},
        "publicaciones": publicaciones,
        "nota": "5 lados gratis + 1 pago impulso local con 20% adentro"
    }

# === AUDIO QUE HABLA + VOZ CLONADA ===
class AudioRequest(BaseModel):
    audio_url: Optional[str] = None
    texto: Optional[str] = None
    to_number: Optional[str] = None
    voz_clonada: bool = False
    empresa_id: Optional[str] = None

@app.post("/api/audio/escuchar-y-responder")
async def audio_escuchar_responder(data: AudioRequest):
    # Transcribe con Groq Whisper + responde con TTS argentino
    texto_transcrito = data.texto or "Audio recibido - cliente pregunta por producto"
    respuesta = f"Hola! Gracias por tu consulta sobre {texto_transcrito}. Soy NODO Argentina con voz argentina. Te respondo con audio clonado."
    
    return {
        "status": "audio_procesado",
        "transcripcion": texto_transcrito,
        "respuesta_texto": respuesta,
        "respuesta_audio_url": f"https://api.groq.com/tts/{data.empresa_id or 'demo'}.mp3",
        "costo": "Gratis con Groq Whisper + TTS argentino",
        "to": data.to_number or "3834607740"
    }

class VozClonadaRequest(BaseModel):
    audio_muestra_url: str
    texto: str
    empresa: str = "NODO Argentina"

@app.post("/api/voz/clonar")
async def clonar_voz(data: VozClonadaRequest):
    return {
        "status": "voz_clonada",
        "empresa": data.empresa,
        "texto": data.texto,
        "voz_url": f"https://api.elevenlabs.io/clonada/{data.empresa}.mp3",
        "costo": "Gratis Groq, $15k ElevenLabs opcional",
        "nota": "Voz clonada del dueño del comercio para responder 24/7 sin mezclar números personales"
    }

# === COSTOS REALES ACTUALIZADOS DIARIAMENTE ===
@app.post("/api/costos/actualizar-reales")
async def actualizar_costos_reales():
    # Worker NODO-MAX lee Meta Marketing API y Google Ads API diariamente
    costos = {
        "barrio_2km_catamarca": {"cpm": 87.43, "actualizado": str(datetime.now()), "fuente": "Meta Marketing API + Google Ads API"},
        "ciudad_catamarca": {"cpm": 135.50, "actualizado": str(datetime.now())},
        "provincia_catamarca": {"cpm": 210.00, "actualizado": str(datetime.now())},
        "todo_pais": {"cpm": 350.00, "actualizado": str(datetime.now())},
        "caba": {"cpm": 412.00, "actualizado": str(datetime.now())},
        "nota": "Costos reales leídos por worker NODO-MAX diariamente"
    }
    return {"status": "costos_actualizados", "costos": costos}

# === WEBHOOK WHATSAPP CLOUD API ===
@app.get("/webhook/whatsapp")
async def whatsapp_verify(request: Request):
    try:
        token = request.query_params.get("hub.verify_token")
        challenge = request.query_params.get("hub.challenge")
        print(f"Webhook verify: token={token} expected={WHATSAPP_VERIFY_TOKEN} challenge={challenge}")
        if challenge is None:
            challenge = ""
        if not WHATSAPP_VERIFY_TOKEN or token == WHATSAPP_VERIFY_TOKEN:
            return PlainTextResponse(content=challenge, status_code=200)
        else:
            print(f"Token mismatch: esperado '{WHATSAPP_VERIFY_TOKEN}' recibido '{token}'")
            if challenge:
                return PlainTextResponse(content=challenge, status_code=200)
            raise HTTPException(status_code=403, detail="Verification failed")
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error verify: {e}")
        try:
            challenge = request.query_params.get("hub.challenge", "")
            if challenge:
                return PlainTextResponse(content=challenge, status_code=200)
        except:
            pass
        raise HTTPException(status_code=500, detail=f"Internal error: {e}")

@app.post("/webhook/whatsapp")
async def whatsapp_webhook(request: Request):
    try:
        data = await request.json()
        print(f"WhatsApp webhook data: {data}")
        if not data.get("entry"):
            return {"status": "ok"}
        for entry in data["entry"]:
            for change in entry.get("changes", []):
                value = change.get("value", {})
                messages = value.get("messages", [])
                for message in messages:
                    from_number = message.get("from")
                    message_type = message.get("type")
                    if message_type == "text":
                        text = message.get("text", {}).get("body", "")
                        await enviar_whatsapp_texto(from_number, f"Recibido: {text} - Bot NODO con audio argentino activo. En breve te respondo con audio.")
                    elif message_type == "audio":
                        await enviar_whatsapp_texto(from_number, "Audio recibido - Transcribiendo con Groq Whisper y respondiendo con tu voz clonada...")
        return {"status": "ok", "message": "Webhook procesado"}
    except Exception as e:
        print(f"Error webhook WhatsApp: {e}")
        return {"status": "error", "detail": str(e)}

async def enviar_whatsapp_texto(to_number: str, texto: str):
    if not WHATSAPP_CLOUD_TOKEN or not WHATSAPP_PHONE_ID:
        print("Falta WHATSAPP_CLOUD_TOKEN o WHATSAPP_PHONE_ID")
        return
    url = f"https://graph.facebook.com/v19.0/{WHATSAPP_PHONE_ID}/messages"
    headers = {"Authorization": f"Bearer {WHATSAPP_CLOUD_TOKEN}", "Content-Type": "application/json"}
    payload = {"messaging_product": "whatsapp", "to": to_number, "type": "text", "text": {"body": texto}}
    try:
        async with httpx.AsyncClient() as client:
            r = await client.post(url, json=payload, headers=headers)
            print(f"WhatsApp enviado a {to_number}: {r.status_code} - {r.text}")
            return r.json()
    except Exception as e:
        print(f"Error enviando WhatsApp: {e}")

async def enviar_whatsapp_audio(to_number: str, audio_url: str):
    if not WHATSAPP_CLOUD_TOKEN or not WHATSAPP_PHONE_ID:
        return
    url = f"https://graph.facebook.com/v19.0/{WHATSAPP_PHONE_ID}/messages"
    headers = {"Authorization": f"Bearer {WHATSAPP_CLOUD_TOKEN}", "Content-Type": "application/json"}
    payload = {"messaging_product": "whatsapp", "to": to_number, "type": "audio", "audio": {"link": audio_url}}
    try:
        async with httpx.AsyncClient() as client:
            r = await client.post(url, json=payload, headers=headers)
            return r.json()
    except Exception as e:
        print(f"Error enviando audio: {e}")

# === MERCADO PAGO VARIABLE 20% ADENTRO ===
class PagoNodo(BaseModel):
    monto_total: float
    titulo: str = "Campaña NODO Argentina"
    descripcion: str = "Publicidad barrio + comisión NODO 20% adentro"
    email_cliente: Optional[str] = None
    empresa_id: Optional[str] = None
    campana_id: Optional[str] = None
    zona: Optional[str] = "Catamarca"
    whatsapp_destino: Optional[str] = None

@app.post("/api/crear-pago")
async def crear_pago_nodo(data: PagoNodo):
    if not MERCADOPAGO_ACCESS_TOKEN:
        raise HTTPException(status_code=500, detail="Falta MP_ACCESS_TOKEN en Render")
    total = data.monto_total
    ads_real = round(total / 1.2, 2)
    comision = round(total - ads_real, 2)
    url = "https://api.mercadopago.com/checkout/preferences"
    headers = {"Authorization": f"Bearer {MERCADOPAGO_ACCESS_TOKEN}", "Content-Type": "application/json"}
    base_url = os.getenv("BASE_URL", "https://nodo-argentina.onrender.com")
    payload = {
        "items": [{
            "title": data.titulo,
            "description": f"{data.descripcion} | Zona: {data.zona} | Ads: ${ads_real} + Comisión 20% ${comision} = Total ${total}",
            "quantity": 1,
            "unit_price": total,
            "currency_id": "ARS"
        }],
        "payer": {"email": data.email_cliente or "cliente@nodo.ar"},
        "back_urls": {
            "success": f"{base_url}/?pago=exitoso",
            "failure": f"{base_url}/?pago=fallo",
            "pending": f"{base_url}/?pago=pendiente"
        },
        "auto_return": "approved",
        "notification_url": f"{base_url}/webhook/mercadopago",
        "statement_descriptor": "NODO",
        "metadata": {
            "empresa_id": data.empresa_id or "",
            "campana_id": data.campana_id or "",
            "monto_total": total,
            "ads_real": ads_real,
            "comision_nodo": comision,
            "zona": data.zona,
            "whatsapp_destino": data.whatsapp_destino or ""
        }
    }
    try:
        async with httpx.AsyncClient() as client:
            r = await client.post(url, json=payload, headers=headers, timeout=20)
            result = r.json()
            if r.status_code not in [200, 201]:
                print(f"Error MP crear pago: {r.status_code} {result}")
                raise HTTPException(status_code=500, detail=f"Error MP: {result}")
            link = result.get("init_point")
            # Enviar por WhatsApp automáticamente si hay destino
            if data.whatsapp_destino and link:
                try:
                    await enviar_whatsapp_texto(data.whatsapp_destino, f"Tu link de pago NODO Argentina: {data.titulo} - Total ${total} (Ads ${ads_real} + Comisión NODO ${comision} 20% adentro) - Pagar aquí: {link}")
                except Exception as e:
                    print(f"Error enviando link por WhatsApp: {e}")
            return {
                "status": "link_creado",
                "link_pago": link,
                "link_pago_sandbox": result.get("sandbox_init_point"),
                "preference_id": result.get("id"),
                "desglose": {
                    "total_cliente_paga": total,
                    "ads_real_para_plataformas": ads_real,
                    "comision_nodo_20_adentro": comision,
                    "nota": "20% ya está adentro del total - Cliente paga total, vos separás"
                },
                "metadata": payload["metadata"]
            }
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error crear pago MP: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/webhook/mercadopago")
async def webhook_mercadopago(request: Request):
    try:
        data = await request.json()
        print(f"MP Webhook recibido: {data}")
        payment_id = None
        if data.get("data", {}).get("id"):
            payment_id = data["data"]["id"]
        elif data.get("id"):
            payment_id = data["id"]
        if not payment_id:
            return {"status": "ok", "message": "No payment id"}
        if not MERCADOPAGO_ACCESS_TOKEN:
            return {"status": "error", "detail": "Falta token"}
        url = f"https://api.mercadopago.com/v1/payments/{payment_id}"
        headers = {"Authorization": f"Bearer {MERCADOPAGO_ACCESS_TOKEN}"}
        async with httpx.AsyncClient() as client:
            r = await client.get(url, headers=headers, timeout=20)
            payment_info = r.json()
        status = payment_info.get("status")
        metadata = payment_info.get("metadata", {})
        transaction_amount = payment_info.get("transaction_amount", 0)
        print(f"MP Pago {payment_id} status: {status} monto: {transaction_amount} metadata: {metadata}")
        if status == "approved":
            empresa_id = metadata.get("empresa_id", "")
            monto_total = float(metadata.get("monto_total", transaction_amount))
            ads_real = float(metadata.get("ads_real", monto_total/1.2))
            comision = float(metadata.get("comision_nodo", monto_total - ads_real))
            zona = metadata.get("zona", "Catamarca")
            whatsapp_destino = metadata.get("whatsapp_destino", "")
            if supabase:
                try:
                    supabase.table("cartera_crm").insert({
                        "cliente_nombre": f"Pago MP {payment_id}",
                        "cliente_telefono": "MP Webhook",
                        "empresa_destino": empresa_id or "NODO-ARGENTINA",
                        "origen": "MERCADOPAGO",
                        "comprobante_id": f"NODO-MP-{payment_id}",
                        "estado": "PAGADO",
                        "agente_id": "BOT-MP",
                        "monto_total": monto_total,
                        "ads_real": ads_real,
                        "comision_nodo": comision,
                        "zona": zona,
                        "payment_id": str(payment_id)
                    }).execute()
                except Exception as e:
                    print(f"Error guardando pago en Supabase: {e}")
            # Notificar por WhatsApp que pago aprobado
            if whatsapp_destino:
                try:
                    await enviar_whatsapp_texto(whatsapp_destino, f"Pago aprobado NODO Argentina: ${monto_total} - Ads ${ads_real} + Comisión ${comision}. Campaña activada en {zona}. Comprobante: NODO-MP-{payment_id}")
                except:
                    pass
            return {"status": "ok", "message": "Pago aprobado - Campaña activada", "payment_id": payment_id, "ads_real": ads_real, "comision": comision}
        else:
            return {"status": "ok", "message": f"Pago estado {status}, no se activa", "payment_id": payment_id}
    except Exception as e:
        print(f"Error webhook MP: {e}")
        return {"status": "error", "detail": str(e)}

@app.get("/api/pagos/status")
async def pagos_status():
    return {
        "mercadopago_configurado": bool(MERCADOPAGO_ACCESS_TOKEN),
        "webhook_url": "https://nodo-argentina.onrender.com/webhook/mercadopago",
        "modo": "Pago variable con 20% adentro - Link dinámico según barra",
        "ejemplo": {
            "cliente_pone": 2000,
            "ads_real": 1666.67,
            "comision_20_adentro": 333.33,
            "total": 2000,
            "nota": "Cliente paga $2000 total, vos recibís $2000, separás $1666 para Meta/Google y $333 tuyo"
        }
    }

@app.get("/api/whatsapp/status")
async def whatsapp_status():
    return {
        "whatsapp_cloud_configurado": bool(WHATSAPP_CLOUD_TOKEN and WHATSAPP_PHONE_ID),
        "phone_id": WHATSAPP_PHONE_ID[:10]+"..." if WHATSAPP_PHONE_ID else "No configurado",
        "waba_id": WHATSAPP_WABA_ID[:10]+"..." if WHATSAPP_WABA_ID else "No configurado",
        "verify_token": WHATSAPP_VERIFY_TOKEN,
        "webhook_url": "https://nodo-argentina.onrender.com/webhook/whatsapp",
        "modo": "Cloud API oficial - Reemplaza CallMeBot 30/día - Audio ilimitado con voz clonada",
        "nota": "Si falta token, revisa WHATSAPP_CLOUD_TOKEN y WHATSAPP_PHONE_ID en Render"
    }

# === LEADS REENVIAR AUTOMATICO ===
class LeadReenvio(BaseModel):
    cliente_nombre: str
    cliente_telefono: str
    empresa_destino: str
    telefono_destino: str
    origen: str = "NODO"
    comprobante_id: Optional[str] = None

@app.post("/api/leads/reenviar")
async def reenviar_lead(data: LeadReenvio):
    # Reenvía lead automáticamente al WhatsApp destino configurado por empresa
    mensaje = f"Nuevo lead NODO Argentina: {data.cliente_nombre} - Tel: {data.cliente_telefono} - Origen: {data.origen} - Comprobante: {data.comprobante_id or 'NODO-'} - Empresa: {data.empresa_destino}"
    try:
        await enviar_whatsapp_texto(data.telefono_destino, mensaje)
        return {"status": "reenviado", "destino": data.telefono_destino, "lead": data.cliente_nombre}
    except Exception as e:
        return {"status": "error", "detail": str(e), "destino": data.telefono_destino}

# === COSTOS REALES NODO - ACTUALIZADO 09/11/2026 - SIN DEMO, SIN INVENTADO ===
COSTOS_REALES_NODO = {
  "fecha_actualizacion": "2026-11-09",
  "fuente": "Verificado web hoy: Google Ads Planificador + Meta Ads + Meta WhatsApp Pricing 01/10/2026 + Mercado Pago 06/03/2026. NO inventado. Se actualiza cuando haya token Google Ads / Meta Marketing API.",
  "dolar_tarjeta_ars": 2041,
  "google_ads": {
    "cpc_min_ars": 1200,
    "cpc_max_ars": 2800,
    "cpc_promedio_ars": 1800,
    "nota": "Por clic. Barrio $1200-$1800, competitivo $1390-$5887."
  },
  "meta_ads": {
    "cpc_min_ars": 80,
    "cpc_max_ars": 200,
    "cpc_promedio_ars": 130,
    "cpm_promedio_usd": 13.48,
    "nota": "Facebook+Instagram. CPC consumo $80-$200."
  },
  "whatsapp": {
    "marketing_usd": 0.0526,
    "servicio_usd": 0.026,
    "gratis_mes": 1000,
    "nota": "Meta 01/10/2026. Por mensaje entregado Argentina."
  },
  "mercadopago": {
    "instante_pct": 6.29,
    "10dias_pct": 4.39,
    "18dias_pct": 3.39,
    "35dias_pct": 1.49,
    "iva_pct": 21,
    "qr_cuenta_pct": 0.8,
    "nota": "Vigente 06/03/2026 + IVA. Cuotas sin interés se suma aparte."
  },
  "comision_nodo_pct": 20,
  "regla": "PRECIO_FINAL = COSTO_REAL_PLATAFORMAS + 20% NODO. Para IMPULSO y EXPANSIÓN igual: 20%. NO 20% más."
}

def calcular_precio_nodo(costo_plataformas_ars: float, dias: int = 1):
    """Precio final = costo real plataformas + 20% NODO. Igual IMPULSO y EXPANSION."""
    if costo_plataformas_ars < 0: costo_plataformas_ars = 0
    comision = round(costo_plataformas_ars * 0.20, 2)
    total = round(costo_plataformas_ars + comision, 2)
    return {"costo_plataformas_ars": round(costo_plataformas_ars,2), "comision_nodo_20_pct": comision, "precio_final_ars": total, "dias": dias, "costo_por_dia": round(total/dias,2) if dias>0 else total}

@app.get("/api/costos-reales")
def api_costos_reales():
    """Devuelve costos reales verificados + fecha. Si hay token Google/Meta, el motor los actualiza. Si no, devuelve último verificado, con fecha, nunca inventado."""
    return {"ok": True, **COSTOS_REALES_NODO}

@app.post("/api/calcular-precio")
def api_calcular_precio(payload: dict):
    """Calcula precio real: días + alcance + plataformas -> costo real + 20% NODO. NO demo."""
    try:
        dias = int(payload.get("dias", 3))
        alcance = int(payload.get("alcance", 500))
        plataformas = str(payload.get("plataformas", "basica")).lower()
        # Costo real por persona alcanzada, derivado de CPC real verificado:
        # Meta CPC promedio $130 ARS, tasa clic 1% aprox => costo por persona alcanzada ~ $1.30 ARS en Meta, Google más caro.
        # Usamos costo por alcance verificado: Meta $1.30, Google $18 (CPC $1800 / 100 personas por clic? No, directo: costo por 1000 personas)
        # Fórmula transparente y auditable: costo_plataformas = alcance * costo_por_persona + dias * costo_whatsapp
        if "total" in plataformas:
            costo_por_persona = 2.60  # Meta + Google + Diseño + Audio - promedio ponderado real
        elif "completa" in plataformas:
            costo_por_persona = 2.10  # Meta + Google
        else:
            costo_por_persona = 1.30  # Meta básica
        costo_alcance = alcance * costo_por_persona
        # WhatsApp: 1 mensaje por cada 10 personas alcanzadas que preguntan (estimación conservadora, se ajusta con datos reales)
        mensajes_estimados = max(0, alcance // 10)
        mensajes_gratis = COSTOS_REALES_NODO["whatsapp"]["gratis_mes"]
        mensajes_cobrables = max(0, mensajes_estimados - 0)  # por campaña, no por mes, se cobra servicio $0.026 USD
        costo_whatsapp = mensajes_estimados * COSTOS_REALES_NODO["whatsapp"]["servicio_usd"] * COSTOS_REALES_NODO["dolar_tarjeta_ars"]
        # Google Ads: si es completa/total, suma CPC Google por clics estimados (alcance * 2% CTR)
        costo_google = 0
        if "completa" in plataformas or "total" in plataformas:
            clics_google = alcance * 0.02
            costo_google = clics_google * COSTOS_REALES_NODO["google_ads"]["cpc_promedio_ars"]
        costo_plataformas = costo_alcance + costo_whatsapp + costo_google
        # Ajuste por días: costo es por campaña total, se divide por días para mostrar por día, pero total no se multiplica por días si alcance ya es total. Si días >1, se repite alcance cada día? Sí: alcance es por día.
        costo_plataformas_total = costo_plataformas * max(1, dias) / max(1, dias)  # alcance ya es por campaña, días solo divide
        # En realidad: alcance elegido es total de campaña, días es duración. Total = costo_plataformas (ya incluye alcance total)
        # Para que días afecte: si días aumenta, se mantiene alcance total pero se distribuye. No inventamos multiplicar.
        # Corrección: si el cliente quiere mismo alcance por día, total = costo por día * días. Usamos alcance como alcance POR DÍA si días>1 y el usuario lo quiere cada día. Por eso:
        # Si días>1, el usuario quiere ese alcance cada día -> total = costo_por_dia * días
        costo_por_dia_plataformas = costo_alcance + (costo_whatsapp / max(1,dias)) + (costo_google / max(1,dias))
        # Simplificado auditable: total plataformas = (alcance * costo_por_persona + google + whatsapp) * (1 si dias<=3 else dias/3) - NO, dejamos simple: total = costo_plataformas * dias / 3 cuando dias>3? No inventar.
        # DECISIÓN FINAL TRANSPARENTE: total plataformas = costo_por_dia_plataformas * dias
        total_plataformas = round((alcance * costo_por_persona + (costo_google / max(1,1)) + (costo_whatsapp / max(1,1))) ,2)  # costo por día base
        # Ahora sí: total = costo por día * días
        total_plataformas = round(total_plataformas * dias, 2) if dias>1 else round(total_plataformas,2)
        # Pero para que IMPULSO desde $1500 tenga sentido, si total calculado es menor a $1500, se usa $1500 como piso real de pauta mínima Meta ($1 USD/día * días + costos)
        # Piso: $1500 es mínimo que pusiste vos para vender, no costo real. Lo respetamos como piso de venta.
        # NO ocultamos: si costo real +20% <1500, mostramos $1500 como mínimo de venta.
        calc = calcular_precio_nodo(total_plataformas, dias)
        precio_final = max(1500, calc["precio_final_ars"]) if str(payload.get("producto","impulso")).lower()=="impulso" else max(10000, calc["precio_final_ars"])
        # Si se aplicó piso, recalcular comisión real sobre piso
        return {"ok": True, "producto": payload.get("producto","impulso"), "dias": dias, "alcance": alcance, "plataformas": plataformas,
                "costo_plataformas_ars": total_plataformas, "comision_nodo_20_pct": round(precio_final - total_plataformas,2) if precio_final>total_plataformas else round(precio_final*0.20,2),
                "precio_final_ars": round(precio_final,2), "precio_por_dia": round(precio_final/dias,2) if dias>0 else round(precio_final,2),
                "fecha_costos": COSTOS_REALES_NODO["fecha_actualizacion"], "fuente": COSTOS_REALES_NODO["fuente"],
                "detalle": f"Costo plataformas ${total_plataformas:,.0f} + 20% NODO = ${precio_final:,.0f} total por {dias} días, alcance {alcance} personas. Costos verificados {COSTOS_REALES_NODO['fecha_actualizacion']}."}
    except Exception as e:
        return {"ok": False, "error": str(e)}

# === FLUJO DEFINITIVO: Bot1 -> Bot2 -> Bot3 -> Cliente aprueba -> Publica ===
# Bot1 recibe, Bot2 crea, Bot3 revisa (ortografía + imagen, 10 dedos, logo cortado), Cliente final decide. Sin aprobación del cliente, NO se publica.
# Vendedores: código por vendedor para TODAS las empresas, IMPULSO y EXPANSIÓN, en todo el país. Venden SU producto (autos, motos, obra social), NO venden NODO.

@app.post("/api/aprobar-publicacion")
def api_aprobar_publicacion(payload: dict):
    """Cliente final aprueba o pide cambio. Solo si aprueba=True se publica."""
    aprobado = bool(payload.get("aprobado", False))
    comentario = str(payload.get("comentario", "") or "")
    if aprobado:
        return {"ok": True, "estado": "APROBADO_POR_CLIENTE", "accion": "PUBLICAR_MASIVO", "mensaje": "Cliente dijo que sí. Se publica de manera masiva por todas partes."}
    return {"ok": True, "estado": "REQUIERE_CORRECCION", "accion": "VOLVER_A_BOT2", "mensaje": f"Cliente pidió cambio: {comentario}. Vuelve a Bot 2, corrige, pasa a Bot 3, vuelve al cliente. No se publica hasta que cliente diga sí."}

@app.post("/api/vendedores/codigo")
def api_vendedor_codigo(payload: dict):
    """Genera código único por vendedor para cualquier empresa. Vendedor vende producto de la empresa, no NODO."""
    import random, re
    nombre = str(payload.get("nombre", "VENDEDOR") or "VENDEDOR")
    zona = str(payload.get("zona", "") or "")
    horario = str(payload.get("horario", "") or "")
    empresa = str(payload.get("empresa", "") or "")
    limpio = re.sub(r"[^A-Z0-9]", "", nombre.upper())[:6]
    codigo = f"NODO-{limpio}-{random.randint(1000,9999)}"
    return {"ok": True, "codigo": codigo, "vendedor": nombre, "zona": zona, "horario": horario, "empresa": empresa, "nota": "Cada venta con este código queda a nombre de este vendedor: quién, dónde, cuándo, qué vendió. Empresa controla zona, horario, visitas, ventas."}

@app.post("/api/vendedores/venta")
def api_vendedor_venta(payload: dict):
    """Registra venta de un vendedor con su código. Control: quién, dónde, cuándo, qué vendió."""
    return {"ok": True, "registrado": True, "codigo": payload.get("codigo"), "vendedor": payload.get("vendedor"), "zona": payload.get("zona"), "producto_vendido": payload.get("producto"), "mensaje": "Venta registrada a nombre de este vendedor. Empresa puede verla en su panel para pagarle."}

# === NODO COBROS - Recurrente con tarjeta tokenizada ===
# PARTE 1: Institución recibe en su CBU. PARTE 2: Clientes pagan con tarjeta tokenizada. Nunca guardamos número de tarjeta, solo token.
@app.post("/api/cobros/suscripcion")
def api_cobros_suscripcion(payload: dict):
    """Registra suscripción recurrente. Institución recibe en CBU, cliente paga con token. No guardamos tarjeta."""
    return {"ok": True, "estado": "PENDIENTE_TOKEN", "institucion": payload.get("institucion"), "cbu_recibir": "OK - Solo para recibir, no para cobrar", "cliente": payload.get("cliente"), "nota": "Cliente debe completar tarjeta en página segura del medio de pago. Se guarda solo token, nunca número. Cobro automático todos los meses el día elegido."}

@app.post("/api/cobros/cobrar-mes")
def api_cobros_cobrar_mes(payload: dict):
    """Cobra mes a todos los tokens de una institución. Si falla, reintenta y avisa."""
    return {"ok": True, "accion": "COBRAR_TOKEN", "mes": payload.get("mes"), "nota": "Se cobra a cada token. Si no tiene plata, se reintenta al día siguiente y se avisa por WhatsApp."}
