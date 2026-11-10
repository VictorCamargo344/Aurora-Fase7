####################################################################
# ALERTAS — transforma as situações de risco da regra booleana em
#           alertas, grava no banco e organiza na fila de prioridade.
####################################################################

from src import regra_booleana as rb
from src.banco import abrir_banco, carregar_leituras, carregar_modulos
from src.decisao import avaliar_ciclo
from src.estruturas import FilaAlertas
from src.terminal import imprimir_tabela, ler_numero


## Texto explicativo de um alerta a partir da avaliação da regra.
def mensagem_alerta(av):
    partes = []
    if av["A"] and not av["G"]:
        partes.append(f"bateria em {av['carga']:.1f}% e geração insuficiente "
                      f"({av['geracao_total']:.1f} de {av['consumo_total']:.1f} kWh)")
    if av["E"]:
        partes.append(f"consumo {av['consumo']:.2f} kWh acima de {rb.FATOR_CONSUMO_EXCESSIVO:.0%} "
                      f"do esperado ({av['esperado']:.2f} kWh)")
    acao = "corte de carga recomendado" if av["corte"] else "módulo essencial mantido ligado"
    return "; ".join(partes) + f" -> {acao}"


## Aplica a regra a todos os ciclos (ou aos ciclos informados) e devolve os alertas.
def gerar_alertas(df, modulos, ciclos=None):
    perfil = rb.calcular_perfil_esperado(df)
    ciclos = sorted(df["ciclo"].unique()) if ciclos is None else ciclos
    alertas = []
    for ciclo in ciclos:
        for av in avaliar_ciclo(df, modulos, perfil, int(ciclo)):
            if av["risco"]:
                av["mensagem"] = mensagem_alerta(av)
                alertas.append(av)
    return alertas


## Atualiza a tabela de alertas com o resultado atual da regra:
## os pendentes antigos são recalculados (os dados ou a regra podem ter mudado)
## e os já resolvidos pelo operador são preservados, sem duplicar.
## Devolve quantos alertas ficaram pendentes.
def sincronizar_alertas(con, alertas):
    with con:
        con.execute("DELETE FROM alertas WHERE resolvido = 0")
        con.executemany(
            "INSERT INTO alertas (id_modulo, ciclo, tipo, gravidade, mensagem) SELECT ?, ?, ?, ?, ? "
            "WHERE NOT EXISTS (SELECT 1 FROM alertas WHERE id_modulo = ? AND ciclo = ? AND tipo = ?)",
            [(a["id_modulo"], a["ciclo"], a["tipo"], a["gravidade"], a["mensagem"],
              a["id_modulo"], a["ciclo"], a["tipo"]) for a in alertas])
    return con.execute("SELECT COUNT(*) FROM alertas WHERE resolvido = 0").fetchone()[0]


## Monta a fila de prioridade com os alertas ainda não resolvidos do banco.
def carregar_fila(con, modulos):
    fila = FilaAlertas()
    for linha in con.execute("SELECT * FROM alertas WHERE resolvido = 0"):
        alerta = dict(linha)
        modulo = modulos.get(alerta["id_modulo"], {})
        alerta["nome"] = modulo.get("nome", "?")
        alerta["prioridade"] = modulo.get("prioridade", 5)
        fila.inserir(alerta)
    return fila


def imprimir_alertas(alertas):
    imprimir_tabela(["#", "Gravidade", "Módulo", "Prior.", "Ciclo", "Mensagem"],
                    [[i, rb.GRAVIDADE_TEXTO[a["gravidade"]], a["nome"], a["prioridade"], a["ciclo"],
                      a["mensagem"][:70] + ("..." if len(a["mensagem"]) > 70 else "")]
                     for i, a in enumerate(alertas, start=1)])


## Opção 9: gera os alertas, monta a fila e permite atender um por um.
def menu_fila_alertas():
    print("\n--- FILA DE PRIORIDADE DE ALERTAS (heapq) ---")
    with abrir_banco() as con:
        modulos = carregar_modulos(con)
        df = carregar_leituras(con)
        alertas = gerar_alertas(df, modulos)
        pendentes = sincronizar_alertas(con, alertas)
        fila = carregar_fila(con, modulos)
        print(f"  Regra aplicada a {df['ciclo'].nunique()} ciclos: {len(alertas)} situações de risco; "
              f"{pendentes} alertas pendentes no banco (os já resolvidos não voltam).")
        if not fila:
            print("  Nenhum alerta pendente.")
            return
        contagem = fila.contagem_por_gravidade()
        print(f"  Pendentes: {len(fila)}  (crítico: {contagem[1]} | alto: {contagem[2]} | moderado: {contagem[3]})")

        while True:
            print("\n  Próximos alertas na fila (mais urgente primeiro):")
            imprimir_alertas(fila.proximos(5))
            print("\n  1. Atender (resolver) o alerta mais urgente   2. Ver os 15 primeiros   0. Voltar")
            opcao = ler_numero("Escolha: ", int, 0, 2)
            if opcao == 0:
                break
            if opcao == 2:
                imprimir_alertas(fila.proximos(15))
                continue
            alerta = fila.atender()
            with con:
                con.execute("UPDATE alertas SET resolvido = 1 WHERE id_alerta = ?", (alerta["id_alerta"],))
            print(f"\n  [OK] Alerta {alerta['id_alerta']} ({alerta['nome']}, ciclo {alerta['ciclo']}) marcado como resolvido.")
            print(f"  Mensagem: {alerta['mensagem']}")
            print(f"  Restam {len(fila)} alertas pendentes.")
            if not fila:
                break
