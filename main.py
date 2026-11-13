# main.py - NODO Argentina
# Publica: /  Panel: /admin  Salud: /health

import os
import secrets
import hashlib
import time
import smtplib
from email.message import EmailMessage
from datetime import datetime, timedelta, timezone, date
from typing import Optional

from fastapi import FastAPI, Request, HTTPException, Depends
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.security import HTTPBasic, HTTPBasicCredentials
import httpx

ADMIN_KEY = os.environ.get("ADMIN_KEY", "")
MP_ACCESS_TOKEN = os.environ.get("MP_ACCESS_TOKEN", "")
DLOCAL_API_KEY = os.environ.get("DLOCAL_API_KEY", "")
DLOCAL_LOGIN = os.environ.get("DLOCAL_LOGIN", "")
PAGOTIC_TOKEN = os.environ.get("PAGOTIC_TOKEN", "")
GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "")
SUPABASE_URL = os.environ.get("SUPABASE_URL", "")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY", "")
TWILIO_SID = os.environ.get("TWILIO_SID", "")
TWILIO_TOKEN = os.environ.get("TWILIO_TOKEN", "")
SMTP_USER = os.environ.get("SMTP_USER", "")
SMTP_PASS = os.environ.get("SMTP_PASS", "")
META_TOKEN = os.environ.get("META_TOKEN", "")

app = FastAPI(title="NODO Argentina")
security = HTTPBasic(auto_error=False)

DB = {"leads": [], "campanas": [], "cobros": [], "publicaciones": [], "recovery": {}, "usuarios": []}

BASE_USD = {"impulso_10": 5.38, "expansion_10": 12.90}
_AJUSTE = 1.20

TASAS = {
    "AR": {"moneda": "ARS", "tasa": 1450.0},
    "BR": {"moneda": "BRL", "tasa": 5.45},
    "MX": {"moneda": "MXN", "tasa": 17.10},
    "CL": {"moneda": "CLP", "tasa": 940.0},
    "CO": {"moneda": "COP", "tasa": 4100.0},
    "PE": {"moneda": "PEN", "tasa": 3.75},
    "UY": {"moneda": "UYU", "tasa": 40.5},
    "EC": {"moneda": "USD", "tasa": 1.0},
    "PY": {"moneda": "PYG", "tasa": 7300.0},
    "BO": {"moneda": "BOB", "tasa": 6.96},
    "VE": {"moneda": "VES", "tasa": 36.5},
    "CR": {"moneda": "CRC", "tasa": 520.0},
    "PA": {"moneda": "PAB", "tasa": 1.0},
    "ES": {"moneda": "EUR", "tasa": 0.92},
    "US": {"moneda": "USD", "tasa": 1.0},
}

RETENCION_GRATIS_DIAS = 30
RETENCION_MENSUAL_ARS = 2700

def contar_dias(fecha_inicio: str, fecha_fin: str, modo: str):
    try:
        d1 = date.fromisoformat(fecha_inicio)
        d2 = date.fromisoformat(fecha_fin)
    except Exception:
        return None
    if d2 < d1:
        return None
    total = 0
    d = d1
    while d <= d2:
        wd = d.weekday()
        if modo == "lunes_viernes" and wd <= 4:
            total += 1
        elif modo == "finde" and wd >= 5:
            total += 1
        elif modo == "todos":
            total += 1
        d = d + timedelta(days=1)
    return total

def precio_final(pais: str, producto: str, dias: int = 10):
    pais = pais.upper()
    if pais not in TASAS:
        raise HTTPException(status_code=400, detail="Pais no disponible")
    if producto not in BASE_USD:
        raise HTTPException(status_code=400, detail="Producto no disponible")
    if dias < 1:
        dias = 1
    if dias > 90:
        dias = 90
    base = BASE_USD[producto] * (dias / 10.0)
    total_usd = round(base * _AJUSTE, 2)
    fx = TASAS[pais]
    total_local = round(total_usd * fx["tasa"], 2)
    return {"pais": pais, "moneda": fx["moneda"], "total": total_local, "dias": dias, "producto": producto}

def metodos_pago(pais: str):
    pais = pais.upper()
    if pais == "AR":
        return ["Mercado Pago", "Pago TIC", "dLocal"]
    if pais in ["BR", "MX", "CL", "CO", "PE", "UY", "EC"]:
        return ["Mercado Pago", "dLocal"]
    return ["dLocal"]

def check_admin(credentials: HTTPBasicCredentials = Depends(security)):
    if not ADMIN_KEY:
        raise HTTPException(status_code=500, detail="ADMIN_KEY no configurada en Render")
    if not credentials or credentials.password != ADMIN_KEY:
        raise HTTPException(status_code=401, detail="No autorizado")
    return credentials.username or "admin"

def generar_codigo():
    return f"{secrets.randbelow(900000) + 100000}"

def enviar_correo(destinatario: str, asunto: str, cuerpo: str):
    if not SMTP_USER or not SMTP_PASS:
        raise HTTPException(status_code=500, detail="Correo no configurado en Render")
    msg = EmailMessage()
    msg["From"] = SMTP_USER
    msg["To"] = destinatario
    msg["Subject"] = asunto
    msg.set_content(cuerpo)
    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
        smtp.login(SMTP_USER, SMTP_PASS)
        smtp.send_message(msg)
    return True

def leer_publico():
    try:
        with open("index_publico.html", "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        raise HTTPException(status_code=500, detail="index_publico.html no encontrado")

def leer_privado():
    try:
        with open("index.html", "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        raise HTTPException(status_code=500, detail="index.html no encontrado")

@app.get("/health")
def health():
    return {"ok": True}

@app.get("/", response_class=HTMLResponse)
def publico():
    return leer_publico()

@app.get("/admin", response_class=HTMLResponse)
def admin_panel(user=Depends(check_admin)):
    return leer_privado()

@app.get("/precio")
def ver_precio(pais: str = "AR", producto: str = "impulso_10", dias: int = 10, fecha_inicio: str = "", fecha_fin: str = "", modo: str = "todos"):
    if fecha_inicio and fecha_fin:
        contados = contar_dias(fecha_inicio, fecha_fin, modo)
        if contados is not None and contados > 0:
            dias = contados
    p = precio_final(pais, producto, dias)
    return {"producto": p["producto"], "pais": p["pais"], "moneda": p["moneda"], "total": p["total"], "dias": p["dias"], "metodos": metodos_pago(pais), "boton": "Pagar"}

@app.get("/api/cotizar")
def api_cotizar(pais: str = "AR", producto: str = "impulso_10", dias: int = 10, fecha_inicio: str = "", fecha_fin: str = "", modo: str = "todos"):
    if fecha_inicio and fecha_fin:
        contados = contar_dias(fecha_inicio, fecha_fin, modo)
        if contados is not None and contados > 0:
            dias = contados
    p = precio_final(pais, producto, dias)
    return {"total": p["total"], "moneda": p["moneda"], "dias": p["dias"], "pais": p["pais"], "boton": "Pagar"}

@app.get("/api/metodos-pago")
def api_metodos(pais: str = "AR"):
    return {"pais": pais.upper(), "metodos": metodos_pago(pais), "boton": "Pagar"}

@app.get("/pagar/{tipo}")
def pagar(tipo: str, pais: str = "AR", dias: int = 10):
    producto = "impulso_10" if tipo == "impulso" else "expansion_10" if tipo == "expansion" else None
    if not producto:
        raise HTTPException(status_code=400, detail="Tipo invalido")
    p = precio_final(pais, producto, dias)
    return {"boton": "Pagar", "producto": tipo, "total": p["total"], "moneda": p["moneda"], "metodos": metodos_pago(pais), "dias": p["dias"]}

@app.post("/api/login")
async def api_login(request: Request):
    data = await request.json()
    email = (data.get("email") or "").strip().lower()
    clave = data.get("clave") or ""
    sector = data.get("sector") or "negocio"
    if not email or not clave:
        raise HTTPException(status_code=400, detail="Faltan email y clave")
    if clave == ADMIN_KEY and ADMIN_KEY:
        return {"ok": True, "rol": "admin", "email": email}
    u = next((x for x in DB["usuarios"] if x["email"] == email), None)
    if not u:
        raise HTTPException(status_code=401, detail="Usuario no encontrado")
    if hashlib.sha256(clave.encode()).hexdigest() != u["clave_hash"]:
        raise HTTPException(status_code=401, detail="Clave incorrecta")
    return {"ok": True, "rol": sector, "email": email, "nombre": u["nombre"]}

@app.post("/api/recuperar")
async def api_recuperar(request: Request):
    data = await request.json()
    email = (data.get("email") or "").strip().lower()
    if not email:
        raise HTTPException(status_code=400, detail="Falta email")
    codigo = generar_codigo()
    DB["recovery"][email] = {"hash": hashlib.sha256(codigo.encode()).hexdigest(), "expira": time.time() + 30 * 60}
    try:
        enviar_correo(email, "Codigo de recuperacion NODO", f"Tu codigo es: {codigo}. Vence en 30 minutos.")
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"No se pudo enviar el correo: {str(e)}")
    return {"ok": True, "mensaje": "Codigo enviado por correo. Vence en 30 minutos."}

@app.post("/api/verificar-codigo")
async def api_verificar_codigo(request: Request):
    data = await request.json()
    email = (data.get("email") or "").strip().lower()
    codigo = (data.get("codigo") or "").strip()
    reg = DB["recovery"].get(email)
    if not reg or time.time() > reg["expira"]:
        raise HTTPException(status_code=400, detail="Codigo vencido o no existe")
    if hashlib.sha256(codigo.encode()).hexdigest() != reg["hash"]:
        raise HTTPException(status_code=400, detail="Codigo incorrecto")
    del DB["recovery"][email]
    return {"ok": True, "mensaje": "Codigo correcto. Podes cambiar tu clave."}

@app.post("/api/nodo/chat")
async def api_nodo_chat(request: Request):
    if not GROQ_API_KEY:
        raise HTTPException(status_code=500, detail="GROQ no configurado en Render")
    data = await request.json()
    prompt = f"Arma un anuncio profesional blanco y azul para {data.get('rubro', '')} - {data.get('nombre', '')}. Solo Impulso, Expansion, Cobros."
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            r = await client.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers={"Authorization": f"Bearer {GROQ_API_KEY}"},
                json={"model": "llama-3.1-8b-instant", "messages": [{"role": "user", "content": prompt}]},
            )
            r.raise_for_status()
            texto = r.json()["choices"][0]["message"]["content"]
        except Exception as e:
            raise HTTPException(status_code=502, detail=f"Error de GROQ: {str(e)}")
    pub_id = secrets.token_hex(8)
    DB["publicaciones"].append({"id": pub_id, "texto": texto, "rubro": data.get("rubro", ""), "nombre": data.get("nombre", ""), "aprobado": False, "fecha": datetime.now(timezone.utc).isoformat()})
    return {"ok": True, "respuesta": texto, "publicacion_id": pub_id}

@app.post("/api/publicaciones")
async def api_publicaciones(request: Request):
    data = await request.json()
    pub_id = secrets.token_hex(8)
    pub = {"id": pub_id, "nombre": data.get("nombre", ""), "rubro": data.get("rubro", ""), "texto": data.get("texto", ""), "aprobado": False, "fecha": datetime.now(timezone.utc).isoformat()}
    DB["publicaciones"].append(pub)
    return {"ok": True, "publicacion_id": pub_id, "publicacion": pub}

@app.post("/api/aprobar")
async def api_aprobar(request: Request):
    data = await request.json()
    pub_id = data.get("publicacion_id")
    aprobado = data.get("aprobado") is True
    pub = next((p for p in DB["publicaciones"] if p["id"] == pub_id), None)
    if not pub:
        raise HTTPException(status_code=404, detail="Publicacion no encontrada")
    if not aprobado:
        pub["aprobado"] = False
        return {"ok": True, "aprobado": False, "mensaje": "No aprobado. Se corrige y se vuelve a mostrar."}
    pub["aprobado"] = True
    return {"ok": True, "aprobado": True, "mensaje": "Aprobado. Ahora se puede pagar y publicar."}

@app.post("/nodo/1-recibe")
async def nodo_1_recibe(request: Request):
    data = await request.json()
    nombre = (data.get("nombre") or "").strip()
    whatsapp = (data.get("whatsapp") or "").strip()
    rubro = (data.get("rubro") or "").strip()
    if not nombre or not whatsapp or not rubro:
        raise HTTPException(status_code=400, detail="Faltan nombre, WhatsApp o rubro")
    lead = {"id": secrets.token_hex(8), "nombre": nombre, "whatsapp": whatsapp, "rubro": rubro, "producto": data.get("producto", "impulso_10"), "pais": data.get("pais", "AR"), "estado": "recibido", "fecha": datetime.now(timezone.utc).isoformat(), "fuente": data.get("fuente", "web")}
    DB["leads"].append(lead)
    return {"ok": True, "lead_id": lead["id"]}

@app.post("/nodo/2-disena")
async def nodo_2_disena(request: Request):
    return await api_nodo_chat(request)

@app.post("/nodo/3-verifica")
async def nodo_3_verifica(request: Request):
    data = await request.json()
    respuesta = (data.get("respuesta_cliente") or "").strip().upper()
    if respuesta in ["SI", "ME GUSTA, PUBLICA"]:
        return {"ok": True, "aprobado": True}
    if respuesta == "NO":
        return {"ok": True, "aprobado": False, "accion": "Corregir y volver a mostrar"}
    return {"ok": True, "aprobado": False, "accion": "Esperando SI o NO del cliente"}

@app.post("/nodo/4-publica")
async def nodo_4_publica(request: Request):
    data = await request.json()
    aprobado = data.get("aprobado") is True
    pagado = data.get("pagado") is True
    if not aprobado:
        raise HTTPException(status_code=403, detail="Sin SI del cliente, NO se publica.")
    if not pagado:
        raise HTTPException(status_code=402, detail="Campana no pagada.")
    if not META_TOKEN:
        raise HTTPException(status_code=500, detail="META_TOKEN no configurado en Render")
    return {"ok": True, "publicado": True}

@app.post("/nodo/5-cobra")
async def nodo_5_cobra(request: Request):
    data = await request.json()
    pais = data.get("pais", "AR")
    producto = data.get("producto", "impulso_10")
    dias = int(data.get("dias", 10))
    p = precio_final(pais, producto, dias)
    metodo = data.get("metodo", "【entity-Mercado Pago¦canonical_name=Mercado Pago】")
    if metodo not in metodos_pago(pais):
        raise HTTPException(status_code=400, detail=f"Metodo {metodo} no disponible para {pais}")
    if metodo == "Mercado Pago" and not MP_ACCESS_TOKEN:
        raise HTTPException(status_code=500, detail="MP_ACCESS_TOKEN no configurado en Render")
    if metodo == "dLocal" and not (DLOCAL_API_KEY and DLOCAL_LOGIN):
        raise HTTPException(status_code=500, detail="dLocal no configurado en Render")
    if metodo == "Pago TIC" and not PAGOTIC_TOKEN:
        raise HTTPException(status_code=500, detail="Pago TIC no configurado en Render")
    return {"ok": True, "boton": "Pagar", "total": p["total"], "moneda": p["moneda"], "metodo": metodo, "estado": "Esperando confirmacion del proveedor"}

@app.post("/api/cobros")
async def api_cobros(request: Request):
    data = await request.json()
    for campo in ["nombre", "dni", "email", "whatsapp", "monto", "concepto"]:
        if not data.get(campo):
            raise HTTPException(status_code=400, detail=f"Falta {campo}")
    cobro = {"id": secrets.token_hex(8), "nombre": data["nombre"], "dni": data["dni"], "email": data["email"], "whatsapp": data["whatsapp"], "monto": data["monto"], "concepto": data["concepto"], "estado": "pendiente_confirmacion", "fecha": datetime.now(timezone.utc).isoformat()}
    DB["cobros"].append(cobro)
    mensaje = f"Hola {data['nombre']}, Sos vos, DNI {data['dni']}? Es por {data['concepto']} - {data['monto']}. Responde SI para recibir el link de pago."
    return {"ok": True, "cobro_id": cobro["id"], "mensaje_que_se_enviara": mensaje}

@app.post("/cobros/crear")
async def cobros_crear(request: Request):
    return await api_cobros(request)

@app.post("/cobros/confirmar")
async def cobros_confirmar(request: Request):
    data = await request.json()
    cobro_id = data.get("cobro_id")
    respuesta = (data.get("respuesta") or "").strip().upper()
    cobro = next((c for c in DB["cobros"] if c["id"] == cobro_id), None)
    if not cobro:
        raise HTTPException(status_code=404, detail="Cobro no encontrado")
    if respuesta not in ["SI"]:
        cobro["estado"] = "no_confirmado"
        return {"ok": True, "estado": "no_confirmado"}
    cobro["estado"] = "confirmado_link_enviado"
    return {"ok": True, "estado": "confirmado", "link_pago": f"/pagar/cobro/{cobro_id}"}

@app.get("/crm/mis-contactos")
def crm_mis_contactos(negocio: str, user=Depends(check_admin)):
    contactos = [l for l in DB["leads"] if l.get("nombre") == negocio or l.get("rubro") == negocio]
    return {"negocio": negocio, "contactos": [{"nombre": c["nombre"], "whatsapp": c["whatsapp"], "interes": c["rubro"], "fecha": c["fecha"], "fuente": c["fuente"]} for c in contactos]}

@app.get("/crm/retencion")
def crm_retencion(fecha_fin_campana: str, user=Depends(check_admin)):
    try:
        fin = datetime.fromisoformat(fecha_fin_campana.replace("Z", "+00:00"))
    except Exception:
        raise HTTPException(status_code=400, detail="Fecha invalida")
    ahora = datetime.now(timezone.utc)
    dias_pasados = (ahora - fin).days
    if dias_pasados <= RETENCION_GRATIS_DIAS:
        return {"estado": "gratis", "dias_restantes_gratis": RETENCION_GRATIS_DIAS - dias_pasados, "puede_contactar": True, "puede_descargar": True}
    return {"estado": "requiere_pago", "mensual": RETENCION_MENSUAL_ARS, "moneda": "ARS", "nota": "Si no paga, datos pausados, seguros, NO borrados. Al volver, se restaura todo.", "puede_contactar": False}

@app.get("/api/admin/resumen")
def api_admin_resumen(user=Depends(check_admin)):
    return {"leads": len(DB["leads"]), "publicaciones": len(DB["publicaciones"]), "cobros": len(DB["cobros"]), "leads_lista": DB["leads"], "cobros_lista": DB["cobros"]}

@app.get("/admin/leads")
def admin_leads(user=Depends(check_admin)):
    return {"leads": DB["leads"], "campanas": DB["campanas"], "cobros": DB["cobros"]}
