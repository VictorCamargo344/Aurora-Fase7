import sqlite3
import math
import random

random.seed(42)

MODULOS = [
    (1, "Habitat Alpha", "habitacao",   "0x1A2F", 1, "ativo",      45),
    (2, "MedBase",       "medico",      "0x1B3C", 2, "ativo",      38),
    (3, "Reator Solar",  "energia",     "0x2C4D", 2, "ativo",      20),
    (4, "BioLab",        "laboratorio", "0x2D5E", 3, "ativo",      30),
    (5, "LogiStore",     "armazenagem", "0x3E6F", 4, "ativo",      25),
    (6, "TerraBot",      "mineracao",   "0x3F7A", 5, "manutencao", 55),
]

CICLOS = 168              # 7 dias de 24 horas
GERACAO_PICO = 12.0       # kWh gerados ao meio-dia pelo Reator Solar
TEMP_REF = -15.0          # temperatura mais alta do dia, referência do aquecimento
LUX_MAX = 40000.0         # luminosidade ao meio-dia
COEF_AQUECIMENTO = 0.02   # kWh a mais por grau abaixo da referência
COEF_ILUMINACAO = 0.00002 # kWh a mais por lux abaixo do máximo
PENALIDADE_STATUS = {"ativo": 0.0, "manutencao": 0.3, "alerta": 0.6}

def fator_solar(hora):
    if hora >= 6 and hora <= 18:
        return math.sin(math.pi * (hora - 6) / 12)
    return 0.0

def condicoes_ambientais(hora):
    temperatura = -45 - 30 * math.cos(2 * math.pi * (hora - 3) / 24) + random.gauss(0, 2)
    luminosidade = max(0.0, LUX_MAX * fator_solar(hora) + random.gauss(0, 500))
    umidade = min(50.0, max(30.0, 40 + random.gauss(0, 4)))

    return temperatura, luminosidade, umidade

def calcular_consumo(base_diario, status, temperatura, luminosidade):
    base_horario = base_diario / 24
    aquecimento  = COEF_AQUECIMENTO * (TEMP_REF - temperatura)
    iluminacao   = COEF_ILUMINACAO * (LUX_MAX - luminosidade)

    consumo = base_horario + aquecimento + iluminacao + PENALIDADE_STATUS[status] + random.gauss(0, 0.35)

    return max(0.0, consumo)

def gerar_leituras():
    leituras = []

    for modulo in MODULOS:
        for ciclo in range(1, CICLOS + 1):
            hora = ciclo % 24
            temperatura, luminosidade, umidade = condicoes_ambientais(hora)
            consumo = calcular_consumo(modulo[6], modulo[5], temperatura, luminosidade)

            fator = fator_solar(hora)

            if modulo[1] == "Reator Solar":
                geracao = max(0.0, GERACAO_PICO * fator + random.gauss(0, 0.3) * fator)
            else:
                geracao = 0.0

            leituras.append((modulo[0], ciclo, consumo, geracao, temperatura, luminosidade, umidade))

    return leituras

def gravar_no_banco(leituras):
    con = sqlite3.connect("aurora_siger.db")
    con.execute("PRAGMA foreign_keys = ON")

    con.execute("DELETE FROM leituras")
    con.execute("DELETE FROM modulos")

    con.executemany(
        "INSERT INTO modulos (id_modulo, nome, tipo, codigo_sensor, prioridade, status) VALUES (?, ?, ?, ?, ?, ?)",
        [m[:6] for m in MODULOS]
    )

    con.executemany(
        "INSERT INTO leituras (id_modulo, ciclo, consumo_kwh, geracao_kwh, temperatura_c, luminosidade_lux, umidade_pct) VALUES (?, ?, ?, ?, ?, ?, ?)",
        leituras
    )

    con.commit()
    con.close()

if __name__ == "__main__":
    leituras = gerar_leituras()
    gravar_no_banco(leituras)
    print(f"{len(leituras)} leituras gravadas.")