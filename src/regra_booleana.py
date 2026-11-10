"""
SIFSM - Aurora Siger - Fase 7
Regra booleana de risco energético e corte de carga.

Variáveis de entrada (cada uma é Verdadeiro ou Falso):
  A = bateria baixa         -> carga da bateria abaixo de 30%
  G = geração suficiente    -> geração solar do ciclo >= consumo total da colônia
  E = consumo excessivo     -> consumo do módulo acima de 140% do esperado para aquela hora
  P = módulo essencial      -> prioridade 1 ou 2 (Habitat, MedBase, Reator)

Saídas:
  RISCO = (A AND NOT G) OR E
  CORTE = RISCO AND NOT P

Ou seja: há risco quando a bateria está baixa e o sol não dá conta da
demanda, ou quando o módulo consome demais. Nesse caso, módulos NÃO
essenciais entram em modo de economia (corte de carga); os essenciais
nunca são cortados, apenas sinalizados.
"""

from itertools import product

# Limiares da regra (fáceis de ajustar em um único lugar)
LIMIAR_BATERIA_BAIXA_PCT = 30.0
# 140%: calibrado nos dados - detecta 8 de 8 anomalias injetadas com só 17
# falsos alarmes em 1008 leituras (com 125% eram 57 falsos alarmes).
FATOR_CONSUMO_EXCESSIVO = 1.40
PRIORIDADE_MAX_ESSENCIAL = 2

# Gravidade dos alertas (quanto menor o número, mais urgente)
GRAVIDADE_TEXTO = {1: "CRÍTICO", 2: "ALTO", 3: "MODERADO"}


def avaliar_regra(a, g, e, p):
    """Aplica a regra booleana e devolve (risco, corte)."""
    risco = (a and not g) or e
    corte = risco and not p
    return risco, corte


def montar_variaveis(carga_pct, geracao_total, consumo_total,
                     consumo_modulo, consumo_esperado, prioridade):
    """Transforma as medidas numéricas de uma leitura nas variáveis A, G, E e P."""
    a = carga_pct < LIMIAR_BATERIA_BAIXA_PCT
    g = geracao_total >= consumo_total
    # Sem referência de consumo esperado (ex.: módulo novo), E é considerado falso
    e = consumo_esperado is not None and consumo_modulo > FATOR_CONSUMO_EXCESSIVO * consumo_esperado
    p = prioridade <= PRIORIDADE_MAX_ESSENCIAL
    return a, g, e, p


def classificar_alerta(a, g, e):
    """Define tipo e gravidade do alerta a partir das variáveis (None = sem alerta)."""
    risco_energia = a and not g
    if risco_energia and e:
        return "energia_consumo", 1
    if risco_energia:
        return "energia", 2
    if e:
        return "consumo", 3
    return None, None


def calcular_perfil_esperado(leituras):
    """
    Consumo esperado de cada módulo em cada hora do dia: a MEDIANA das leituras
    daquela hora. A mediana é usada (e não a média) porque não é distorcida
    pelas próprias anomalias que queremos detectar.
    Recebe um DataFrame com id_modulo, hora e consumo_kwh e devolve um
    dicionário {(id_modulo, hora): consumo esperado}.
    """
    mediana = leituras.groupby(["id_modulo", "hora"])["consumo_kwh"].median()
    return mediana.to_dict()


def tabela_verdade():
    """Gera as 16 combinações de A, G, E, P com as saídas RISCO e CORTE."""
    linhas = []
    for a, g, e, p in product([False, True], repeat=4):
        risco, corte = avaliar_regra(a, g, e, p)
        linhas.append((a, g, e, p, risco, corte))
    return linhas


def formatar_tabela_verdade():
    """Devolve a tabela-verdade como texto pronto para exibir no terminal."""
    texto = [" A  G  E  P | RISCO CORTE", "-" * 26]
    for a, g, e, p, risco, corte in tabela_verdade():
        bits = "  ".join(str(int(v)) for v in (a, g, e, p))
        texto.append(f" {bits} |   {int(risco)}     {int(corte)}")
    return "\n".join(texto)
