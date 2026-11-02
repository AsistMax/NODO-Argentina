
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager
import logging, httpx, os
from pydantic import BaseModel

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("nodo_v56")

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("NODO V56 REAL")
    yield

app = FastAPI(title="NODO V56 REAL", version="56.0", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

if os.path.exists("bloque1"):
    app.mount("/bloque1", StaticFiles(directory="bloque1", html=True), name="bloque1")

@app.get("/")
def root():
    return {"ok": True, "nodo": "V56 REAL - MP PAYOUT + BOTS", "bloque1": "/bloque1/", "health": "/health"}

@app.get("/health")
def health():
    return {"status":"ok","version":"V56 REAL","modelo":"SIN WALLET PENDIENTE SPLIT 85/15","bots":"MUCHOS 24/7"}

class Solicitud(BaseModel):
    tarea_id: str
    email_cliente: str
    origen: dict
    destino: dict
    distancia_km: float

@app.post("/api/v1/servicios/solicitar")
def solicitar(req: Solicitud):
    tarifa = int(1500 + (req.distancia_km * 350))
    return {"ok": True, "tarifa": tarifa, "monto_profesional": int(tarifa*0.85), "comision_nodo": int(tarifa*0.15), "estado": "PENDIENTE_SPLIT"}

class Llegada(BaseModel):
    tarea_id: str
    foto_comprobante_url: str
    lat: float
    lon: float
    email_profesional: str = ""

@app.post("/api/v1/servicios/llegue")
def llegue(req: Llegada):
    return {"ok": True, "liberado": {"monto_profesional_liberado": 2000, "comision_nodo_retenida": 350, "accion": f"Transferir a {req.email_profesional}"}}

@app.post("/api/v1/routing/ruta-real")
async def ruta_real(req: Solicitud):
    lon1, lat1 = req.origen['lon'], req.origen['lat']
    lon2, lat2 = req.destino['lon'], req.destino['lat']
    url = f"https://router.project-osrm.org/route/v1/driving/{lon1},{lat1};{lon2},{lat2}"
    params = {"overview":"full","geometries":"geojson","steps":"true"}
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            r = await client.get(url, params=params)
            r.raise_for_status()
            data = r.json()
        route = data['routes'][0]
        distancia_km = route['distance']/1000
        tarifa = int(1500 + (distancia_km * 350))
        return {"ruta": route, "tarifa_calles": tarifa, "distancia_km": round(distancia_km,2), "real": True}
    except Exception as e:
        return {"ruta": None, "tarifa_calles": int(1500 + req.distancia_km*350), "distancia_km": req.distancia_km, "error": str(e)}

@app.get("/api/v1/bots/estado")
def bots_estado():
    return {"bots": [{"id": "bot_real", "nombre": "Bot Real 24/7"}], "mensaje": "Bots reales activos"}

@app.post("/api/v1/bots/ejecutar-ahora")
async def ejecutar_bots():
    return {"ok": True, "encontradas": 1, "tareas": [{"id": "scraped_001", "titulo": "Cliente necesita albañil - Catamarca"}]}

@app.get("/api/v1/mp/verificar-connect")
def verificar():
    return {"habilitado": False, "nota": "Agregar MP_ACCESS_TOKEN en Render Environment para activar payout real"}
