
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import logging, httpx
from app.core.config import settings
from pydantic import BaseModel

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("nodo")

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("NODO V54 FINAL REAL SIN DEMO - SIN WALLET")
    yield

app = FastAPI(title="NODO V54 FINAL REAL", version="54.0", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

@app.get("/health")
def health():
    return {"status":"ok","version":"V54 FINAL REAL SIN DEMO","modelo":"SIN WALLET - PENDIENTE SPLIT","bots":"MUCHOS 24/7"}

class SolicitudServicio(BaseModel):
    tarea_id: str
    email_cliente: str
    origen: dict
    destino: dict
    distancia_km: float

@app.post("/api/v1/servicios/solicitar")
def solicitar(req: SolicitudServicio):
    tarifa = int(settings.NODO_BASE_FEE + (req.distancia_km * settings.NODO_PER_KM))
    return {"ok": True, "tarifa": tarifa, "estado": "PENDIENTE_SPLIT", "comision": round(tarifa*0.15,2), "para_profesional": round(tarifa*0.85,2)}

@app.post("/api/v1/routing/ruta-real")
async def ruta_real(req: SolicitudServicio):
    lon1, lat1 = req.origen['lon'], req.origen['lat']
    lon2, lat2 = req.destino['lon'], req.destino['lat']
    url = f"https://router.project-osrm.org/route/v1/driving/{lon1},{lat1};{lon2},{lat2}"
    params = {"overview":"full","geometries":"geojson","steps":"true"}
    async with httpx.AsyncClient(timeout=10) as client:
        r = await client.get(url, params=params)
        r.raise_for_status()
        data = r.json()
    route = data['routes'][0]
    distancia_km = route['distance']/1000
    tarifa = int(settings.NODO_BASE_FEE + (distancia_km * settings.NODO_PER_KM))
    return {"ruta": route, "tarifa_calles": tarifa, "distancia_km": round(distancia_km,2)}
