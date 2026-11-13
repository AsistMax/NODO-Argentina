# NODO Argentina - main.py FINAL
# Recuperacion PARA TODOS, no solo admin
# Sitio HTTPS siempre. httpx = libreria interna que llama por HTTPS
# Precio USD + 20% adentro, nunca visible
import os, re, secrets, hashlib, smtplib, ssl, uuid
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any, List
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import httpx
from fastapi import FastAPI, Request, HTTPException, Query
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

ADMIN_KEY = os.getenv("ADMIN_KEY", "nodo-arg.2026!")
BASE_URL = os.getenv("BASE_URL", "https://nodo-argentina.onrender.com")
SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_KEY = os.getenv("SUPABASE_KEY", "")
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
META_ACCESS_TOKEN = os.getenv("META_ACCESS_TOKEN", "")
MP_ACCESS_TOKEN = os.getenv("MP_ACCESS_TOKEN", "")
DLOCAL_API_KEY = os.getenv("DLOCAL_API_KEY", "")
DLOCAL_API_SECRET = os.getenv("DLOCAL_API_SECRET", "")
GOOGLE_ADS_DEVELOPER_TOKEN = os.getenv("GOOGLE_ADS_DEVELOPER_TOKEN", "")
GOOGLE_ADS_REFRESH_TOKEN = os.getenv("GOOGLE_ADS_REFRESH_TOKEN", "")
WHATSAPP_CLOUD_TOKEN = os.getenv("WHATSAPP_CLOUD_TOKEN", "")
WHATSAPP_PHONE_ID = os.getenv("WHATSAPP_PHONE_ID", "")
WHATSAPP_VERIFY_TOKEN = os.getenv("WHATSAPP_VERIFY_TOKEN", "")
SMTP_CORREO = os.getenv("SMTP_CORREO", "")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")
SMTP_HOST = os.getenv("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))

app = FastAPI(title="NODO Argentina", version="25.0-final")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])
if os.path.exists("assets"):
    app.mount("/assets", StaticFiles(directory="assets"), name="assets")

USUARIOS_DB: Dict[str, Dict[str, Any]] = {}
CODIGOS: Dict[str, Dict[str, Any]] = {}
CONTACTOS_DB: List[Dict[str, Any]] = []
COBROS_DB: List[Dict[str, Any]] = []
PUBLICACIONES_DB: List[Dict[str, Any]] = []

def ahora():
    return datetime.now(timezone.utc)
def hash_clave(c: str):
    return hashlib.sha256(c.encode("utf-8")).hexdigest()
def es_email(e: str):
    return bool(re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", (e or "").strip()))

PAISES = {
    "AR": {"nombre": "Argentina", "moneda": "ARS", "simbolo": "$", "fx": 1450.0},
    "BR": {"nombre": "Brasil", "moneda": "BRL", "simbolo": "R$", "fx": 5.20},
    "MX": {"nombre": "Mexico", "moneda": "MXN", "simbolo": "$", "fx": 17.50},
    "CL": {"nombre": "Chile", "moneda": "CLP", "simbolo": "$", "fx": 950.0},
    "CO": {"nombre": "Colombia", "moneda": "COP", "simbolo": "$", "fx": 4200.0},
    "PE": {"nombre": "Peru", "moneda": "PEN", "simbolo": "S/", "fx": 3.75},
    "UY": {"nombre": "Uruguay", "moneda": "UYU", "simbolo": "$U", "fx": 40.0},
    "EC": {"nombre": "Ecuador", "moneda": "USD", "simbolo": "$", "fx": 1.0},
    "PY": {"nombre": "Paraguay", "moneda": "PYG", "simbolo": "G", "fx": 7800.0},
    "BO": {"nombre": "Bolivia", "moneda": "BOB", "simbolo": "Bs", "fx": 6.90},
    "VE": {"nombre": "Venezuela", "moneda": "VES", "simbolo": "Bs.", "fx": 36.0},
    "CR": {"nombre": "Costa Rica", "moneda": "CRC", "simbolo": "C", "fx": 520.0},
    "PA": {"nombre": "Panama", "moneda": "PAB", "simbolo": "B/.", "fx": 1.0},
}
PRECIOS = {"impulso": 5.38, "expansion": 12.90, "cobros": 0.0}
def calcular(plan: str, pais: str, dias: int):
    plan = plan.lower().strip(); pais = pais.upper().strip()
    if plan not in PRECIOS: raise ValueError("Plan no valido")
    if pais not in PAISES: pais = "AR"
    dias = max(1, min(90, dias or 10))
    base = (PRECIOS[plan] / 10.0) * dias
    total_usd = round(base * 1.20, 2)
    p = PAISES[pais]
    return {"plan": plan, "pais": p["nombre"], "codigo_pais": pais, "moneda": p["moneda"], "simbolo": p["simbolo"], "dias": dias, "total_usd": total_usd, "total_local": round(total_usd * p["fx"], 2)}

class Reg(BaseModel):
    nombre: str; email: str; clave: str; tipo: str = "negocio"; pais: str = "AR"; whatsapp: Optional[str] = ""; empresa: Optional[str] = ""
class Log(BaseModel):
    email: str; clave: str
class SolRec(BaseModel):
    email: str
class ConfRec(BaseModel):
    email: str; codigo: str; nueva_clave: str
class Contacto(BaseModel):
    negocio_id: str; nombre: str; telefono: Optional[str] = ""; whatsapp: Optional[str] = ""; interes: Optional[str] = ""; fuente: Optional[str] = ""
class Cobro(BaseModel):
    institucion: str; cliente_nombre: str; cliente_dni: str; cliente_email: str; cliente_whatsapp: str; monto: float; concepto: str; pais: str = "AR"
class Pub(BaseModel):
    negocio_id: str; titulo: str; descripcion: str; plan: str = "impulso"; pais: str = "AR"; dias: int = 10
class Aprob(BaseModel):
    publicacion_id: str; aprobado: bool; comentario: Optional[str] = ""
def enviar_correo(dest: str, asunto: str, cuerpo: str) -> bool:
    if not SMTP_CORREO or not SMTP_PASSWORD:
        return False
    try:
        m = MIMEMultipart("alternative")
        m["From"] = SMTP_CORREO
        m["To"] = dest
        m["Subject"] = asunto
        m.attach(MIMEText(cuerpo, "html", "utf-8"))
        ctx = ssl.create_default_context()
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=20) as s:
            s.starttls(context=ctx)
            s.login(SMTP_CORREO, SMTP_PASSWORD)
            s.sendmail(SMTP_CORREO, dest, m.as_string())
        return True
    except Exception:
        return False

def generar_codigo(email: str) -> str:
    codigo = f"{secrets.randbelow(900000) + 100000}"
    CODIGOS[email.lower().strip()] = {"codigo": codigo, "vence_en": ahora() + timedelta(minutes=30), "usado": False}
    return codigo
async def enviar_whatsapp(numero: str, mensaje: str):
    if not WHATSAPP_CLOUD_TOKEN or not WHATSAPP_PHONE_ID:
        return {"ok": False, "error": "WhatsApp no configurado en Render"}
    numero_limpio = re.sub(r"\D", "", numero or "")
    url = f"https://graph.facebook.com/v21.0/{WHATSAPP_PHONE_ID}/messages"
    headers = {"Authorization": f"Bearer {WHATSAPP_CLOUD_TOKEN}", "Content-Type": "application/json"}
    payload = {"messaging_product": "whatsapp", "to": numero_limpio, "type": "text", "text": {"body": mensaje}}
    try:
        async with httpx.AsyncClient(timeout=20.0) as c:
            r = await c.post(url, headers=headers, json=payload)
            if r.status_code in (200, 201):
                return {"ok": True, "respuesta": r.json()}
            return {"ok": False, "error": f"WhatsApp {r.status_code}"}
    except Exception as e:
        return {"ok": False, "error": str(e)}

async def llamar_groq(prompt: str):
    if not GROQ_API_KEY:
        return {"ok": False, "error": "Groq no configurado"}
    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"}
    payload = {"model": "llama-3.3-70b-versatile", "messages": [{"role": "system", "content": "Sos NODO, sistema autonomo de NODO Argentina. Espanol, profesional, claro."}, {"role": "user", "content": prompt}], "temperature": 0.7, "max_tokens": 800}
    try:
        async with httpx.AsyncClient(timeout=30.0) as c:
            r = await c.post(url, headers=headers, json=payload)
            if r.status_code == 200:
                return {"ok": True, "texto": r.json()["choices"][0]["message"]["content"]}
            return {"ok": False, "error": f"Groq {r.status_code}"}
    except Exception as e:
        return {"ok": False, "error": str(e)}

@app.get("/", response_class=HTMLResponse)
async def publica():
    if os.path.exists("index_publico.html"):
        return FileResponse("index_publico.html", media_type="text/html")
    return HTMLResponse("<h1>NODO</h1><p>En mantenimiento.</p>")

@app.get("/admin", response_class=HTMLResponse)
async def privada():
    if os.path.exists("index.html"):
        return FileResponse("index.html", media_type="text/html")
    return HTMLResponse("<h1>NODO Panel</h1>")

@app.get("/health")
async def health():
    return {"ok": True, "servicio": "NODO Argentina", "https": True, "supabase": bool(SUPABASE_URL and SUPABASE_KEY), "mercado_pago": bool(MP_ACCESS_TOKEN), "dlocal": bool(DLOCAL_API_KEY and DLOCAL_API_SECRET), "whatsapp": bool(WHATSAPP_CLOUD_TOKEN), "groq": bool(GROQ_API_KEY), "google_ads": bool(GOOGLE_ADS_DEVELOPER_TOKEN)}

@app.get("/api/paises")
async def paises():
    return {"ok": True, "paises": [{"codigo": k, "nombre": v["nombre"], "moneda": v["moneda"], "simbolo": v["simbolo"]} for k, v in PAISES.items()]}

@app.get("/api/calcular-precio")
async def calc(plan: str = "impulso", pais: str = "AR", dias: int = 10):
    try:
        return {"ok": True, **calcular(plan, pais, dias)}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/api/registro")
async def registro(d: Reg):
    email = d.email.lower().strip()
    if not es_email(email):
        raise HTTPException(status_code=400, detail="Correo no valido")
    if len(d.clave) < 6:
        raise HTTPException(status_code=400, detail="Clave minimo 6")
    if email in USUARIOS_DB:
        raise HTTPException(status_code=400, detail="Ya registrado. Usa Recuperar clave.")
    uid = str(uuid.uuid4())
    USUARIOS_DB[email] = {"id": uid, "nombre": d.nombre.strip(), "email": email, "clave_hash": hash_clave(d.clave), "tipo": d.tipo, "pais": d.pais.upper(), "whatsapp": d.whatsapp or "", "empresa": d.empresa or "", "creado_en": ahora().isoformat(), "activo": True}
    return {"ok": True, "usuario_id": uid}

@app.post("/api/login")
async def login(d: Log):
    email = d.email.lower().strip()
    if email == "admin@nodo.lat" and d.clave == ADMIN_KEY:
        return {"ok": True, "rol": "admin", "email": email, "nombre": "Administrador"}
    u = USUARIOS_DB.get(email)
    if not u or hash_clave(d.clave) != u["clave_hash"]:
        raise HTTPException(status_code=401, detail="Correo o clave incorrectos")
    if not u.get("activo", True):
        raise HTTPException(status_code=403, detail="Cuenta pausada")
    return {"ok": True, "rol": u["tipo"], "usuario_id": u["id"], "nombre": u["nombre"]}

@app.post("/api/recuperar-clave")
async def recuperar(d: SolRec):
    email = d.email.lower().strip()
    if not es_email(email):
        raise HTTPException(status_code=400, detail="Correo no valido")
    codigo = generar_codigo(email)
    cuerpo = f"<h2>NODO - Recuperar clave</h2><p>Tu codigo es:</p><p style='font-size:28px'><b>{codigo}</b></p><p>Vence en 30 minutos.</p>"
    enviado = enviar_correo(email, "NODO - Codigo para recuperar tu clave", cuerpo)
    return {"ok": True, "mensaje": "Si el correo existe, te enviamos un codigo que vence en 30 minutos.", "correo_enviado": enviado}

@app.post("/api/confirmar-recuperacion")
async def confirmar(d: ConfRec):
    email = d.email.lower().strip()
    reg = CODIGOS.get(email)
    if not reg:
        raise HTTPException(status_code=400, detail="No hay codigo. Pedi uno nuevo.")
    if reg["usado"]:
        raise HTTPException(status_code=400, detail="Codigo ya usado. Pedi uno nuevo.")
    if ahora() > reg["vence_en"]:
        raise HTTPException(status_code=400, detail="Codigo vencido. Pedi uno nuevo.")
    if d.codigo.strip() != reg["codigo"]:
        raise HTTPException(status_code=400, detail="Codigo incorrecto")
    if len(d.nueva_clave) < 6:
        raise HTTPException(status_code=400, detail="Clave minimo 6")
    if email == "admin@nodo.lat":
        raise HTTPException(status_code=400, detail="Clave admin se cambia en Render -> Environment -> ADMIN_KEY")
    u = USUARIOS_DB.get(email)
    if not u:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    u["clave_hash"] = hash_clave(d.nueva_clave); reg["usado"] = True
    return {"ok": True, "mensaje": "Clave actualizada. Ya podes iniciar sesion."}
    @app.post("/api/nodo/chat")
async def chat(request: Request):
    b = await request.json(); mensaje = (b.get("mensaje") or "").strip()
    if not mensaje:
        raise HTTPException(status_code=400, detail="Escribi tu mensaje")
    r = await llamar_groq(f"Cliente NODO dice: {mensaje}. Responde como NODO, ayudalo a crear su diseno, ofrece 2 opciones.")
    if not r["ok"]:
        return {"ok": False, "respuesta": "Gracias. NODO recibio tu mensaje y te responde en unos minutos.", "error": r["error"]}
    return {"ok": True, "respuesta": r["texto"]}

@app.post("/api/publicaciones")
async def crear_pub(d: Pub):
    try:
        precio = calcular(d.plan, d.pais, d.dias)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
    pid = str(uuid.uuid4())
    PUBLICACIONES_DB.append({"id": pid, "negocio_id": d.negocio_id, "titulo": d.titulo.strip(), "descripcion": d.descripcion.strip(), "plan": d.plan, "pais": d.pais, "dias": d.dias, "precio": precio, "estado": "pendiente_aprobacion", "creado_en": ahora().isoformat()})
    return {"ok": True, "publicacion_id": pid, "precio": precio, "mensaje": "NODO creo tu borrador. Revisalo y aprobalo."}

@app.post("/api/aprobar-publicacion")
async def aprobar(d: Aprob):
    for p in PUBLICACIONES_DB:
        if p["id"] == d.publicacion_id:
            if d.aprobado:
                p["estado"] = "aprobada_para_publicar"; p["comentario_cliente"] = d.comentario or ""
                return {"ok": True, "mensaje": "Gracias. NODO va a publicar tu diseno."}
            p["estado"] = "necesita_correccion"; p["comentario_cliente"] = d.comentario or ""
            return {"ok": True, "mensaje": "Entendido. NODO corrige y te muestra nueva version."}
    raise HTTPException(status_code=404, detail="Publicacion no encontrada")

@app.get("/api/nodo/estado")
async def estado():
    return {"ok": True, "nodo_1_recibe": True, "nodo_2_disena": bool(GROQ_API_KEY), "nodo_3_verifica": True, "nodo_4_publica": bool(META_ACCESS_TOKEN or GOOGLE_ADS_DEVELOPER_TOKEN), "nodo_5_cobra": bool(MP_ACCESS_TOKEN or DLOCAL_API_KEY)}

@app.post("/api/contactos")
async def crear_contacto(d: Contacto):
    if not d.negocio_id or not d.nombre:
        raise HTTPException(status_code=400, detail="Faltan datos")
    c = {"id": str(uuid.uuid4()), "negocio_id": d.negocio_id, "nombre": d.nombre.strip(), "telefono": d.telefono or "", "whatsapp": d.whatsapp or "", "interes": d.interes or "", "fuente": d.fuente or "", "creado_en": ahora().isoformat()}
    CONTACTOS_DB.append(c)
    return {"ok": True, "contacto": c}

@app.get("/api/contactos")
async def listar_contactos(negocio_id: str = Query(...)):
    if negocio_id == "admin":
        return {"ok": True, "contactos": CONTACTOS_DB, "total": len(CONTACTOS_DB)}
    return {"ok": True, "contactos": [c for c in CONTACTOS_DB if c["negocio_id"] == negocio_id]}

@app.post("/api/cobros/solicitar")
async def solicitar_cobro(d: Cobro):
    if not es_email(d.cliente_email):
        raise HTTPException(status_code=400, detail="Correo cliente no valido")
    if d.monto <= 0:
        raise HTTPException(status_code=400, detail="Monto no valido")
    cid = str(uuid.uuid4())
    mensaje = f"Hola {d.cliente_nombre}, soy NODO. {d.institucion} quiere cobrarte {d.concepto} por {d.monto}. Sos vos, DNI {d.cliente_dni}? Responde SI para recibir el link de pago."
    rws = await enviar_whatsapp(d.cliente_whatsapp, mensaje)
    COBROS_DB.append({"id": cid, "institucion": d.institucion, "cliente_nombre": d.cliente_nombre, "cliente_dni": d.cliente_dni, "cliente_email": d.cliente_email, "cliente_whatsapp": d.cliente_whatsapp, "monto": d.monto, "concepto": d.concepto, "pais": d.pais, "estado": "esperando_SI", "whatsapp_enviado": rws.get("ok", False), "creado_en": ahora().isoformat()})
    return {"ok": True, "cobro_id": cid, "whatsapp": rws}

@app.post("/api/crear-pago-mercadopago")
async def pago_mp(request: Request):
    b = await request.json(); monto = b.get("monto", 0); concepto = (b.get("concepto") or "NODO Publicidad").strip(); email = b.get("email", "")
    if not MP_ACCESS_TOKEN:
        return JSONResponse(status_code=400, content={"ok": False, "error": "【entity-Mercado Pago¦canonical_name=Mercado Pago】 no configurado. Falta MP_ACCESS_TOKEN en Render."})
    if not monto or float(monto) <= 0:
        return JSONResponse(status_code=400, content={"ok": False, "error": "Monto no valido"})
    url = "https://api.mercadopago.com/checkout/preferences"
    headers = {"Authorization": f"Bearer {MP_ACCESS_TOKEN}", "Content-Type": "application/json"}
    payload = {"items": [{"title": concepto, "quantity": 1, "currency_id": "ARS", "unit_price": float(monto)}], "payer": {"email": email}, "back_urls": {"success": f"{BASE_URL}/?pago=ok", "failure": f"{BASE_URL}/?pago=error", "pending": f"{BASE_URL}/?pago=pendiente"}, "auto_return": "approved"}
    try:
        async with httpx.AsyncClient(timeout=20.0) as c:
            r = await c.post(url, headers=headers, json=payload)
            if r.status_code in (200, 201):
                data = r.json()
                return {"ok": True, "link_pago": data.get("init_point"), "id": data.get("id")}
            return JSONResponse(status_code=400, content={"ok": False, "error": f"【entity-Mercado Pago¦canonical_name=Mercado Pago】 {r.status_code}"})
    except Exception as e:
        return JSONResponse(status_code=500, content={"ok": False, "error": str(e)})

@app.post("/api/crear-pago-dlocal")
async def pago_dlocal(request: Request):
    if not DLOCAL_API_KEY or not DLOCAL_API_SECRET:
        return JSONResponse(status_code=400, content={"ok": False, "error": "dLocal no configurado. Falta DLOCAL_API_KEY y DLOCAL_API_SECRET en Render. Cuando los tengas, se activa solo."})
    return {"ok": False, "error": "dLocal listo para conectar. Faltan claves."}

@app.get("/api/metodos-pago")
async def metodos(pais: str = "AR"):
    pais = pais.upper()
    if pais == "AR":
        return {"ok": True, "pais": pais, "metodos": ["【entity-Mercado Pago¦canonical_name=Mercado Pago】", "Pago TIC", "dLocal"], "boton": "Pagar"}
    if pais in ("BR", "MX", "CL", "CO", "PE", "UY", "EC"):
        return {"ok": True, "pais": pais, "metodos": ["【entity-Mercado Pago¦canonical_name=Mercado Pago】", "dLocal"], "boton": "Pagar"}
    return {"ok": True, "pais": pais, "metodos": ["dLocal"], "boton": "Pagar"}

@app.get("/webhook/whatsapp")
async def wv(hub_verify_token: str = Query("", alias="hub.verify_token"), hub_challenge: str = Query("", alias="hub.challenge")):
    if hub_verify_token == WHATSAPP_VERIFY_TOKEN:
        return HTMLResponse(content=hub_challenge, status_code=200)
    raise HTTPException(status_code=403, detail="Token incorrecto")

@app.post("/webhook/whatsapp")
async def wr(request: Request):
    await request.json()
    return {"ok": True, "recibido": True}

@app.post("/webhook/mercadopago")
async def wm(request: Request):
    b = await request.json()
    return {"ok": True, "recibido": True, "tipo": b.get("type", "")}

@app.get("/api/admin/resumen")
async def resumen(clave: str = Query(...)):
    if clave != ADMIN_KEY:
        raise HTTPException(status_code=401, detail="Clave incorrecta")
    return {"ok": True, "total_usuarios": len(USUARIOS_DB), "total_contactos": len(CONTACTOS_DB), "total_cobros": len(COBROS_DB), "total_publicaciones": len(PUBLICACIONES_DB), "config": {"mercado_pago": bool(MP_ACCESS_TOKEN), "dlocal": bool(DLOCAL_API_KEY), "whatsapp": bool(WHATSAPP_CLOUD_TOKEN), "groq": bool(GROQ_API_KEY), "google_ads": bool(GOOGLE_ADS_DEVELOPER_TOKEN), "supabase": bool(SUPABASE_URL)}}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=int(os.getenv("PORT", "10000")), reload=False)
