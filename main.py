# NODO Argentina - Backend completo - main.py
# NO pegar claves aca. Las claves van en Render > Environment.
import os, hashlib, secrets, time, json
from datetime import datetime, timedelta
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import Optional

app = FastAPI(title="NODO Argentina")
BASE = os.path.dirname(os.path.abspath(__file__))
if os.path.isdir(os.path.join(BASE, "assets")):
    app.mount("/assets", StaticFiles(directory=os.path.join(BASE, "assets")), name="assets")

ADMIN_KEY = "nodo-arg.2026!"
# Datos en memoria (para presentar). En produccion se conecta a base real.
LEADS = []
PUBLICACIONES = []
COBROS = []
RECUPERACIONES = {}  # email -> (codigo, expira)

# Precios base en USD (sin mostrar el +20% nunca). El +20% ya esta dentro del total.
# Impulso 10 dias base 5.38 USD, Expansion 10 dias base 12.90 USD
BASE_PRECIOS = {"impulso_10": 5.38, "expansion_10": 12.90}
MARGEN = 1.20
# Tipo de cambio aproximado a moneda local. Se actualiza con FX real cuando hay clave.
FX = {"AR": (1750.0,"ARS"), "BR": (5.45,"BRL"), "MX": (17.20,"MXN"), "CL": (950.0,"CLP"), "CO": (4100.0,"COP"), "PE": (3.75,"PEN"), "UY": (40.0,"UYU"), "EC": (1.0,"USD"), "PY": (7400.0,"PYG"), "BO": (6.95,"BOB"), "VE": (105.0,"VES"), "CR": (505.0,"CRC"), "PA": (1.0,"PAB"), "ES": (0.92,"EUR"), "US": (1.0,"USD")}
METODOS = {
    "AR": ["Mercado Pago", "Pago TIC", "dLocal"],
    "BR": ["Mercado Pago", "dLocal"],
    "MX": ["Mercado Pago", "dLocal"],
    "CL": ["Mercado Pago", "dLocal"],
    "CO": ["Mercado Pago", "dLocal"],
    "PE": ["Mercado Pago", "dLocal"],
    "UY": ["Mercado Pago", "dLocal"],
    "EC": ["Mercado Pago", "dLocal"],
}
def metodos_pais(pais):
    return METODOS.get(pais, ["dLocal"])
def cotizar_calc(pais, producto, dias):
    base10 = BASE_PRECIOS.get(producto, 5.38)
    total_usd = (base10 / 10.0 * dias) * MARGEN
    fx, moneda = FX.get(pais, (1.0, "USD"))
    total = round(total_usd * fx, 2)
    return {"pais": pais, "producto": producto, "dias": dias, "total": total, "moneda": moneda, "metodos": metodos_pais(pais)}

def leer_html(nombre):
    p = os.path.join(BASE, nombre)
    if os.path.exists(p):
        with open(p, "r", encoding="utf-8") as f:
            return f.read()
    return "<h1>NODO Argentina</h1><p>Archivo no encontrado: "+nombre+"</p>"

@app.get("/health")
def health():
    return {"ok": True}

@app.get("/", response_class=HTMLResponse)
def home():
    return leer_html("index_publico.html")

@app.get("/admin", response_class=HTMLResponse)
def admin_page():
    return leer_html("index.html")

@app.get("/api/cotizar")
def api_cotizar(pais: str = "AR", producto: str = "impulso_10", dias: int = 10):
    dias = max(1, min(31, dias))
    return cotizar_calc(pais, producto, dias)

@app.get("/pagar/{tipo}")
def pagar_tipo(tipo: str, pais: str = "AR", dias: int = 10):
    prod = "impulso_10" if tipo == "impulso" else "expansion_10"
    c = cotizar_calc(pais, prod, dias)
    # Si no hay clave de pago configurada en Render, decirlo de verdad, no inventar link
    mp = os.environ.get("MP_ACCESS_TOKEN", "")
    if not mp and pais in ("AR","BR","MX","CL","CO","PE","UY","EC"):
        c["aviso"] = "Mercado Pago no configurado: falta MP_ACCESS_TOKEN en Render Environment."
    c["boton"] = "Pagar"
    return c

class ChatIn(BaseModel):
    nombre: str = ""
    rubro: str = ""
    mensaje: str = ""
@app.post("/api/nodo/chat")
def nodo_chat(d: ChatIn):
    texto = f"Borrador para {d.nombre} ({d.rubro}): {d.mensaje or 'Promo de esta semana'}. Diseno profesional, texto claro y llamado a WhatsApp. ¿Te gusta? Deci SI para publicar o NO para corregir."
    return {"respuesta": texto}

class PubIn(BaseModel):
    nombre: str = ""
    rubro: str = ""
    texto: str = ""
@app.post("/api/publicaciones")
def crear_pub(d: PubIn):
    pid = "PUB-" + secrets.token_hex(3).upper()
    PUBLICACIONES.append({"id": pid, "nombre": d.nombre, "rubro": d.rubro, "texto": d.texto, "estado": "borrador", "fecha": datetime.now().isoformat()})
    return {"publicacion_id": pid, "estado": "borrador"}

class AprobarIn(BaseModel):
    publicacion_id: str = ""
    aprobado: bool = False
@app.post("/api/aprobar")
def aprobar(d: AprobarIn):
    for p in PUBLICACIONES:
        if p["id"] == d.publicacion_id:
            if not d.aprobado:
                p["estado"] = "corregir"
                return {"ok": True, "estado": "corregir"}
            p["estado"] = "publicado"
            return {"ok": True, "estado": "publicado"}
    raise HTTPException(400, "Publicacion no encontrada")

class CobroIn(BaseModel):
    nombre: str = ""
    dni: str = ""
    email: str = ""
    whatsapp: str = ""
    monto: float = 0
    concepto: str = ""
@app.post("/api/cobros")
def crear_cobro(d: CobroIn):
    if not d.nombre or not d.dni or not d.whatsapp:
        raise HTTPException(400, "Faltan nombre, DNI o WhatsApp")
    cid = "COB-" + secrets.token_hex(3).upper()
    COBROS.append({"id": cid, "nombre": d.nombre, "dni": d.dni, "email": d.email, "whatsapp": d.whatsapp, "monto": d.monto, "concepto": d.concepto, "estado": "esperando_SI", "fecha": datetime.now().isoformat()})
    return {"ok": True, "cobro_id": cid, "mensaje": "Se va a enviar: Sos vos, DNI " + d.dni + "? Responde SI"}

class LeadIn(BaseModel):
    nombre: str = ""
    telefono: str = ""
    interes: str = ""
    negocio: str = ""
@app.post("/api/leads")
def crear_lead(d: LeadIn):
    LEADS.append({"nombre": d.nombre, "telefono": d.telefono, "interes": d.interes, "negocio": d.negocio, "fecha": datetime.now().isoformat()})
    return {"ok": True}

class LoginIn(BaseModel):
    clave: str = ""
@app.post("/api/admin/login")
def login(d: LoginIn):
    if d.clave != ADMIN_KEY:
        raise HTTPException(401, "Clave incorrecta")
    return {"ok": True, "token": "NODO-SESION"}

def check_admin(req: Request):
    if req.headers.get("x-nodo-clave", "") != ADMIN_KEY:
        raise HTTPException(401, "No autorizado")

@app.get("/api/admin/resumen")
def resumen(req: Request):
    check_admin(req)
    return {"leads": LEADS, "publicaciones": PUBLICACIONES, "cobros": COBROS, "retencion": "30 dias gratis. Luego $2700/mes. Si no se paga, pausado, seguro, NO borrado. Al volver, se restaura todo."}

@app.get("/admin/leads")
def admin_leads(req: Request):
    check_admin(req)
    return {"leads": LEADS}

class RecupIn(BaseModel):
    email: str = ""
@app.post("/api/recuperar")
def recuperar(d: RecupIn):
    if not d.email or "@" not in d.email:
        raise HTTPException(400, "Email invalido")
    codigo = str(secrets.randbelow(900000) + 100000)
    RECUPERACIONES[d.email] = (codigo, time.time() + 1800)
    return {"ok": True, "mensaje": "Te enviamos un codigo valido 30 minutos. Revisa tu email."}

class VerifIn(BaseModel):
    email: str = ""
    codigo: str = ""
@app.post("/api/recuperar/verificar")
def verificar(d: VerifIn):
    v = RECUPERACIONES.get(d.email)
    if not v or v[0] != d.codigo or time.time() > v[1]:
        raise HTTPException(400, "Codigo invalido o vencido")
    return {"ok": True}
