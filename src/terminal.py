####################################################################
# TERMINAL — entrada de dados com tratamento de erros e saída formatada.
#   Toda leitura do teclado passa por estas funções: elas repetem a
# pergunta até receber um valor válido, então nenhuma digitação
# errada derruba o sistema.
####################################################################

import re
import sys


## Lê um texto não vazio (ou devolve o padrão se o usuário só apertar Enter).
def ler_texto(mensagem, obrigatorio=True, tamanho_max=40, padrao=None):
    while True:
        valor = input(mensagem).strip()
        if not valor and padrao is not None:
            return padrao
        if not valor and not obrigatorio:
            return None
        if not valor:
            print("  [ERRO] Este campo é obrigatório.")
        elif len(valor) > tamanho_max:
            print(f"  [ERRO] Use no máximo {tamanho_max} caracteres.")
        else:
            return valor


## Lê um número (int ou float) dentro da faixa [minimo, maximo].
def ler_numero(mensagem, tipo=float, minimo=None, maximo=None, padrao=None):
    while True:
        # Aceita vírgula como separador decimal (padrão brasileiro).
        bruto = input(mensagem).strip().replace(",", ".")
        if not bruto and padrao is not None:
            return padrao
        try:
            valor = tipo(bruto)
        except ValueError:
            nome = "inteiro" if tipo is int else "numérico"
            print(f"  [ERRO] '{bruto}' não é um valor {nome} válido.")
            continue
        if minimo is not None and valor < minimo:
            print(f"  [ERRO] O valor deve ser maior ou igual a {minimo}.")
        elif maximo is not None and valor > maximo:
            print(f"  [ERRO] O valor deve ser menor ou igual a {maximo}.")
        else:
            return valor


## Mostra uma lista numerada e devolve o item escolhido.
## Com padrao informado, Enter mantém o valor atual.
def ler_opcao_lista(titulo, opcoes, padrao=None):
    print(titulo)
    for i, opcao in enumerate(opcoes, start=1):
        marca = " (atual)" if opcao == padrao else ""
        print(f"   {i}. {opcao}{marca}")
    indice = ler_numero("  Escolha o número: " if padrao is None else "  Escolha o número (Enter mantém): ",
                        int, 1, len(opcoes), padrao=-1 if padrao is not None else None)
    return padrao if indice == -1 else opcoes[indice - 1]


## Pergunta de sim/não. Aceita s, sim, n, não.
def ler_sim_nao(mensagem):
    while True:
        resposta = input(f"{mensagem} (s/n): ").strip().lower()
        if resposta in ("s", "sim"):
            return True
        if resposta in ("n", "nao", "não"):
            return False
        print("  [ERRO] Responda apenas 's' ou 'n'.")


## Lê o código hexadecimal do sensor no formato 0x0000 (opcional).
def ler_codigo_sensor(mensagem, padrao=None):
    while True:
        valor = input(mensagem).strip()
        if not valor:
            return padrao
        if re.fullmatch(r"0x[0-9A-Fa-f]{4}", valor):
            return valor[:2] + valor[2:].upper()
        print("  [ERRO] Use o formato hexadecimal 0x seguido de 4 dígitos (ex.: 0x4A1B).")


def pausar():
    input("\nPressione Enter para voltar ao menu...")


## Imprime uma tabela alinhada: a largura de cada coluna é a do maior valor.
def imprimir_tabela(colunas, linhas):
    textos = [[str(c) for c in linha] for linha in linhas]
    larguras = [max(len(str(col)), *(len(l[i]) for l in textos)) if textos else len(str(col))
                for i, col in enumerate(colunas)]
    print("  " + "  ".join(str(c).ljust(w) for c, w in zip(colunas, larguras)))
    print("  " + "  ".join("-" * w for w in larguras))
    for linha in textos:
        print("  " + "  ".join(v.ljust(w) for v, w in zip(linha, larguras)))


## Garante acentos e símbolos (π, ·) no terminal, inclusive com saída redirecionada.
def configurar_saida_utf8():
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass  # terminal que não permite reconfigurar: segue com a codificação padrão
