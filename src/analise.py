####################################################################
# ANÁLISE — o fluxo integrado "Analisar sustentabilidade da colônia"
#           (opção 12) e a análise final com limitações (opção 13).
#   Este é o arquivo que junta todas as peças: banco, regra booleana,
# fila de prioridade, simulação e regressão.
####################################################################

import numpy as np
import pandas as pd

import simulacao_computacional as sim
from src import regra_booleana as rb
from src.alertas import gerar_alertas, imprimir_alertas
from src.banco import abrir_banco, carregar_bateria, carregar_leituras, carregar_modulos
from src.config import LINHA
from src.decisao import avaliar_ciclo, imprimir_avaliacao
from src.estruturas import FilaAlertas, media_movel
from src.regressao import estimar_autonomia, treinar_regressao
from src.terminal import imprimir_tabela


## Simulação simples das próximas 24 h a partir da carga atual,
## usando o consumo típico de cada hora e o sol de um dia típico.
def projetar_24h(df, modulos, bateria, perfil, fator_geracao, corte):
    series = sim.montar_series(pd.DataFrame(list(modulos.values())), df)
    ultimo = df.sort_values("ciclo").iloc[-1]
    horas = np.array([(int(ultimo["hora"]) + 1 + i) % 24 for i in range(24)])
    # Módulo sem histórico naquela hora: usa o consumo base dele dividido por 24.
    base = {m: modulos[m]["consumo_base_kwh_dia"] / 24 for m in series["ids"]}
    consumo = np.array([[perfil.get((m, h), base[m]) for m in series["ids"]] for h in horas])
    geracao = sim.perfil_solar_ceu_limpo(series)[horas] * fator_geracao
    mini = dict(series, esperado=consumo, horas=horas)
    bat = dict(bateria, carga_inicial_pct=float(ultimo["carga_bateria_pct"]))
    resultado = sim.simular_bateria(mini, bat, geracao=geracao, consumo=consumo, corte_ativo=corte)
    # Horas até a geração voltar a cobrir o consumo
    cobre = np.where(geracao >= consumo.sum(axis=1))[0]
    resultado["horas_ate_sol"] = int(cobre[0]) + 1 if len(cobre) else None
    return resultado


## Opção 12: o fluxo completo do exemplo do enunciado, em 7 passos.
def analisar_sustentabilidade():
    print("\n" + LINHA)
    print(" ANÁLISE DE SUSTENTABILIDADE DA COLÔNIA")
    print(LINHA)
    with abrir_banco() as con:
        modulos = carregar_modulos(con)          # dicionário (busca O(1))
        df = carregar_leituras(con)
        bateria = carregar_bateria(con)
    if df.empty or not modulos:
        print("  Não há dados suficientes para a análise.")
        return

    # ---- Passo 1: consulta ao banco ----
    ultimo_ciclo = int(df["ciclo"].max())
    atual = df[df["ciclo"] == ultimo_ciclo]
    carga_atual = float(atual["carga_bateria_pct"].iloc[0])
    ultimas24 = df[df["ciclo"] > ultimo_ciclo - 24]
    print(f"\n[1] CONSULTA AO BANCO: {len(df)} leituras, {len(modulos)} módulos, ciclos 1 a {ultimo_ciclo}")
    print(f"    Situação atual: dia {atual['dia'].iloc[0]}, {atual['hora'].iloc[0]:02d}h | bateria {carga_atual:.1f}%")
    print(f"    Últimas 24 h: consumo {ultimas24['consumo_kwh'].sum():.1f} kWh | "
          f"geração {ultimas24['geracao_kwh'].sum():.1f} kWh")
    print("    Consumo médio móvel (24 h, deque) por módulo:")
    for id_modulo, grupo in df.groupby("id_modulo"):
        if id_modulo in modulos:
            media = media_movel(grupo["consumo_kwh"].tolist())[-1]
            print(f"      - {modulos[id_modulo]['nome']:<15} {media:5.2f} kWh/h")

    # ---- Passo 2: regra booleana no ciclo atual ----
    perfil = rb.calcular_perfil_esperado(df)
    print("\n[2] REGRA BOOLEANA no ciclo atual  (RISCO = A·¬G + E ; CORTE = RISCO·¬P)")
    avaliacoes = avaliar_ciclo(df, modulos, perfil, ultimo_ciclo)
    imprimir_avaliacao(avaliacoes)

    # ---- Passo 3: fila de prioridade com os alertas das últimas 24 h ----
    alertas = gerar_alertas(df, modulos, ciclos=range(ultimo_ciclo - 23, ultimo_ciclo + 1))
    fila = FilaAlertas()
    for alerta in alertas:
        fila.inserir(alerta)
    contagem = fila.contagem_por_gravidade()
    print(f"\n[3] FILA DE ALERTAS (heapq) - últimas 24 h: {len(fila)} alertas "
          f"(crítico {contagem[1]} | alto {contagem[2]} | moderado {contagem[3]})")
    if fila:
        imprimir_alertas(fila.proximos(5))
    anomalias = sorted({a["nome"] for a in alertas if a["E"]})

    # ---- Passo 4: simulação das próximas 24 h ----
    print("\n[4] SIMULAÇÃO DAS PRÓXIMAS 24 h (perfil típico de consumo, a partir da carga atual)")
    projecoes = {
        ("Céu limpo", False): projetar_24h(df, modulos, bateria, perfil, 1.0, False),
        ("Céu limpo", True): projetar_24h(df, modulos, bateria, perfil, 1.0, True),
        ("Tempestade", False): projetar_24h(df, modulos, bateria, perfil, 0.35, False),
        ("Tempestade", True): projetar_24h(df, modulos, bateria, perfil, 0.35, True),
    }
    imprimir_tabela(["Cenário", "Corte de carga", "Carga mín. %", "Carga final %", "Horas < 20%", "Apagão kWh"],
                    [[c, "sim" if corte else "não", f"{r['carga_minima_atingida']:.1f}", f"{r['carga_final']:.1f}",
                      r["horas_abaixo_minimo"], f"{r['energia_nao_atendida_kwh']:.1f}"]
                     for (c, corte), r in projecoes.items()])

    # ---- Passo 5: regressão linear -> autonomia ----
    reg = treinar_regressao(df)
    noite = df[(df["hora"] < 6) | (df["hora"] > 18)]["temperatura_c"].mean()
    consumo_prev, disponivel, autonomia = estimar_autonomia(reg, noite, carga_atual, bateria)
    horas_ate_sol = projecoes[("Céu limpo", False)]["horas_ate_sol"]
    print(f"\n[5] REGRESSÃO LINEAR (R² = {reg['r2_teste']:.2f}): consumo = {reg['a']:.2f} {reg['b']:+.3f}·T")
    print(f"    Temperatura noturna média: {noite:.1f} °C -> consumo previsto {consumo_prev:.2f} kWh/h")
    print(f"    Energia útil na bateria (acima do mínimo de {bateria['carga_minima_pct']:.0f}%): "
          f"{disponivel:.1f} kWh -> autonomia de {autonomia:.1f} h sem sol")
    if horas_ate_sol:
        print(f"    A geração solar volta a cobrir o consumo em ~{horas_ate_sol} h")

    # ---- Passo 6: recomendação técnica ----
    print("\n[6] RECOMENDAÇÃO TÉCNICA")
    recomendacoes = []
    cortaveis = [m["nome"] for m in modulos.values() if m["prioridade"] > rb.PRIORIDADE_MAX_ESSENCIAL]
    essenciais = [m["nome"] for m in modulos.values() if m["prioridade"] <= rb.PRIORIDADE_MAX_ESSENCIAL]
    if horas_ate_sol and autonomia < horas_ate_sol:
        ceu = projecoes[("Céu limpo", False)]
        ceu_corte = projecoes[("Céu limpo", True)]
        recomendacoes.append(f"URGENTE: a autonomia ({autonomia:.1f} h) é menor que o tempo até o sol "
                             f"(~{horas_ate_sol} h). Colocar em economia: {', '.join(cortaveis)}. "
                             f"Na projeção, o corte eleva a carga mínima de {ceu['carga_minima_atingida']:.1f}% "
                             f"para {ceu_corte['carga_minima_atingida']:.1f}%.")
    cortes_agora = [a["nome"] for a in avaliacoes if a["corte"]]
    if cortes_agora:
        recomendacoes.append(f"A regra booleana já indica CORTE agora para: {', '.join(cortes_agora)}.")
    tempestade = projecoes[("Tempestade", False)]
    tempestade_corte = projecoes[("Tempestade", True)]
    if tempestade["energia_nao_atendida_kwh"] > 0:
        reducao = 1 - tempestade_corte["energia_nao_atendida_kwh"] / tempestade["energia_nao_atendida_kwh"]
        recomendacoes.append(f"Se houver tempestade nas próximas 24 h, o corte de carga reduz o apagão em "
                             f"{reducao:.0%}; manter o plano de contingência pronto.")
    if anomalias:
        recomendacoes.append(f"Inspecionar consumo anômalo (E = 1) em: {', '.join(anomalias)}.")
    try:
        series = sim.montar_series(pd.DataFrame(list(modulos.values())), df)
        capacidade = sim.capacidade_minima_sem_apagao(series, bateria, corte_ativo=True)
        if capacidade and capacidade > bateria["capacidade_kwh"]:
            recomendacoes.append(f"Longo prazo: ampliar o banco de baterias de {bateria['capacidade_kwh']:.0f} "
                                 f"para pelo menos {capacidade} kWh (simulação dos 7 dias com corte de carga).")
    except (ValueError, KeyError):
        pass  # sem dados suficientes para o dimensionamento
    if not recomendacoes:
        recomendacoes.append("Operação dentro dos limites. Manter o monitoramento.")
    for i, texto in enumerate(recomendacoes, start=1):
        print(f"    {i}. {texto}")

    # ---- Passo 7: validação por critérios de sustentabilidade e responsabilidade social ----
    print("\n[7] VALIDAÇÃO SOCIOAMBIENTAL DA RECOMENDAÇÃO")
    criterios = [
        (True, f"Vida em primeiro lugar: módulos essenciais ({', '.join(essenciais)}) nunca são cortados."),
        (True, "Transparência: cada decisão mostra as variáveis A, G, E, P que a justificaram."),
        (True, "Humano no controle: o sistema RECOMENDA; o operador confirma o corte."),
        (True, "Critério objetivo e igualitário: o corte segue a prioridade do módulo, não pessoas."),
        (tempestade_corte["energia_nao_atendida_kwh"] < tempestade["energia_nao_atendida_kwh"]
         or tempestade["energia_nao_atendida_kwh"] == 0,
         "Uso racional de energia: o corte reduz a energia que faltaria em cenário de crise."),
        (autonomia >= (horas_ate_sol or 0),
         "Resiliência: a bateria atual cobre a noite sem depender de corte de carga."),
    ]
    for ok, texto in criterios:
        print(f"    [{'OK' if ok else 'ATENÇÃO'}] {texto}")
    print(LINHA)


LIMITACOES = [
    "Os dados são simulados (7 dias); valores reais de Marte exigiriam calibração com sensores.",
    "O modelo linear usa só a temperatura; luminosidade e tempestades também afetam o consumo.",
    "A bateria é modelada com eficiência constante, sem degradação, autodescarga ou efeito do frio.",
    "O consumo esperado (perfil horário) vem dos próprios dados; um módulo novo ainda não tem perfil.",
    "A regra booleana usa limiares fixos (30%, 140%); o ideal seria ajustá-los com histórico real.",
    "O critério E ainda gera alguns falsos alarmes (17 em 1008 leituras) por causa do ruído dos sensores.",
    "O corte de carga é instantâneo e fixo em 30% do consumo; na prática há tempos de religamento.",
    "Banco local (SQLite) com um único usuário; não há autenticação nem registro de quem alterou dados.",
]
MELHORIAS = [
    "Regressão múltipla (temperatura + luminosidade + hora) ou modelos não lineares.",
    "Agente de IA que monitora a fila de alertas e propõe ações, com guardrails e aprovação humana.",
    "Integração com sensores reais (Arduino/ESP32) enviando leituras para o banco.",
    "Previsão de tempestades a partir de dados meteorológicos para antecipar o corte de carga.",
    "Painel gráfico (dashboard) e histórico de decisões para auditoria.",
]


## Opção 13: resume os resultados de todas as partes e lista limitações e melhorias.
def analise_final():
    print("\n" + LINHA)
    print(" ANÁLISE FINAL DOS RESULTADOS E LIMITAÇÕES")
    print(LINHA)
    with abrir_banco() as con:
        modulos = carregar_modulos(con)
        df = carregar_leituras(con)
        bateria = carregar_bateria(con)
        n_alertas = con.execute("SELECT COUNT(*), SUM(resolvido) FROM alertas").fetchone()
    por_dia = df.groupby("dia").agg(consumo=("consumo_kwh", "sum"), geracao=("geracao_kwh", "sum"),
                                    minimo=("carga_bateria_pct", "min"))
    print(f"\n  Base: {len(modulos)} módulos, {len(df)} leituras, {df['dia'].nunique()} dias.")
    print("  Balanço diário (consumo x geração) e carga mínima da bateria:")
    for dia, r in por_dia.iterrows():
        cobertura = r["geracao"] / r["consumo"] if r["consumo"] else 0
        print(f"    Dia {dia}: consumo {r['consumo']:6.1f} | geração {r['geracao']:6.1f} kWh "
              f"({cobertura:4.0%} coberto) | bateria mínima {r['minimo']:5.1f}%")

    alertas = gerar_alertas(df, modulos)
    print(f"\n  Regra booleana: {len(alertas)} situações de risco na semana "
          f"({sum(a['corte'] for a in alertas)} com corte recomendado). "
          f"Alertas no banco: {n_alertas[0]} ({n_alertas[1] or 0} resolvidos).")
    reg = treinar_regressao(df)
    print(f"  Modelo linear: consumo = {reg['a']:.2f} {reg['b']:+.3f}·T | R² teste = {reg['r2_teste']:.2f} "
          f"| MAE = {reg['mae']:.2f} kWh/h")
    series = sim.montar_series(pd.DataFrame(list(modulos.values())), df)
    cenarios = sim.executar_cenarios(series, bateria)
    base = cenarios["Registrado (sem corte)"]
    corte = cenarios["Registrado + corte de carga"]
    print(f"  Simulação: apagão de {base['energia_nao_atendida_kwh']:.1f} kWh sem corte x "
          f"{corte['energia_nao_atendida_kwh']:.1f} kWh com corte de carga.")

    print("\n  Conclusão: em dias de céu limpo a colônia é autossuficiente (geração > consumo),")
    print("  mas a bateria atual não atravessa uma tempestade de poeira de 2 dias. A regra booleana")
    print("  e o corte de carga reduzem o déficit, protegendo os módulos essenciais, porém a")
    print("  solução definitiva exige ampliar o armazenamento de energia.")

    print("\n  LIMITAÇÕES:")
    for texto in LIMITACOES:
        print(f"    - {texto}")
    print("\n  MELHORIAS FUTURAS:")
    for texto in MELHORIAS:
        print(f"    - {texto}")
