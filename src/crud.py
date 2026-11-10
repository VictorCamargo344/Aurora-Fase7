####################################################################
# CRUD — cadastrar, listar, alterar e excluir módulos;
#        registrar e consultar leituras de sensores.
#   Todos os comandos SQL usam "?" (consulta parametrizada): o valor
# digitado nunca é colado no SQL, o que evita SQL injection.
####################################################################

import sqlite3

from src import regra_booleana as rb
from src.banco import abrir_banco, carregar_leituras, carregar_modulos
from src.estruturas import media_movel
from src.gerar_base import dia_e_hora
from src.terminal import (imprimir_tabela, ler_codigo_sensor, ler_numero, ler_opcao_lista,
                          ler_sim_nao, ler_texto)

TIPOS_MODULO = ["habitacao", "medico", "energia", "laboratorio",
                "armazenagem", "mineracao", "agricultura", "outro"]
STATUS_MODULO = ["ativo", "manutencao", "alerta"]


## Lê um ID e confirma que o módulo existe (busca O(1) no dicionário).
def escolher_modulo(con, mensagem="Informe o ID do módulo: "):
    modulos = carregar_modulos(con)
    if not modulos:
        print("  Nenhum módulo cadastrado.")
        return None
    print("  Módulos: " + ", ".join(f"{i}={m['nome']}" for i, m in modulos.items()))
    while True:
        id_modulo = ler_numero(mensagem, int, 1)
        if id_modulo in modulos:
            return modulos[id_modulo]
        print(f"  [ERRO] Não existe módulo com ID {id_modulo}.")


def cadastrar_modulo():
    print("\n--- CADASTRAR MÓDULO ---")
    nome = ler_texto("Nome do módulo: ")
    tipo = ler_opcao_lista("Tipo do módulo:", TIPOS_MODULO)
    codigo = ler_codigo_sensor("Código do sensor (ex.: 0x4A1B, Enter para deixar vazio): ")
    prioridade = ler_numero("Prioridade (1 = mais essencial ... 5 = menos essencial): ", int, 1, 5)
    status = ler_opcao_lista("Status:", STATUS_MODULO)
    consumo = ler_numero("Consumo base (kWh/dia): ", float, 0.1, 500)

    with abrir_banco() as con:
        try:
            with con:  # transação: confirma se der certo, desfaz se der erro
                cursor = con.execute(
                    "INSERT INTO modulos (nome, tipo, codigo_sensor, prioridade, status, consumo_base_kwh_dia) "
                    "VALUES (?, ?, ?, ?, ?, ?)", (nome, tipo, codigo, prioridade, status, consumo))
            print(f"\n  [OK] Módulo '{nome}' cadastrado com ID {cursor.lastrowid}.")
        except sqlite3.IntegrityError as erro:
            if "UNIQUE" in str(erro):
                print("\n  [ERRO] Já existe um módulo com esse nome ou código de sensor.")
            else:
                print(f"\n  [ERRO] Dados rejeitados pelo banco: {erro}")


def listar_modulos():
    print("\n--- MÓDULOS DA COLÔNIA ---")
    with abrir_banco() as con:
        # LEFT JOIN: módulos sem leituras também aparecem (com contagem 0).
        linhas = con.execute("""
            SELECT m.*, COUNT(l.id_leitura) AS n_leituras, AVG(l.consumo_kwh) AS media
            FROM modulos m LEFT JOIN leituras l ON l.id_modulo = m.id_modulo
            GROUP BY m.id_modulo ORDER BY m.id_modulo""").fetchall()
    if not linhas:
        print("  Nenhum módulo cadastrado.")
        return
    imprimir_tabela(
        ["ID", "Nome", "Tipo", "Sensor", "Prior.", "Status", "Base kWh/dia", "Leituras", "Média kWh/h"],
        [[l["id_modulo"], l["nome"], l["tipo"], l["codigo_sensor"] or "-", l["prioridade"], l["status"],
          f"{l['consumo_base_kwh_dia']:.1f}", l["n_leituras"],
          f"{l['media']:.2f}" if l["media"] is not None else "-"] for l in linhas])
    print(f"\n  Total: {len(linhas)} módulos. Prioridade <= {rb.PRIORIDADE_MAX_ESSENCIAL} = módulo essencial.")


def alterar_modulo():
    print("\n--- ALTERAR MÓDULO ---  (Enter mantém o valor atual)")
    with abrir_banco() as con:
        modulo = escolher_modulo(con)
        if modulo is None:
            return
        nome = ler_texto(f"Nome [{modulo['nome']}]: ", padrao=modulo["nome"])
        tipo = ler_opcao_lista("Tipo:", TIPOS_MODULO, padrao=modulo["tipo"])
        codigo = ler_codigo_sensor(f"Código do sensor [{modulo['codigo_sensor']}]: ", padrao=modulo["codigo_sensor"])
        prioridade = ler_numero(f"Prioridade 1-5 [{modulo['prioridade']}]: ", int, 1, 5, padrao=modulo["prioridade"])
        status = ler_opcao_lista("Status:", STATUS_MODULO, padrao=modulo["status"])
        consumo = ler_numero(f"Consumo base kWh/dia [{modulo['consumo_base_kwh_dia']}]: ", float, 0.1, 500,
                             padrao=modulo["consumo_base_kwh_dia"])
        try:
            with con:
                con.execute("UPDATE modulos SET nome=?, tipo=?, codigo_sensor=?, prioridade=?, status=?, "
                            "consumo_base_kwh_dia=? WHERE id_modulo=?",
                            (nome, tipo, codigo, prioridade, status, consumo, modulo["id_modulo"]))
            print(f"\n  [OK] Módulo {modulo['id_modulo']} atualizado.")
        except sqlite3.IntegrityError:
            print("\n  [ERRO] Já existe outro módulo com esse nome ou código de sensor. Nada foi alterado.")


def excluir_modulo():
    print("\n--- EXCLUIR MÓDULO ---")
    with abrir_banco() as con:
        modulo = escolher_modulo(con)
        if modulo is None:
            return
        n = con.execute("SELECT COUNT(*) FROM leituras WHERE id_modulo=?", (modulo["id_modulo"],)).fetchone()[0]
        print(f"  Atenção: as {n} leituras, os alertas e as manutenções deste módulo também serão excluídos.")
        if modulo["tipo"] == "energia":
            print("  Atenção: este é um módulo de ENERGIA; a colônia ficará sem geração registrada.")
        if not ler_sim_nao(f"  Confirma a exclusão de '{modulo['nome']}'?"):
            print("  Exclusão cancelada.")
            return
        with con:
            con.execute("DELETE FROM modulos WHERE id_modulo=?", (modulo["id_modulo"],))  # ON DELETE CASCADE
        print(f"\n  [OK] Módulo '{modulo['nome']}' excluído.")


def registrar_leitura():
    print("\n--- REGISTRAR LEITURA DE SENSORES ---")
    with abrir_banco() as con:
        modulo = escolher_modulo(con)
        if modulo is None:
            return
        # Sugere o próximo ciclo do módulo e a última carga registrada da bateria.
        ultimo = con.execute("SELECT MAX(ciclo), (SELECT carga_bateria_pct FROM leituras ORDER BY ciclo DESC LIMIT 1) "
                             "FROM leituras WHERE id_modulo=?", (modulo["id_modulo"],)).fetchone()
        proximo = (ultimo[0] or 0) + 1
        carga_ref = ultimo[1] if ultimo[1] is not None else 50.0

        ciclo = ler_numero(f"Ciclo (hora da missão) [{proximo}]: ", int, 1, padrao=proximo)
        dia, hora = dia_e_hora(ciclo)
        print(f"  -> dia {dia}, {hora:02d}h")
        consumo = ler_numero("Consumo (kWh): ", float, 0, 100)
        geracao = ler_numero("Geração (kWh) [0]: ", float, 0, 500, padrao=0.0) if modulo["tipo"] == "energia" else 0.0
        temperatura = ler_numero("Temperatura externa (°C, -150 a 50): ", float, -150, 50)
        luminosidade = ler_numero("Luminosidade (lux) [0]: ", float, 0, 200000, padrao=0.0)
        umidade = ler_numero("Umidade interna (%) [40]: ", float, 0, 100, padrao=40.0)
        carga = ler_numero(f"Carga da bateria (%) [{carga_ref:.1f}]: ", float, 0, 100, padrao=carga_ref)
        try:
            with con:
                con.execute(
                    "INSERT INTO leituras (id_modulo, ciclo, dia, hora, consumo_kwh, geracao_kwh, temperatura_c, "
                    "luminosidade_lux, umidade_interna_pct, carga_bateria_pct) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    (modulo["id_modulo"], ciclo, dia, hora, consumo, geracao, temperatura, luminosidade, umidade, carga))
            print(f"\n  [OK] Leitura do ciclo {ciclo} registrada para '{modulo['nome']}'.")
        except sqlite3.IntegrityError:
            print(f"\n  [ERRO] Já existe leitura de '{modulo['nome']}' no ciclo {ciclo}. Nada foi gravado.")


def consultar_leituras():
    print("\n--- CONSULTAR LEITURAS ---")
    print("  1. Por módulo (com média móvel de 24 h)")
    print("  2. Por dia (resumo da colônia, hora a hora)")
    print("  3. Por ciclo (todos os módulos)")
    filtro = ler_numero("Escolha: ", int, 1, 3)
    with abrir_banco() as con:
        df = carregar_leituras(con)
        modulos = carregar_modulos(con)
        if df.empty:
            print("  Nenhuma leitura registrada.")
            return

        if filtro == 1:
            modulo = escolher_modulo(con)
            dados = df[df["id_modulo"] == modulo["id_modulo"]].copy()
            if dados.empty:
                print("  Este módulo ainda não tem leituras.")
                return
            dados["media_24h"] = media_movel(dados["consumo_kwh"].tolist())
            n = ler_numero("Quantas leituras mais recentes exibir? [12]: ", int, 1, len(dados), padrao=min(12, len(dados)))
            print(f"\n  Últimas {n} leituras de {modulo['nome']}:")
            imprimir_tabela(["Ciclo", "Dia", "Hora", "Consumo", "Média 24h", "Geração", "Temp °C", "Lux", "Bateria %"],
                            [[r.ciclo, r.dia, f"{r.hora:02d}h", f"{r.consumo_kwh:.2f}", f"{r.media_24h:.2f}",
                              f"{r.geracao_kwh:.2f}", f"{r.temperatura_c:.1f}", f"{r.luminosidade_lux:.0f}",
                              f"{r.carga_bateria_pct:.1f}"] for r in dados.tail(n).itertuples()])
            print(f"\n  Consumo total: {dados['consumo_kwh'].sum():.1f} kWh em {len(dados)} leituras | "
                  f"máximo {dados['consumo_kwh'].max():.2f} kWh/h")

        elif filtro == 2:
            dia = ler_numero(f"Dia ({df['dia'].min()} a {df['dia'].max()}): ", int, int(df["dia"].min()), int(df["dia"].max()))
            dados = df[df["dia"] == dia]
            resumo = dados.groupby("hora").agg(consumo=("consumo_kwh", "sum"), geracao=("geracao_kwh", "sum"),
                                               temp=("temperatura_c", "mean"), bateria=("carga_bateria_pct", "first"))
            print(f"\n  Dia {dia} - colônia inteira:")
            imprimir_tabela(["Hora", "Consumo kWh", "Geração kWh", "Saldo kWh", "Temp °C", "Bateria %"],
                            [[f"{h:02d}h", f"{r.consumo:.1f}", f"{r.geracao:.1f}", f"{r.geracao - r.consumo:+.1f}",
                              f"{r.temp:.1f}", f"{r.bateria:.1f}"] for h, r in resumo.iterrows()])
            print(f"\n  Total do dia: consumo {resumo['consumo'].sum():.1f} kWh | geração {resumo['geracao'].sum():.1f} kWh "
                  f"| bateria entre {resumo['bateria'].min():.1f}% e {resumo['bateria'].max():.1f}%")

        else:
            ciclo = ler_numero(f"Ciclo (1 a {df['ciclo'].max()}): ", int, 1)
            dados = df[df["ciclo"] == ciclo]
            if dados.empty:
                print(f"  Nenhuma leitura no ciclo {ciclo}.")
                return
            print(f"\n  Ciclo {ciclo} (dia {dados['dia'].iloc[0]}, {dados['hora'].iloc[0]:02d}h):")
            imprimir_tabela(["Módulo", "Consumo", "Geração", "Temp °C", "Umid. %", "Bateria %"],
                            [[modulos.get(r.id_modulo, {}).get("nome", r.id_modulo), f"{r.consumo_kwh:.2f}",
                              f"{r.geracao_kwh:.2f}", f"{r.temperatura_c:.1f}", f"{r.umidade_interna_pct:.1f}",
                              f"{r.carga_bateria_pct:.1f}"] for r in dados.itertuples()])
