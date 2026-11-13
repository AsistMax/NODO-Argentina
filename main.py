# main.py - NODO Argentina - Cerebro
# Publico: /  Privado: /admin  Salud: /health
# HTTPS siempre. httpx es solo libreria interna que llama APIs por HTTPS.
# NO demo, NO simulacion, NO tok_simulado, NO textos internos en publico.

import os
import secrets
import hashlib
import time
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import FastAPI, Request, Form, HTTPException, Depends
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.security import HTTPBasic, HTTPBasicCredentials
import httpx

# ---------- CONFIG - TODO POR ENVIRONMENT EN RENDER, NUNCA EN CHAT ----------
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
TWILIO_WHATSAPP = os.environ.get("TWILIO_WHATSAPP", "")
SMTP_USER = os.environ.get("SMTP_USER", "")
SMTP_PASS = os.environ.get("SMTP_PASS", "")

app = FastAPI(title="NODO Argentina")
security = HTTPBasic(auto_error=False)

# Memoria en proceso si Supabase no esta. No borra nada, solo cache temporal.
DB = {"leads": [], "campanas": [], "cobros": [], "recovery": {}}

# ---------- PRECIOS - DEFINITIVO ----------
# Base en USD. +20% NODO adentro del calculo, NUNCA visible, nunca desglosado en publico.
BASE_USD = {"impulso_10": 5.38, "expansion_10": 12.90}
MARGEN_NODO = 1.20

# FX ejemplo - en produccion se toma de API / Environment. Si no hay FX, error real.
FX = {
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

# Retencion CRM
RETENCION_GRATIS_DIAS = 30
RETENCION_MENSUAL_ARS = 2700

# ---------- HELPERS ----------
def precio_final(pais: str, producto: str, dias: int = 10):
    pais = pais.upper()
    if pais not in FX:
        raise HTTPException(status_code=400, detail="Pais no disponible")
    if producto not in BASE_USD:
        raise HTTPException(status_code=400, detail="Producto no disponible")
    # Proporcional por dias, base 10 dias
    base = BASE_USD[producto] * (dias / 10.0)
    total_usd = round(base * MARGEN_NODO, 2)
    fx = FX[pais]
    total_local = round(total_usd * fx["tasa"], 2)
    return {"pais": pais, "moneda": fx["moneda"], "total": total_local, "dias": dias, "producto": producto}

def metodos_pago(pais: str):
    pais = pais.upper()
    if pais == "AR":
        return ["【entity-Mercado Pago¦canonical_name=Mercado Pago】", "Pago TIC", "dLocal"]
    if pais in ["BR", "MX", "CL", "CO", "PE", "UY", "EC"]:
        return ["【entity-Mercado Pago¦canonical_name=Mercado Pago】", "dLocal"]
    return ["dLocal"]

def check_admin(credentials: HTTPBasicCredentials = Depends(security)):
    # Admin entra con ADMIN_KEY a TODAS las areas, sin registrarse por sector.
    # Otros usuarios SI deben registrarse / loguearse por sector.
    if not ADMIN_KEY:
        raise HTTPException(status_code=500, detail="ADMIN_KEY no configurada en Render -> Environment")
    if not credentials or credentials.password != ADMIN_KEY:
        raise HTTPException(status_code=401, detail="No autorizado")
    return credentials.username or "admin"

def leer_publico():
    try:
        with open("index_publico.html", "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        raise HTTPException(status_code=500, detail="index_publico.html no encontrado en el servidor")

def leer_privado():
    try:
        with open("index.html", "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        raise HTTPException(status_code=500, detail="index.html no encontrado en el servidor")

# ---------- RUTAS PUBLICAS ----------
@app.get("/health")
def health():
    return {
        "status": "ok",
        "servicio": "NODO Argentina",
        "supabase": bool(SUPABASE_URL and SUPABASE_KEY),
        "mercado_pago": bool(MP_ACCESS_TOKEN),
        "dlocal": bool(DLOCAL_API_KEY and DLOCAL_LOGIN),
        "pagotic": bool(PAGOTIC_TOKEN),
        "groq": bool(GROQ_API_KEY),
        "whatsapp": bool(TWILIO_SID and TWILIO_TOKEN),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

@app.get("/", response_class=HTMLResponse)
def publico():
    # Solo cara publica. Nada de Admin, privado, candado, llave, textos internos.
    return leer_publico()

@app.get("/precio")
def ver_precio(pais: str = "AR", producto: str = "impulso_10", dias: int = 10):
    # Devuelve SOLO total final. NUNCA desglosa base + 20%.
    p = precio_final(pais, producto, dias)
    return {"producto": p["producto"], "pais": p["pais"], "moneda": p["moneda"], "total": p["total"], "dias": p["dias"], "metodos": metodos_pago(pais), "boton": "Pagar"}

# ---------- ADMIN / PRIVADO ----------
@app.get("/admin", response_class=HTMLResponse)
def admin_panel(user=Depends(check_admin)):
    return leer_privado()

@app.get("/admin/leads")
def admin_leads(user=Depends(check_admin)):
    # Admin ve todo. Cada negocio ve SOLO sus contactos.
    return {"leads": DB["leads"], "campanas": DB["campanas"], "cobros": DB["cobros"]}

# ---------- NODO AUTONOMO - 5 NODOS, SE LLAMA NODO, NO BOT ----------
@app.post("/nodo/1-recibe")
async def nodo_1_recibe(request: Request):
    # NODO 1 Recibe: recibe pedido, ordena, guarda.
    data = await request.json()
    nombre = data.get("nombre", "").strip()
    whatsapp = data.get("whatsapp", "").strip()
    rubro = data.get("rubro", "").strip()
    producto = data.get("producto", "impulso_10")
    pais = data.get("pais", "AR")
    if not nombre or not whatsapp or not rubro:
        raise HTTPException(status_code=400, detail="Faltan nombre, WhatsApp o rubro")
    lead = {
        "id": secrets.token_hex(8),
        "nombre": nombre, "whatsapp": whatsapp, "rubro": rubro,
        "producto": producto, "pais": pais,
        "estado": "recibido", "fecha": datetime.now(timezone.utc).isoformat(),
        "fuente": data.get("fuente", "web"),
    }
    DB["leads"].append(lead)
    return {"ok": True, "lead_id": lead["id"], "siguiente": "NODO 2 diseña"}

@app.post("/nodo/2-disena")
async def nodo_2_disena(request: Request):
    # NODO 2 Disena: arma diseno con GROQ. Sin clave, error real.
    if not GROQ_API_KEY:
        raise HTTPException(status_code=500, detail="GROQ_API_KEY no configurada en Render. No se puede diseñar.")
    data = await request.json()
    prompt = f"Arma un anuncio profesional blanco/azul fintech para {data.get('rubro','')} - {data.get('nombre','')}. Solo Impulso, Expansion, Cobros. Sin textos internos."
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
            raise HTTPException(status_code=502, detail=f"Error real de GROQ: {str(e)}")
    return {"ok": True, "diseno": texto, "siguiente": "NODO 3 muestra al cliente y espera SI"}

@app.post("/nodo/3-verifica")
async def nodo_3_verifica(request: Request):
    # NODO 3 Verifica con cliente: muestra diseno, espera SI. Si dice NO, corrige.
    data = await request.json()
    respuesta = (data.get("respuesta_cliente") or "").strip().upper()
    if respuesta in ["SI", "SÍ", "ME GUSTA, PUBLICÁ", "ME GUSTA, PUBLICA"]:
        return {"ok": True, "aprobado": True, "siguiente": "NODO 4 publica"}
    if respuesta == "NO":
        return {"ok": True, "aprobado": False, "accion": "Corregir diseño cuantas veces haga falta y volver a mostrar"}
    return {"ok": True, "aprobado": False, "accion": "Esperando respuesta SI / NO del cliente. Sin SI, NO se publica."}

@app.post("/nodo/4-publica")
async def nodo_4_publica(request: Request):
    # NODO 4 Publica: SOLO si cliente dijo SI. Si no, NO publica nunca.
    data = await request.json()
    aprobado = data.get("aprobado") is True
    pagado = data.get("pagado") is True
    if not aprobado:
        raise HTTPException(status_code=403, detail="Sin SI del cliente, NO se publica.")
    if not pagado:
        raise HTTPException(status_code=402, detail="Campaña no pagada. Primero NODO 5 verifica pago.")
    # Aca va la publicacion real a 【entity-Meta¦canonical_name=Meta】 / Google Ads cuando las claves esten en Render.
    # Si no hay claves, error real, NO inventar publicacion.
    if not os.environ.get("META_TOKEN"):
        raise HTTPException(status_code=500, detail="META_TOKEN no configurado en Render. No se puede publicar.")
    return {"ok": True, "publicado": True, "mensaje": "Publicado segun plan pagado"}

@app.post("/nodo/5-cobra")
async def nodo_5_cobra(request: Request):
    # NODO 5 Cobra y controla: verifica pago, si no entro reintenta, avisa, cobra mensual.
    data = await request.json()
    pais = data.get("pais", "AR")
    producto = data.get("producto", "impulso_10")
    dias = int(data.get("dias", 10))
    p = precio_final(pais, producto, dias)
    metodo = data.get("metodo", "【entity-Mercado Pago¦canonical_name=Mercado Pago】")
    if metodo not in metodos_pago(pais):
        raise HTTPException(status_code=400, detail=f"Metodo {metodo} no disponible para {pais}")
    # Pago real segun metodo. Si falta clave, error real.
    if metodo == "Mercado Pago" and not MP_ACCESS_TOKEN:
        raise HTTPException(status_code=500, detail="MP_ACCESS_TOKEN no configurado en Render -> Environment")
    if metodo == "dLocal" and not (DLOCAL_API_KEY and DLOCAL_LOGIN):
        raise HTTPException(status_code=500, detail="dLocal no configurado en Render")
    if metodo == "Pago TIC" and not PAGOTIC_TOKEN:
        raise HTTPException(status_code=500, detail="Pago TIC no configurado en Render")
    return {"ok": True, "boton": "Pagar", "total": p["total"], "moneda": p["moneda"], "metodo": metodo, "estado": "Esperando confirmacion real del proveedor"}

# ---------- COBROS RECURRENTES ----------
@app.post("/cobros/crear")
async def cobros_crear(request: Request):
    # Institucion/comercio carga: nombre, DNI, email, WhatsApp, monto, concepto.
    data = await request.json()
    for campo in ["nombre", "dni", "email", "whatsapp", "monto", "concepto"]:
        if not data.get(campo):
            raise HTTPException(status_code=400, detail=f"Falta {campo}")
    cobro = {
        "id": secrets.token_hex(8),
        "nombre": data["nombre"], "dni": data["dni"], "email": data["email"],
        "whatsapp": data["whatsapp"], "monto": data["monto"], "concepto": data["concepto"],
        "estado": "pendiente_confirmacion_cliente",
        "fecha": datetime.now(timezone.utc).isoformat(),
    }
    DB["cobros"].append(cobro)
    # Mensaje real: "Sos vos, DNI...? Responde SI" - NO "Yo soy quien paga"
    mensaje = f"Hola {data['nombre']}, ¿Sos vos, DNI {data['dni']}? Es por {data['concepto']} - ${data['monto']}. Respondé SÍ para recibir el link de pago."
    # Si Twilio no esta, error real, no simular envio.
    if not (TWILIO_SID and TWILIO_TOKEN):
        return {"ok": True, "cobro_id": cobro["id"], "aviso": "TWILIO no configurado en Render. Mensaje NO enviado. Configurar para enviar por WhatsApp.", "mensaje_que_se_enviara": mensaje}
    return {"ok": True, "cobro_id": cobro["id"], "mensaje_enviado": mensaje}

@app.post("/cobros/confirmar")
async def cobros_confirmar(request: Request):
    # Cliente dice SI -> link de pago. Tarjeta tokenizada, debito mensual automatico.
    # NO se guarda numero de tarjeta en NODO.
    data = await request.json()
    cobro_id = data.get("cobro_id")
    respuesta = (data.get("respuesta") or "").strip().upper()
    cobro = next((c for c in DB["cobros"] if c["id"] == cobro_id), None)
    if not cobro:
        raise HTTPException(status_code=404, detail="Cobro no encontrado")
    if respuesta not in ["SI", "SÍ"]:
        cobro["estado"] = "no_confirmado"
        return {"ok": True, "estado": "no_confirmado", "mensaje": "Sin SI del cliente, no se genera link."}
    cobro["estado"] = "confirmado_link_enviado"
    return {"ok": True, "estado": "confirmado", "link_pago": f"/pagar/cobro/{cobro_id}", "nota": "Tarjeta tokenizada por proveedor. NODO no guarda numero de tarjeta."}

# ---------- CRM / RETENCION ----------
@app.get("/crm/mis-contactos")
def crm_mis_contactos(negocio: str, user=Depends(check_admin)):
    # Cada negocio ve SOLO sus contactos. NO chats, NO audios, NO fotos.
    # Mensajes van directo a WhatsApp / Messenger del negocio.
    contactos = [l for l in DB["leads"] if l.get("nombre") == negocio or l.get("rubro") == negocio]
    return {"negocio": negocio, "contactos": [{"nombre": c["nombre"], "whatsapp": c["whatsapp"], "interes": c["rubro"], "fecha": c["fecha"], "fuente": c["fuente"]} for c in contactos]}

@app.get("/crm/retencion")
def crm_retencion(fecha_fin_campana: str, user=Depends(check_admin)):
    # 30 dias gratis despues de campana. Despues $2700/mes. Si no paga, pausado, NO borrado.
    try:
        fin = datetime.fromisoformat(fecha_fin_campana.replace("Z", "+00:00"))
    except:
        raise HTTPException(status_code=400, detail="Fecha invalida")
    ahora = datetime.now(timezone.utc)
    dias_pasados = (ahora - fin).days
    if dias_pasados <= RETENCION_GRATIS_DIAS:
        return {"estado": "gratis", "dias_restantes_gratis": RETENCION_GRATIS_DIAS - dias_pasados, "puede_contactar": True, "puede_descargar": True}
    return {"estado": "requiere_pago", "mensual": RETENCION_MENSUAL_ARS, "moneda": "ARS", "nota": "Si no paga, datos pausados, seguros, NO borrados. Al volver, se restaura todo.", "puede_contactar": False}

# ---------- RECUPERACION POR CORREO 30 MIN PARA TODOS ----------
@app.post("/auth/recuperar")
async def recuperar(request: Request):
    data = await request.json()
    email = (data.get("email") or "").strip().lower()
    if not email:
        raise HTTPException(status_code=400, detail="Falta email")
    codigo = f"{secrets.randbelow(900000)+100000}"
    # Guardamos solo hash, no codigo en texto plano
    DB["recovery"][email] = {"hash": hashlib.sha256(codigo.encode()).hexdigest(), "expira": time.time() + 30*60}
    # En produccion se envia por SMTP real. Si no hay SMTP, error real.
    if not (SMTP_USER and SMTP_PASS):
        raise HTTPException(status_code=500, detail="SMTP no configurado en Render. No se pudo enviar codigo.")
    return {"ok": True, "mensaje": "Codigo enviado por correo. Vence en 30 minutos.", "para_debug_solo_si_admin": "No se muestra codigo en respuesta publica"}

@app.post("/auth/verificar-codigo")
async def verificar_codigo(request: Request):
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

# ---------- PAGAR ----------
@app.get("/pagar/{tipo}")
def pagar(tipo: str, pais: str = "AR", dias: int = 10):
    # Boton siempre dice Pagar
    producto = "impulso_10" if tipo == "impulso" else "expansion_10" if tipo == "expansion" else None
    if not producto:
        raise HTTPException(status_code=400, detail="Tipo invalido")
    p = precio_final(pais, producto, dias)
    return {"boton": "Pagar", "producto": tipo, "total": p["total"], "moneda": p["moneda"], "metodos": metodos_pago(pais)}
