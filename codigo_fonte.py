####################################################################
# SIFSM — SISTEMA INTEGRADO DE FUTURO SUSTENTÁVEL EM MARTE
#   Aurora Siger — Fase 7 — Gestão energética sustentável da colônia
#
#   Ponto de entrada do sistema. Este arquivo não calcula nada:
# ele garante que o banco existe, mostra o menu e chama as funções
# dos módulos em src/ (e da simulacao_computacional.py) conforme a
# opção escolhida.
#
#   Execução:  python codigo_fonte.py
####################################################################

import sqlite3

import simulacao_computacional as sim
from src.alertas import menu_fila_alertas
from src.analise import analisar_sustentabilidade, analise_final
from src.banco import garantir_banco, recriar_base
from src.config import ARQUIVO_BANCO
from src.crud import (alterar_modulo, cadastrar_modulo, consultar_leituras, excluir_modulo,
                      listar_modulos, registrar_leitura)
from src.decisao import menu_circuito, menu_regra_booleana
from src.regressao import menu_regressao
from src.terminal import configurar_saida_utf8, ler_numero, pausar


## Imprime as opções disponíveis.
def exibir_menu():
    # Aspas triplas permitem string de várias linhas num print só.
    print("""
========================================================================
 SIFSM - Aurora Siger | Gestão Energética Sustentável em Marte
========================================================================
 CADASTRO E CONSULTA (CRUD)
   1. Cadastrar módulo
   2. Listar módulos
   3. Alterar módulo
   4. Excluir módulo
   5. Registrar leitura de sensores
   6. Consultar leituras
 DECISÃO E ANÁLISE
   7. Regra booleana (risco e corte de carga)
   8. Circuito lógico
   9. Fila de prioridade de alertas
  10. Simulação computacional da bateria
  11. Modelo linear (consumo x temperatura)
  12. Analisar sustentabilidade da colônia
  13. Análise final e limitações
 SISTEMA
  14. Recriar base de dados simulada
   0. Sair""")


## Executa a opção escolhida. Devolve False quando o usuário pede para sair.
def executar_opcao(opcao):
    if opcao == 1:
        cadastrar_modulo()
    elif opcao == 2:
        listar_modulos()
    elif opcao == 3:
        alterar_modulo()
    elif opcao == 4:
        excluir_modulo()
    elif opcao == 5:
        registrar_leitura()
    elif opcao == 6:
        consultar_leituras()

    elif opcao == 7:
        menu_regra_booleana()
    elif opcao == 8:
        menu_circuito()
    elif opcao == 9:
        menu_fila_alertas()
    elif opcao == 10:
        # A simulação fica num arquivo próprio (exigência da entrega);
        # aqui só se pergunta o tamanho do Monte Carlo e se chama.
        n = ler_numero("Número de execuções do Monte Carlo (100 a 2000) [500]: ", int, 100, 2000, padrao=500)
        print("  Simulando... (pode levar alguns segundos)")
        sim.executar_simulacao_completa(ARQUIVO_BANCO, n_monte_carlo=int(n))
    elif opcao == 11:
        menu_regressao()
    elif opcao == 12:
        analisar_sustentabilidade()
    elif opcao == 13:
        analise_final()

    elif opcao == 14:
        recriar_base()
    elif opcao == 0:
        print("Encerrando o SIFSM. Até logo!")
        return False
    return True


def main():
    configurar_saida_utf8()
    print("Bem-vindo ao SIFSM - Sistema Integrado de Futuro Sustentável em Marte.")
    try:
        if not garantir_banco():
            print("  Sem banco de dados não é possível usar o sistema. Encerrando.")
            return

        # Loop infinito: só termina quando o usuário escolhe a opção 0.
        # Os dados NÃO são carregados uma vez aqui fora: como o CRUD altera
        # o banco, cada opção relê o que precisa e sempre vê o estado atual.
        while True:
            exibir_menu()
            # ler_numero repete a pergunta até receber um número entre 0 e 14.
            opcao = ler_numero("Escolha uma opção: ", int, 0, 14)
            # Tratamento de erros por opção: um erro não derruba o sistema inteiro.
            try:
                if not executar_opcao(opcao):
                    break
            except FileNotFoundError as erro:
                print(f"\n  [ERRO] {erro}")
            except sqlite3.Error as erro:
                print(f"\n  [ERRO DE BANCO] Não foi possível concluir a opção {opcao}: {erro}")
            except ValueError as erro:
                print(f"\n  [ERRO] Dados insuficientes ou inválidos: {erro}")
            pausar()

    # Ctrl+C ou fim da entrada: encerra com mensagem, sem mostrar erro do Python.
    except (KeyboardInterrupt, EOFError):
        print("\n\nExecução interrompida pelo usuário. Encerrando o SIFSM.")


# Garante que o menu só dispare quando o arquivo for executado
# diretamente, e não se algo for importado dele.
if __name__ == "__main__":
    main()
