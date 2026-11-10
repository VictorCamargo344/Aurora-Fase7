####################################################################
# DECISÃO — aplica a regra booleana às leituras do banco e mostra
#           o circuito lógico.
#   A regra em si (fórmula, limiares, tabela-verdade) fica em
# regra_booleana.py; aqui ela é usada sobre os dados reais.
####################################################################

from src import gerar_circuito
from src import regra_booleana as rb
from src.banco import abrir_banco, carregar_leituras, carregar_modulos
from src.terminal import imprimir_tabela, ler_numero, ler_sim_nao


## Aplica a regra booleana a todos os módulos de um ciclo.
## Devolve uma lista de dicionários, um por módulo, com as variáveis e as saídas.
def avaliar_ciclo(df, modulos, perfil, ciclo):
    dados = df[df["ciclo"] == ciclo]
    if dados.empty:
        return []
    # G compara a geração com o consumo da colônia INTEIRA naquela hora.
    geracao_total = dados["geracao_kwh"].sum()
    consumo_total = dados["consumo_kwh"].sum()
    carga = dados["carga_bateria_pct"].iloc[0]
    resultado = []
    for r in dados.itertuples():
        modulo = modulos.get(r.id_modulo)
        if modulo is None:
            continue
        esperado = perfil.get((r.id_modulo, r.hora))
        a, g, e, p = rb.montar_variaveis(carga, geracao_total, consumo_total, r.consumo_kwh,
                                         esperado, modulo["prioridade"])
        risco, corte = rb.avaliar_regra(a, g, e, p)
        tipo, gravidade = rb.classificar_alerta(a, g, e)
        resultado.append({"id_modulo": r.id_modulo, "nome": modulo["nome"], "prioridade": modulo["prioridade"],
                          "ciclo": ciclo, "dia": r.dia, "hora": r.hora, "consumo": r.consumo_kwh,
                          "esperado": esperado, "carga": carga, "geracao_total": geracao_total,
                          "consumo_total": consumo_total, "A": a, "G": g, "E": e, "P": p,
                          "risco": risco, "corte": corte, "tipo": tipo, "gravidade": gravidade})
    return resultado


## Mostra a avaliação da regra para os módulos de um ciclo.
def imprimir_avaliacao(avaliacoes):
    if not avaliacoes:
        print("  Sem leituras nesse ciclo.")
        return
    a0 = avaliacoes[0]
    print(f"\n  Ciclo {a0['ciclo']} (dia {a0['dia']}, {a0['hora']:02d}h) | bateria {a0['carga']:.1f}% | "
          f"geração {a0['geracao_total']:.1f} kWh x consumo {a0['consumo_total']:.1f} kWh")
    imprimir_tabela(["Módulo", "Consumo", "Esperado", "A", "G", "E", "P", "RISCO", "CORTE"],
                    [[a["nome"], f"{a['consumo']:.2f}", f"{a['esperado']:.2f}" if a["esperado"] is not None else "-",
                      int(a["A"]), int(a["G"]), int(a["E"]), int(a["P"]),
                      "SIM" if a["risco"] else "não", "SIM" if a["corte"] else "não"] for a in avaliacoes])


## Opção 7: avaliar um ciclo do banco, testar a regra manualmente ou ver a tabela-verdade.
def menu_regra_booleana():
    print("\n--- REGRA BOOLEANA DE DECISÃO ---")
    print("  RISCO = (A AND NOT G) OR E        CORTE = RISCO AND NOT P")
    print(f"  A = bateria < {rb.LIMIAR_BATERIA_BAIXA_PCT:.0f}%   G = geração >= consumo da colônia")
    print(f"  E = consumo do módulo > {rb.FATOR_CONSUMO_EXCESSIVO:.0%} do esperado   "
          f"P = módulo essencial (prioridade <= {rb.PRIORIDADE_MAX_ESSENCIAL})")
    print("\n  1. Avaliar um ciclo registrado no banco")
    print("  2. Testar a regra informando A, G, E e P manualmente")
    print("  3. Exibir a tabela-verdade")
    opcao = ler_numero("Escolha: ", int, 1, 3)

    if opcao == 1:
        with abrir_banco() as con:
            df = carregar_leituras(con)
            modulos = carregar_modulos(con)
        if df.empty:
            print("  Não há leituras para avaliar.")
            return
        perfil = rb.calcular_perfil_esperado(df)
        print("  Dica: o ciclo 141 (dia 6, 20h) está no meio da tempestade de poeira.")
        ciclo = ler_numero(f"Ciclo (1 a {df['ciclo'].max()}): ", int, 1, int(df["ciclo"].max()))
        avaliacoes = avaliar_ciclo(df, modulos, perfil, ciclo)
        imprimir_avaliacao(avaliacoes)
        cortes = [a["nome"] for a in avaliacoes if a["corte"]]
        protegidos = [a["nome"] for a in avaliacoes if a["risco"] and not a["corte"]]
        if cortes:
            print(f"\n  DECISÃO: colocar em modo de economia -> {', '.join(cortes)}")
        if protegidos:
            print(f"  Em risco, mas essenciais (mantidos ligados e sinalizados) -> {', '.join(protegidos)}")
        if not cortes and not protegidos:
            print("\n  DECISÃO: operação normal, nenhum risco detectado.")
    elif opcao == 2:
        a = ler_sim_nao("  A - bateria abaixo de 30%?")
        g = ler_sim_nao("  G - geração cobre o consumo?")
        e = ler_sim_nao("  E - consumo excessivo no módulo?")
        p = ler_sim_nao("  P - módulo essencial?")
        risco, corte = rb.avaliar_regra(a, g, e, p)
        print(f"\n  (A AND NOT G) = {a and not g}  ->  RISCO = {risco}")
        print(f"  RISCO AND NOT P = {corte}  ->  CORTE = {corte}")
        if corte:
            print("  Resultado: módulo deve entrar em modo de economia.")
        elif risco:
            print("  Resultado: risco detectado, mas o módulo é essencial -> mantido ligado e sinalizado.")
        else:
            print("  Resultado: operação normal.")
    else:
        print()
        print(rb.formatar_tabela_verdade())


CIRCUITO_TEXTO = r"""
   A (bateria < 30%) -----------------------+
                                            |AND|---+
   G (geração >= consumo) --|NOT|-- ¬G -----+       |
                                                    |OR|---+------------> RISCO (alarme)
   E (consumo excessivo) ---------------------------+      |
                                                           +--+
                                                              |AND|-----> CORTE (relé)
   P (módulo essencial) ----|NOT|-- ¬P -----------------------+
"""


## Opção 8: circuito em texto, explicação do hardware, tabela-verdade e imagem.
def menu_circuito():
    print("\n--- CIRCUITO LÓGICO ---")
    print(CIRCUITO_TEXTO)
    print("  Portas usadas: 2 NOT, 2 AND, 1 OR.")
    print("  No hardware (ex.: Arduino), A, G e E viriam de sensores (medidor de carga,")
    print("  medidor solar, medidor de corrente do módulo) e P de uma chave de configuração.")
    print("  RISCO acionaria um LED/alarme e CORTE um relé que coloca o módulo em economia.\n")
    print(rb.formatar_tabela_verdade())
    caminho = gerar_circuito.gerar_circuito()
    print(f"\n  [OK] Diagrama do circuito salvo em: {caminho.name}")
