"""
SIFSM - Aurora Siger - Fase 7
Gerador da base de dados simulada.

O que este script faz:
  1. Cria (ou recria) o banco SQLite aurora_siger.db executando o script_banco.sql;
  2. Cadastra os módulos da colônia, o banco de baterias e uma manutenção;
  3. Simula 7 dias (168 ciclos de 1 hora) de leituras de sensores:
     ambiente marciano, consumo de cada módulo, geração solar e carga da bateria;
  4. Exporta a base completa para dados_aurora_siger.csv.

A semente aleatória é fixa (42), então a base gerada é sempre a mesma.
Execução (a partir da raiz do projeto):  python -m src.gerar_base
"""

import math
import random
import sqlite3

import pandas as pd

from simulacao_computacional import atualizar_carga
from src.config import ARQUIVO_BANCO, ARQUIVO_CSV, ARQUIVO_SQL

SEMENTE = 42

# (id, nome, tipo, código do sensor, prioridade, status, consumo base kWh/dia)
MODULOS = [
    (1, "Habitat Alpha", "habitacao",   "0x1A2F", 1, "ativo",      45.0),
    (2, "MedBase",       "medico",      "0x1B3C", 2, "ativo",      38.0),
    (3, "Reator Solar",  "energia",     "0x2C4D", 2, "ativo",      20.0),
    (4, "BioLab",        "laboratorio", "0x2D5E", 3, "ativo",      30.0),
    (5, "LogiStore",     "armazenagem", "0x3E6F", 4, "ativo",      25.0),
    (6, "TerraBot",      "mineracao",   "0x3F7A", 5, "manutencao", 55.0),
]

# Banco de baterias: (id, nome, capacidade kWh, carga inicial %, carga mínima %, eficiência)
BATERIA = (1, "Banco Principal LiFePO4", 500.0, 70.0, 20.0, 0.95)

# Manutenção registrada para o TerraBot, que está com status "manutencao"
MANUTENCOES = [
    (1, 6, 1, "Troca dos rolamentos da broca de mineração", "pendente"),
]

# Parâmetros da simulação
CICLOS = 168              # 7 dias de 24 horas
GERACAO_PICO = 55.0      # kWh gerados ao meio-dia pelo campo solar (céu limpo)
TEMP_REF = -15.0          # temperatura mais alta do dia, referência do aquecimento
LUX_MAX = 40000.0         # luminosidade ao meio-dia com céu limpo
COEF_AQUECIMENTO = 0.02   # kWh a mais por grau abaixo da referência
COEF_ILUMINACAO = 0.00002 # kWh a mais por lux abaixo do máximo
PENALIDADE_STATUS = {"ativo": 0.0, "manutencao": 0.3, "alerta": 0.6}

# Tempestade de poeira: nos dias 5 e 6 a poeira bloqueia 65% da luz solar
DIAS_TEMPESTADE = {5, 6}
FATOR_TEMPESTADE = 0.35

# Anomalias de consumo injetadas (id_modulo, dia, horas, kWh extra por hora).
# Servem para testar a detecção de consumo excessivo pela regra booleana.
ANOMALIAS = [
    (4, 3, range(13, 18), 2.0),  # BioLab: falha no isolamento térmico
    (5, 6, range(2, 5), 1.5),    # LogiStore: falha no sistema de refrigeração
]


def dia_e_hora(ciclo):
    """Converte o ciclo sequencial (1, 2, 3...) em dia da missão e hora do dia."""
    return (ciclo - 1) // 24 + 1, (ciclo - 1) % 24


def fator_solar(hora):
    """Intensidade relativa do sol (0 a 1): meia senoide entre 6 h e 18 h."""
    if 6 <= hora <= 18:
        return math.sin(math.pi * (hora - 6) / 12)
    return 0.0


def condicoes_ambientais(hora, dia):
    """Sorteia o ambiente do ciclo, que é o mesmo para toda a colônia."""
    # Temperatura: mínima por volta das 3 h (cerca de -75 °C) e máxima por volta das 15 h (cerca de -15 °C)
    temperatura = -45 - 30 * math.cos(2 * math.pi * (hora - 3) / 24) + random.gauss(0, 2)

    # Luminosidade: zero à noite; durante a tempestade a poeira reduz a luz
    fator = fator_solar(hora)
    if dia in DIAS_TEMPESTADE:
        fator *= FATOR_TEMPESTADE
    luminosidade = max(0.0, LUX_MAX * fator + random.gauss(0, 500)) if fator > 0 else 0.0

    # Umidade interna dos módulos, mantida pelo controle ambiental perto de 40%
    umidade = min(100.0, max(0.0, random.gauss(40, 3)))

    return temperatura, luminosidade, umidade


def calcular_consumo(modulo, dia, hora, temperatura, luminosidade):
    """Consumo de 1 hora: base + aquecimento + iluminação + status + anomalia + ruído."""
    id_modulo, status, base_diario = modulo[0], modulo[5], modulo[6]

    base_horario = base_diario / 24
    aquecimento = COEF_AQUECIMENTO * (TEMP_REF - temperatura)
    iluminacao = COEF_ILUMINACAO * (LUX_MAX - luminosidade)

    extra = 0.0
    for id_anomalia, dia_anomalia, horas, kwh in ANOMALIAS:
        if id_anomalia == id_modulo and dia_anomalia == dia and hora in horas:
            extra += kwh

    consumo = (base_horario + aquecimento + iluminacao + PENALIDADE_STATUS[status]
               + extra + random.gauss(0, 0.35))
    return max(0.0, consumo)


def calcular_geracao(hora, dia):
    """Geração do campo solar no ciclo (só o Reator Solar gera energia)."""
    fator = fator_solar(hora)
    if dia in DIAS_TEMPESTADE:
        fator *= FATOR_TEMPESTADE
    return max(0.0, GERACAO_PICO * fator + random.gauss(0, 1.0) * fator)


def gerar_leituras():
    """Simula os 168 ciclos e devolve a lista de leituras prontas para o INSERT."""
    random.seed(SEMENTE)
    _, _, capacidade, carga_inicial_pct, _, eficiencia = BATERIA
    carga_kwh = capacidade * carga_inicial_pct / 100

    leituras = []
    for ciclo in range(1, CICLOS + 1):
        dia, hora = dia_e_hora(ciclo)
        temperatura, luminosidade, umidade = condicoes_ambientais(hora, dia)

        # 1º passo: consumo e geração de cada módulo neste ciclo
        linhas_ciclo = []
        for modulo in MODULOS:
            consumo = calcular_consumo(modulo, dia, hora, temperatura, luminosidade)
            geracao = calcular_geracao(hora, dia) if modulo[2] == "energia" else 0.0
            linhas_ciclo.append([modulo[0], ciclo, dia, hora, consumo, geracao,
                                 temperatura, luminosidade, umidade])

        # 2º passo: o saldo da colônia (geração - consumo) carrega ou descarrega a bateria
        saldo = sum(l[5] for l in linhas_ciclo) - sum(l[4] for l in linhas_ciclo)
        carga_kwh = atualizar_carga(carga_kwh, saldo, capacidade, eficiencia)
        carga_pct = 100 * carga_kwh / capacidade

        for linha in linhas_ciclo:
            leituras.append(tuple(linha + [carga_pct]))

    return leituras


def criar_banco():
    """Cria as tabelas executando o script_banco.sql e devolve a conexão."""
    con = sqlite3.connect(ARQUIVO_BANCO)
    con.execute("PRAGMA foreign_keys = ON")
    con.executescript(ARQUIVO_SQL.read_text(encoding="utf-8"))
    return con


def gravar_no_banco(con, leituras):
    """Insere módulos, bateria, manutenções e leituras numa única transação."""
    with con:
        con.executemany(
            "INSERT INTO modulos (id_modulo, nome, tipo, codigo_sensor, prioridade, status, "
            "consumo_base_kwh_dia) VALUES (?, ?, ?, ?, ?, ?, ?)", MODULOS)
        con.execute(
            "INSERT INTO baterias (id_bateria, nome, capacidade_kwh, carga_inicial_pct, "
            "carga_minima_pct, eficiencia) VALUES (?, ?, ?, ?, ?, ?)", BATERIA)
        con.executemany(
            "INSERT INTO manutencoes (id_manutencao, id_modulo, dia, descricao, status) "
            "VALUES (?, ?, ?, ?, ?)", MANUTENCOES)
        con.executemany(
            "INSERT INTO leituras (id_modulo, ciclo, dia, hora, consumo_kwh, geracao_kwh, "
            "temperatura_c, luminosidade_lux, umidade_interna_pct, carga_bateria_pct) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", leituras)


def exportar_csv(con):
    """Exporta as leituras com os dados do módulo para dados_aurora_siger.csv."""
    consulta = """
        SELECT l.id_leitura, l.id_modulo, m.nome AS nome_modulo, m.tipo, m.prioridade,
               m.status, l.ciclo, l.dia, l.hora, l.consumo_kwh, l.geracao_kwh,
               l.temperatura_c, l.luminosidade_lux, l.umidade_interna_pct,
               l.carga_bateria_pct
        FROM leituras l JOIN modulos m ON m.id_modulo = l.id_modulo
        ORDER BY l.ciclo, l.id_modulo
    """
    tabela = pd.read_sql_query(consulta, con)
    tabela.round(3).to_csv(ARQUIVO_CSV, index=False, encoding="utf-8")
    return len(tabela)


def gerar_base():
    """Executa todo o processo e devolve o número de leituras geradas."""
    leituras = gerar_leituras()
    con = criar_banco()
    try:
        gravar_no_banco(con, leituras)
        exportar_csv(con)
    finally:
        con.close()
    return len(leituras)


if __name__ == "__main__":
    total = gerar_base()
    print(f"Banco criado em: data/{ARQUIVO_BANCO.name}")
    print(f"{total} leituras gravadas e exportadas para data/{ARQUIVO_CSV.name}.")
