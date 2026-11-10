####################################################################
# BANCO — conexão com o SQLite e carregamento dos dados.
#   Todas as telas abrem o banco por aqui, com as chaves estrangeiras
# ligadas (sem isso o SQLite ignora o ON DELETE CASCADE).
####################################################################

import sqlite3
from contextlib import contextmanager

import pandas as pd

from src import gerar_base
from src.config import ARQUIVO_BANCO, ARQUIVO_CSV
from src.terminal import ler_sim_nao


## Abre o banco e garante que ele será fechado ao final, mesmo com erro.
## Uso:  with abrir_banco() as con: ...
@contextmanager
def abrir_banco():
    if not ARQUIVO_BANCO.exists():
        raise FileNotFoundError("Banco de dados não encontrado. Use a opção 14 para recriá-lo.")
    con = sqlite3.connect(ARQUIVO_BANCO)
    con.row_factory = sqlite3.Row      # permite acessar colunas pelo nome: linha["nome"]
    con.execute("PRAGMA foreign_keys = ON")
    try:
        yield con
    finally:
        con.close()


## ESTRUTURA DE DADOS: dicionário {id_modulo: dados do módulo}.
## É uma tabela hash: buscar um módulo pelo id custa O(1), sem varrer a lista.
def carregar_modulos(con):
    return {linha["id_modulo"]: dict(linha) for linha in con.execute("SELECT * FROM modulos ORDER BY id_modulo")}


def carregar_leituras(con):
    return pd.read_sql_query("SELECT * FROM leituras ORDER BY ciclo, id_modulo", con)


def carregar_bateria(con):
    linha = con.execute("SELECT * FROM baterias ORDER BY id_bateria LIMIT 1").fetchone()
    if linha is None:
        raise ValueError("Nenhum banco de baterias cadastrado.")
    return dict(linha)


## Na inicialização, oferece criar o banco caso ele não exista.
def garantir_banco():
    if ARQUIVO_BANCO.exists():
        return True
    print(f"  O banco data/{ARQUIVO_BANCO.name} não foi encontrado.")
    if ler_sim_nao("  Deseja gerar a base de dados simulada agora?"):
        total = gerar_base.gerar_base()
        print(f"  [OK] {total} leituras geradas.")
        return True
    return False


## Opção 14: apaga tudo e gera de novo a base simulada.
def recriar_base():
    print("\n--- RECRIAR BASE DE DADOS SIMULADA ---")
    print("  Isto apaga TODOS os dados atuais (inclusive cadastros feitos pelo menu)")
    print("  e gera novamente os 7 dias de leituras simuladas.")
    if ler_sim_nao("  Deseja continuar?"):
        total = gerar_base.gerar_base()
        print(f"  [OK] Base recriada: {total} leituras gravadas em data/{ARQUIVO_BANCO.name} "
              f"e exportadas para data/{ARQUIVO_CSV.name}.")
    else:
        print("  Operação cancelada.")
