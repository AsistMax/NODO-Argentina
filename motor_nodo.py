# motor_nodo.py - NODO ARGENTINA - MOTOR PRIVADO 24/7 - MULTIPLES AGENTES - CONFIDENCIAL
import os, time, uuid
from supabase import create_client
from datetime import datetime

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

AGENTES_NODO = [
    {"nombre": "Agente NODO - Captacion Norte", "zona": "NOA"},
    {"nombre": "Agente NODO - Captacion CABA", "zona": "CABA"},
    {"nombre": "Agente NODO - Audio & Validacion", "zona": "Nacional"},
    {"nombre": "Agente NODO - Campanas Premium", "zona": "Nacional"},
    {"nombre": "Agente NODO - Seguimiento", "zona": "Nacional"},
    {"nombre": "Agente NODO - Cierre", "zona": "Nacional"},
]

CALLMEBOT_PHONE = os.getenv("CALLMEBOT_PHONE", "3834607740")

def calcular_costo_campo(cantidad, dias, urgencia):
    base = 800000
    factores = {"normal": 1.0, "urgente": 1.5, "express": 2.0}
    factor = factores.get(urgencia, 1.0)
    total = (base * cantidad) * (dias / 30) * factor
    return total, factor

def registrar_lead(empresa_id, origen, agente_campo_id=None, audio_url=None):
    comprobante = f"NODO-{uuid.uuid4().hex[:8].upper()}"
    data = {
        "empresa_id": empresa_id,
        "comprobante_id": comprobante,
        "origen": origen,
        "estado": "pendiente",
        "agente_campo_id": agente_campo_id,
        "audio_url": audio_url,
        "link_evidencia": f"https://nodo.ar/evidencia/{comprobante}"
    }
    supabase.table("cartera_crm").insert(data).execute()
    print(f"[{datetime.now()}] Lead: {comprobante} Origen: {origen}")
    return comprobante

def operar_agentes():
    print("NODO ARGENTINA - Sistema Privado Operando 24/7 - Multiples Agentes")
    for agente in AGENTES_NODO:
        existing = supabase.table("agentes_nodo").select("*").eq("nombre", agente["nombre"]).execute()
        if not existing.data:
            supabase.table("agentes_nodo").insert(agente).execute()
    while True:
        try:
            agentes_db = supabase.table("agentes_nodo").select("*").execute()
            for ag in agentes_db.data:
                print(f"Operando {ag['nombre']} - {ag['zona']}")
                supabase.table("agentes_nodo").update({"leads_hoy": ag.get("leads_hoy",0)+1}).eq("id", ag["id"]).execute()
            time.sleep(60)
        except Exception as e:
            print(f"Error motor NODO: {e}")
            time.sleep(10)

if __name__ == "__main__":
    operar_agentes()
