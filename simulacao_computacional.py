"""
SIFSM - Aurora Siger - Fase 7
Simulação computacional do banco de baterias da colônia.

Conceitos matemáticos aplicados:
  1. Equação de diferenças (modelo discreto, passo de 1 hora):
         carga(t+1) = carga(t) + eficiência * saldo(t),  se saldo(t) > 0  (carregando)
         carga(t+1) = carga(t) + saldo(t),               se saldo(t) <= 0 (descarregando)
     com saldo(t) = geração(t) - consumo(t), limitada entre 0 e a capacidade.
  2. Integral definida (SymPy): energia solar teórica de um dia,
         E = integral de 6 a 18 de Pp * sen(pi * (t - 6) / 12) dt = 24 * Pp / pi
     comparada com a soma das leituras horárias (integração numérica).
  3. Método de Monte Carlo: centenas de tempestades de poeira sorteadas
     para estimar a PROBABILIDADE de a bateria cair abaixo do mínimo.

Cenários simulados:
  - Registrado: reproduz os 7 dias da base (valida o modelo contra os dados);
  - Com corte de carga: a regra booleana desliga cargas não essenciais;
  - Tempestade severa (dias 5 a 7), sem e com corte de carga.

Execução isolada:  python simulacao_computacional.py
(também é chamada pelo menu do codigo_fonte.py)
"""

import sqlite3
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import sympy as sp

from src.config import ARQUIVO_BANCO, PASTA_GRAFICOS, RAIZ
from src.graficos import (COR_GRADE, COR_MUTED, COR_SUPERFICIE, COR_TEXTO, COR_TEXTO_2,
                          CORES_SERIES, estilizar)
from src.regra_booleana import avaliar_regra, calcular_perfil_esperado, montar_variaveis
from src.terminal import configurar_saida_utf8

FATOR_STANDBY = 0.30        # módulo cortado passa a consumir só 30% (sistemas vitais)
FATOR_TEMPESTADE_SEVERA = 0.20
DIAS_TEMPESTADE_SEVERA = (5, 6, 7)


# ----------------------------------------------------------------------
# Modelo da bateria
# ----------------------------------------------------------------------
def atualizar_carga(carga_kwh, saldo_kwh, capacidade_kwh, eficiencia):
    """Aplica um passo (1 hora) da equação de diferenças da bateria."""
    if saldo_kwh > 0:
        nova = carga_kwh + saldo_kwh * eficiencia   # carregando: há perdas
    else:
        nova = carga_kwh + saldo_kwh                # descarregando
    return min(capacidade_kwh, max(0.0, nova))      # limites físicos


# ----------------------------------------------------------------------
# Leitura dos dados
# ----------------------------------------------------------------------
def carregar_dados(caminho_banco=ARQUIVO_BANCO):
    """Lê bateria, módulos e leituras do banco SQLite."""
    caminho_banco = Path(caminho_banco)
    if not caminho_banco.exists():
        raise FileNotFoundError(f"Banco de dados não encontrado: {caminho_banco.name}")
    con = sqlite3.connect(caminho_banco)
    try:
        bateria = pd.read_sql_query("SELECT * FROM baterias ORDER BY id_bateria LIMIT 1", con)
        modulos = pd.read_sql_query("SELECT * FROM modulos ORDER BY id_modulo", con)
        leituras = pd.read_sql_query("SELECT * FROM leituras ORDER BY ciclo, id_modulo", con)
    finally:
        con.close()
    if bateria.empty or modulos.empty or leituras.empty:
        raise ValueError("O banco não tem bateria, módulos ou leituras suficientes para simular.")
    return bateria.iloc[0].to_dict(), modulos, leituras


def montar_series(modulos, leituras):
    """
    Organiza os dados em vetores/matrizes NumPy, um valor por ciclo:
      geracao[t]     -> geração total da colônia no ciclo t
      consumo[t, m]  -> consumo do módulo m no ciclo t
      esperado[t, m] -> consumo esperado (perfil horário) do módulo m no ciclo t
    """
    perfil = calcular_perfil_esperado(leituras)
    tabela = leituras.pivot_table(index="ciclo", columns="id_modulo",
                                  values="consumo_kwh", aggfunc="sum").fillna(0.0)
    ids = list(tabela.columns)
    ciclos = tabela.index.to_numpy()
    horas = leituras.groupby("ciclo")["hora"].first().reindex(ciclos).to_numpy()
    dias = leituras.groupby("ciclo")["dia"].first().reindex(ciclos).to_numpy()
    geracao = leituras.groupby("ciclo")["geracao_kwh"].sum().reindex(ciclos).to_numpy()
    carga_registrada = leituras.groupby("ciclo")["carga_bateria_pct"].first().reindex(ciclos).to_numpy()

    esperado = np.array([[perfil.get((m, h), np.nan) for m in ids] for h in horas])
    prioridades = modulos.set_index("id_modulo").loc[ids, "prioridade"].to_numpy()
    nomes = modulos.set_index("id_modulo").loc[ids, "nome"].tolist()

    return {"ciclos": ciclos, "dias": dias, "horas": horas, "geracao": geracao,
            "consumo": tabela.to_numpy(), "esperado": esperado, "ids": ids,
            "nomes": nomes, "prioridades": prioridades, "carga_registrada": carga_registrada}


# ----------------------------------------------------------------------
# Simulação
# ----------------------------------------------------------------------
def simular_bateria(series, bateria, geracao=None, consumo=None, corte_ativo=False):
    """
    Simula a bateria hora a hora. Se corte_ativo=True, a cada hora a regra
    booleana decide quais módulos não essenciais entram em modo de economia.
    Devolve a carga (%) em cada ciclo e indicadores do cenário.
    """
    geracao = series["geracao"] if geracao is None else geracao
    consumo = series["consumo"] if consumo is None else consumo
    capacidade = float(bateria["capacidade_kwh"])
    eficiencia = float(bateria["eficiencia"])
    minimo = float(bateria["carga_minima_pct"])
    carga = capacidade * float(bateria["carga_inicial_pct"]) / 100

    cargas_pct = np.zeros(len(geracao))
    energia_cortada = 0.0      # kWh economizados pelo corte de carga
    energia_nao_atendida = 0.0 # kWh que faltaram com a bateria vazia (apagão)
    horas_com_corte = 0

    for t in range(len(geracao)):
        demanda = consumo[t].copy()
        carga_pct = 100 * carga / capacidade

        if corte_ativo:
            houve_corte = False
            for m in range(len(demanda)):
                esperado = None if np.isnan(series["esperado"][t, m]) else series["esperado"][t, m]
                a, g, e, p = montar_variaveis(carga_pct, geracao[t], consumo[t].sum(),
                                              consumo[t, m], esperado, series["prioridades"][m])
                _, corte = avaliar_regra(a, g, e, p)
                if corte:
                    energia_cortada += demanda[m] * (1 - FATOR_STANDBY)
                    demanda[m] *= FATOR_STANDBY
                    houve_corte = True
            horas_com_corte += houve_corte

        saldo = geracao[t] - demanda.sum()
        if saldo < 0 and carga + saldo < 0:
            energia_nao_atendida += -(carga + saldo)
        carga = atualizar_carga(carga, saldo, capacidade, eficiencia)
        cargas_pct[t] = 100 * carga / capacidade

    return {"carga_pct": cargas_pct,
            "carga_minima_atingida": float(cargas_pct.min()),
            "carga_final": float(cargas_pct[-1]),
            "horas_abaixo_minimo": int((cargas_pct < minimo).sum()),
            "horas_bateria_vazia": int((cargas_pct <= 0.5).sum()),
            "energia_nao_atendida_kwh": energia_nao_atendida,
            "energia_cortada_kwh": energia_cortada,
            "horas_com_corte": horas_com_corte}


def geracao_tempestade_severa(series):
    """Geração registrada, mas com tempestade severa nos dias 5 a 7."""
    perfil = perfil_solar_ceu_limpo(series)
    geracao = series["geracao"].copy()
    for t, (dia, hora) in enumerate(zip(series["dias"], series["horas"])):
        if dia in DIAS_TEMPESTADE_SEVERA:
            geracao[t] = perfil[hora] * FATOR_TEMPESTADE_SEVERA
    return geracao


def capacidade_minima_sem_apagao(series, bateria, corte_ativo=True, limite_kwh=3000, passo=50):
    """
    Dimensionamento: menor capacidade de bateria (busca de 50 em 50 kWh) que
    atravessa os 7 dias registrados sem apagão, mantendo a mesma carga inicial (%).
    """
    for capacidade in range(passo, limite_kwh + 1, passo):
        teste = dict(bateria, capacidade_kwh=float(capacidade))
        if simular_bateria(series, teste, corte_ativo=corte_ativo)["energia_nao_atendida_kwh"] == 0:
            return capacidade
    return None


def executar_cenarios(series, bateria):
    """Roda os quatro cenários determinísticos."""
    severa = geracao_tempestade_severa(series)
    return {
        "Registrado (sem corte)": simular_bateria(series, bateria),
        "Registrado + corte de carga": simular_bateria(series, bateria, corte_ativo=True),
        "Tempestade severa (sem corte)": simular_bateria(series, bateria, geracao=severa),
        "Tempestade severa + corte": simular_bateria(series, bateria, geracao=severa, corte_ativo=True),
    }


# ----------------------------------------------------------------------
# Matemática: integral da curva solar (SymPy) x soma numérica
# ----------------------------------------------------------------------
def dias_ceu_limpo(series):
    """Dias sem tempestade: geração diária acima de 60% do melhor dia."""
    por_dia = pd.Series(series["geracao"]).groupby(series["dias"]).sum()
    return por_dia[por_dia > 0.6 * por_dia.max()].index.tolist()


def perfil_solar_ceu_limpo(series):
    """Geração média em cada hora do dia, considerando só os dias de céu limpo."""
    limpos = np.isin(series["dias"], dias_ceu_limpo(series))
    perfil = pd.Series(series["geracao"][limpos]).groupby(series["horas"][limpos]).mean()
    return perfil.reindex(range(24), fill_value=0.0).to_numpy()


def analise_simbolica(series):
    """Calcula com SymPy a energia solar teórica de um dia e compara com os dados."""
    t, pp = sp.symbols("t P_p", positive=True)
    potencia = pp * sp.sin(sp.pi * (t - 6) / 12)
    integral = sp.simplify(sp.integrate(potencia, (t, 6, 18)))   # = 24*P_p/pi

    perfil = perfil_solar_ceu_limpo(series)
    pico_estimado = float(perfil[12])                             # potência ao meio-dia
    energia_teorica = float(integral.subs(pp, pico_estimado))
    energia_medida = float(perfil.sum())                          # soma de Riemann (passo 1 h)

    # Pico mínimo para que a geração diária cubra o consumo médio diário
    consumo_diario = float(series["consumo"].sum() / len(np.unique(series["dias"])))
    pico_minimo = float(sp.solve(sp.Eq(integral, consumo_diario), pp)[0])

    return {"expressao": f"{sp.sstr(potencia)}", "integral": sp.sstr(integral),
            "pico_estimado": pico_estimado, "energia_teorica": energia_teorica,
            "energia_medida": energia_medida, "consumo_diario": consumo_diario,
            "pico_minimo": pico_minimo, "perfil": perfil}


# ----------------------------------------------------------------------
# Monte Carlo
# ----------------------------------------------------------------------
def monte_carlo(series, bateria, n_execucoes=500, semente=7):
    """
    Sorteia tempestades (dia de início 1-7, duração 1-3 dias, intensidade 20%-60%
    da luz) e variação de demanda (95%-110%). Para cada sorteio simula a bateria
    sem e com corte de carga e guarda a carga mínima atingida.
    """
    rng = np.random.default_rng(semente)
    perfil = perfil_solar_ceu_limpo(series)
    base = perfil[series["horas"]]
    minimo = float(bateria["carga_minima_pct"])
    minimos = {"sem": [], "com": []}
    apagoes = {"sem": 0, "com": 0}

    for _ in range(n_execucoes):
        inicio = rng.integers(1, 8)
        duracao = rng.integers(1, 4)
        intensidade = rng.uniform(0.2, 0.6)
        fator_demanda = rng.uniform(0.95, 1.10)

        em_tempestade = (series["dias"] >= inicio) & (series["dias"] < inicio + duracao)
        geracao = base * np.where(em_tempestade, intensidade, 1.0)
        geracao = np.clip(geracao * (1 + rng.normal(0, 0.05, len(geracao))), 0, None)
        consumo = series["consumo"] * fator_demanda

        for chave, corte in (("sem", False), ("com", True)):
            r = simular_bateria(series, bateria, geracao=geracao, consumo=consumo, corte_ativo=corte)
            minimos[chave].append(r["carga_minima_atingida"])
            apagoes[chave] += r["horas_bateria_vazia"] > 0

    resultado = {}
    for chave in ("sem", "com"):
        valores = np.array(minimos[chave])
        resultado[chave] = {
            "minimos": valores,
            "prob_abaixo_minimo": float((valores < minimo).mean()),
            "prob_apagao": apagoes[chave] / n_execucoes,
            "media_minimo": float(valores.mean()),
            "percentil_5": float(np.percentile(valores, 5)),
        }
    resultado["n"] = n_execucoes
    return resultado


# ----------------------------------------------------------------------
# Gráficos (paleta e estilo em src/graficos.py)
# ----------------------------------------------------------------------
def grafico_cenarios(series, cenarios, bateria, arquivo):
    """Carga da bateria (%) ao longo dos 7 dias em cada cenário."""
    fig, ax = plt.subplots(figsize=(11, 5.2), facecolor=COR_SUPERFICIE)
    ciclos = series["ciclos"]
    ax.axvspan(4 * 24 + 0.5, 6 * 24 + 0.5, color=COR_GRADE, alpha=0.6, linewidth=0)
    ax.text(5 * 24 + 0.5, 103, "tempestade registrada", ha="center", color=COR_TEXTO_2, fontsize=9)
    for limite, texto in ((30, "A: bateria baixa (30%)"), (float(bateria["carga_minima_pct"]), "mínimo operacional (20%)")):
        ax.axhline(limite, color=COR_MUTED, linestyle="--", linewidth=1)
        ax.text(2, limite + 1.2, texto, color=COR_TEXTO_2, fontsize=8)
    for cor, (nome, r) in zip(CORES_SERIES, cenarios.items()):
        ax.plot(ciclos, r["carga_pct"], color=cor, linewidth=2, label=nome)
    estilizar(ax, "Carga da bateria por cenário simulado", "Ciclo (hora da missão)", "Carga da bateria (%)")
    ax.set_ylim(0, 108)
    ax.set_xlim(1, ciclos[-1])
    ax.set_xticks(range(1, ciclos[-1] + 1, 24), [f"dia {d}" for d in range(1, 8)])
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.13), ncol=4, frameon=False,
              fontsize=9, labelcolor=COR_TEXTO)
    fig.tight_layout()
    fig.savefig(arquivo, dpi=130)
    plt.close(fig)


def grafico_monte_carlo(mc, bateria, arquivo):
    """Distribuição da carga mínima atingida nas execuções de Monte Carlo."""
    fig, ax = plt.subplots(figsize=(9, 4.8), facecolor=COR_SUPERFICIE)
    faixas = np.linspace(0, 100, 26)
    for cor, chave, nome in ((CORES_SERIES[0], "sem", "Sem corte de carga"),
                             (CORES_SERIES[1], "com", "Com corte de carga")):
        ax.hist(mc[chave]["minimos"], bins=faixas, histtype="step", linewidth=2, color=cor,
                label=f"{nome} (P(abaixo do mínimo) = {mc[chave]['prob_abaixo_minimo']:.0%})")
    minimo = float(bateria["carga_minima_pct"])
    ax.axvline(minimo, color=COR_MUTED, linestyle="--", linewidth=1)
    ax.text(minimo + 1, ax.get_ylim()[1] * 0.92, "mínimo 20%", color=COR_TEXTO_2, fontsize=8)
    estilizar(ax, f"Monte Carlo: carga mínima em {mc['n']} tempestades sorteadas",
            "Carga mínima atingida na semana (%)", "Número de execuções")
    ax.legend(frameon=False, fontsize=9, labelcolor=COR_TEXTO)
    fig.tight_layout()
    fig.savefig(arquivo, dpi=130)
    plt.close(fig)


def grafico_curva_solar(simb, arquivo):
    """Curva teórica da geração solar x média medida nos dias de céu limpo."""
    fig, ax = plt.subplots(figsize=(9, 4.8), facecolor=COR_SUPERFICIE)
    t = np.linspace(6, 18, 200)
    curva = simb["pico_estimado"] * np.sin(np.pi * (t - 6) / 12)
    ax.fill_between(t, curva, color=CORES_SERIES[0], alpha=0.12, linewidth=0)
    ax.plot(t, curva, color=CORES_SERIES[0], linewidth=2,
            label=f"Teórica: integral = 24·Pp/π = {simb['energia_teorica']:.1f} kWh/dia")
    ax.scatter(range(24), simb["perfil"], s=40, color=CORES_SERIES[1], zorder=3,
               edgecolor=COR_SUPERFICIE, linewidth=1.5,
               label=f"Medida (média por hora): soma = {simb['energia_medida']:.1f} kWh/dia")
    estilizar(ax, "Geração solar: integral analítica x soma das leituras", "Hora do dia", "Geração (kWh)")
    ax.set_xticks(range(0, 24, 2))
    ax.legend(frameon=False, fontsize=9, labelcolor=COR_TEXTO, loc="upper left")
    fig.tight_layout()
    fig.savefig(arquivo, dpi=130)
    plt.close(fig)


# ----------------------------------------------------------------------
# Execução completa com relatório no terminal
# ----------------------------------------------------------------------
def executar_simulacao_completa(caminho_banco=ARQUIVO_BANCO, n_monte_carlo=500, salvar_graficos=True):
    """Roda cenários, análise simbólica e Monte Carlo; imprime e devolve o resumo."""
    bateria, modulos, leituras = carregar_dados(caminho_banco)
    series = montar_series(modulos, leituras)

    print("\n=== SIMULAÇÃO COMPUTACIONAL DO BANCO DE BATERIAS ===")
    print(f"Bateria: {bateria['nome']} | capacidade {bateria['capacidade_kwh']:.0f} kWh | "
          f"carga inicial {bateria['carga_inicial_pct']:.0f}% | mínimo {bateria['carga_minima_pct']:.0f}% | "
          f"eficiência {bateria['eficiencia']:.0%}")
    print("Modelo: carga(t+1) = carga(t) + saldo(t) (x eficiência ao carregar), limitada a [0, capacidade]")

    # 1) Cenários determinísticos
    cenarios = executar_cenarios(series, bateria)
    erro = np.abs(cenarios["Registrado (sem corte)"]["carga_pct"] - series["carga_registrada"]).max()
    print(f"\nValidação: diferença máxima entre o modelo e a carga registrada no banco = {erro:.4f} p.p.")
    print("\n[1] Cenários determinísticos (7 dias)")
    print(f"{'Cenário':<32}{'Mín.(%)':>8}{'Final(%)':>9}{'h<20%':>7}{'Apagão(kWh)':>12}{'Economia(kWh)':>14}")
    for nome, r in cenarios.items():
        print(f"{nome:<32}{r['carga_minima_atingida']:>8.1f}{r['carga_final']:>9.1f}"
              f"{r['horas_abaixo_minimo']:>7}{r['energia_nao_atendida_kwh']:>12.1f}{r['energia_cortada_kwh']:>14.1f}")

    base = cenarios["Registrado (sem corte)"]["energia_nao_atendida_kwh"]
    com_corte = cenarios["Registrado + corte de carga"]["energia_nao_atendida_kwh"]
    if base > 0:
        print(f"O corte de carga reduziu a energia não atendida em {1 - com_corte / base:.0%}.")
    dimensionamento = {"sem_corte": capacidade_minima_sem_apagao(series, bateria, corte_ativo=False),
                       "com_corte": capacidade_minima_sem_apagao(series, bateria, corte_ativo=True)}
    print(f"Dimensionamento: capacidade mínima para atravessar a semana sem apagão = "
          f"{dimensionamento['sem_corte']} kWh sem corte | {dimensionamento['com_corte']} kWh com corte "
          f"(atual: {bateria['capacidade_kwh']:.0f} kWh)")

    # 2) Matemática simbólica
    simb = analise_simbolica(series)
    print("\n[2] Integral da curva solar (SymPy)")
    print(f"Potência solar: P(t) = {simb['expressao']}  (6 h <= t <= 18 h)")
    print(f"Integral de 6 a 18: E = {simb['integral']}")
    print(f"Pico estimado nos dados (12 h): Pp = {simb['pico_estimado']:.2f} kWh")
    print(f"Energia teórica = {simb['energia_teorica']:.1f} kWh/dia | soma das leituras = "
          f"{simb['energia_medida']:.1f} kWh/dia "
          f"(diferença {abs(simb['energia_teorica'] - simb['energia_medida']) / simb['energia_teorica']:.1%})")
    print(f"Consumo médio da colônia = {simb['consumo_diario']:.1f} kWh/dia -> pico mínimo para "
          f"autossuficiência: Pp >= {simb['pico_minimo']:.1f} kWh (resolvendo 24·Pp/π = consumo)")

    # 3) Monte Carlo
    mc = monte_carlo(series, bateria, n_execucoes=n_monte_carlo)
    print(f"\n[3] Monte Carlo ({mc['n']} tempestades sorteadas)")
    for chave, nome in (("sem", "Sem corte de carga"), ("com", "Com corte de carga")):
        r = mc[chave]
        print(f"{nome:<20} P(carga < mínimo) = {r['prob_abaixo_minimo']:6.1%} | "
              f"P(apagão) = {r['prob_apagao']:6.1%} | carga mínima média = {r['media_minimo']:5.1f}% | "
              f"pior 5% = {r['percentil_5']:5.1f}%")

    arquivos = []
    if salvar_graficos:
        PASTA_GRAFICOS.mkdir(exist_ok=True)
        arquivos = [PASTA_GRAFICOS / "simulacao_cenarios_bateria.png",
                    PASTA_GRAFICOS / "simulacao_monte_carlo.png",
                    PASTA_GRAFICOS / "simulacao_curva_solar_integral.png"]
        grafico_cenarios(series, cenarios, bateria, arquivos[0])
        grafico_monte_carlo(mc, bateria, arquivos[1])
        grafico_curva_solar(simb, arquivos[2])
        print("\nGráficos salvos em:")
        for arq in arquivos:
            print(f"  - {arq.relative_to(RAIZ)}")

    return {"cenarios": cenarios, "simbolica": simb, "monte_carlo": mc,
            "dimensionamento": dimensionamento, "validacao_erro": float(erro), "graficos": arquivos}


if __name__ == "__main__":
    configurar_saida_utf8()
    try:
        executar_simulacao_completa()
    except (FileNotFoundError, ValueError, sqlite3.Error) as erro:
        print(f"Erro ao executar a simulação: {erro}")
        print("Dica: rode 'python -m src.gerar_base' para criar a base de dados.")
