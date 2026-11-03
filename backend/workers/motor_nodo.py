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

def operar_agentes():
    print("NODO ARGENTINA - Sistema Privado Operando 24/7")
    for agente in AGENTES_NODO:
        existing = supabase.table("agentes_nodo").select("*").eq("nombre", agente["nombre"]).execute()
        if not existing.data:
            supabase.table("agentes_nodo").insert(agente).execute()
    while True:
        try:
            agentes_db = supabase.table("agentes_nodo").select("*").execute()
            for ag in agentes_db.data:
                print(f"Operando {ag['nombre']}")
            time.sleep(60)
        except Exception as e:
            print(f"Error: {e}")
            time.sleep(10)

if __name__ == "__main__":
    operar_agentes()
