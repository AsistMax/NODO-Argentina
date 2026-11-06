import os, time, uuid
from supabase import create_client
from datetime import datetime

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
supabase = create_client(SUPABASE_URL, SUPABASE_KEY) if SUPABASE_URL and SUPABASE_KEY else None

AGENTES_NODO = [
    {"nombre": "Agente NODO - Captacion Norte", "zona": "NOA"},
    {"nombre": "Agente NODO - Captacion CABA", "zona": "CABA"},
    {"nombre": "Agente NODO - Audio & Validacion", "zona": "Nacional"},
    {"nombre": "Agente NODO - Campanas Premium", "zona": "Nacional"},
    {"nombre": "Agente NODO - Seguimiento", "zona": "Nacional"},
    {"nombre": "Agente NODO - Cierre", "zona": "Nacional"},
]

def operar_agentes():
    print("NODO ARGENTINA - Sistema Privado Operando 24/7 - Multiples Agentes - FIX PGRST205")
    if not supabase:
        print("Sin SUPABASE_URL/KEY - motor en modo espera, no crashea")
        while True:
            time.sleep(60)
    # Sincronizar agentes en equipo_campo (tabla real), no agentes_nodo
    for agente in AGENTES_NODO:
        try:
            existing = supabase.table("equipo_campo").select("id").eq("nombre", agente["nombre"]).execute()
            if not existing.data:
                supabase.table("equipo_campo").insert(agente).execute()
                print(f"Agente creado en equipo_campo: {agente['nombre']}")
        except Exception as e:
            print(f"Sync agente {agente['nombre']} - error no fatal: {e}")
    while True:
        try:
            agentes_db = supabase.table("equipo_campo").select("*").execute()
            for ag in (agentes_db.data or []):
                print(f"Operando {ag.get('nombre')} - {ag.get('zona')} - {datetime.now()}")
            time.sleep(60)
        except Exception as e:
            # NO CRASHEA - solo loguea y espera, Render no reinicia
            print(f"Error motor NODO (no fatal, sigue operando): {e}")
            time.sleep(30)

if __name__ == "__main__":
    operar_agentes()
