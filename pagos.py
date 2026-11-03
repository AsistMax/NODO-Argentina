# pagos.py
def calcular_total(cantidad_personas, dias, urgencia, inversion_digital):
    base_campo = 800000
    factores = {'normal': 1.0, 'urgente': 1.5, 'express': 2.0}
    factor = factores.get(urgencia, 1.0)
    total_campo = (base_campo * cantidad_personas) * (dias/30) * factor
    total_final = total_campo + inversion_digital
    return {'total_campo': total_campo, 'total_digital': inversion_digital, 'total_final': total_final}
