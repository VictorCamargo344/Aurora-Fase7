"""
SIFSM - Aurora Siger - Fase 7
Gera as evidências de execução (prints) do sistema.

Executa o codigo_fonte.py com entradas roteirizadas (como se alguém digitasse
no teclado), guarda a saída REAL do terminal em .txt e a desenha em .png,
na pasta graficos_ou_imagens/prints_execucao/.

Execução (a partir da raiz do projeto):  python -m src.gerar_prints_execucao
(a base é recriada no início, para que os prints saiam sempre iguais)
"""

import os
import subprocess
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from src import gerar_base
from src.config import PASTA_GRAFICOS, RAIZ as PASTA

DESTINO = PASTA_GRAFICOS / "prints_execucao"
INICIO_MENU = "=" * 72

# (nome do arquivo, título exibido no print, entradas digitadas, manter o menu?)
ROTEIROS = [
    ("01_menu_principal", "python codigo_fonte.py", "0\n", True),
    ("02_crud_cadastrar_listar", "python codigo_fonte.py  (opções 1 e 2)",
     "1\nEstufa Verde\n7\n0x5b2c\n3\n1\n28.5\n\n2\n\n0\n", False),
    ("03_crud_leitura_alterar_excluir", "python codigo_fonte.py  (opções 5, 6, 3 e 4)",
     "5\n7\n\n1.3\n-60\n\n\n\n\n6\n1\n7\n\n\n3\n7\n\n\n\n2\n\n\n\n4\n7\ns\n\n0\n", False),
    ("04_tratamento_de_erros", "python codigo_fonte.py  (entradas inválidas de propósito)",
     "abc\n99\n1\n\nHabitat Alpha\n9\n1\n123\n0x1A2F\ndez\n1\n1\n-5\n10\n\n4\n42\n1\ntalvez\nn\n\n0\n", False),
    ("05_regra_booleana_ciclo_141", "python codigo_fonte.py  (opção 7 -> ciclo 141)", "7\n1\n141\n\n0\n", False),
    ("06_circuito_logico", "python codigo_fonte.py  (opção 8)", "8\n\n0\n", False),
    ("07_fila_de_alertas", "python codigo_fonte.py  (opção 9)", "9\n1\n0\n\n0\n", False),
    ("08_simulacao_computacional", "python simulacao_computacional.py", None, False),
    ("09_modelo_linear", "python codigo_fonte.py  (opção 11)", "11\n\n\n\n0\n", False),
    ("10_analisar_sustentabilidade", "python codigo_fonte.py  (opção 12)", "12\n\n0\n", False),
    ("11_analise_final", "python codigo_fonte.py  (opção 13)", "13\n\n0\n", False),
]


def executar(script, entrada=None):
    """Roda um script Python do projeto e devolve tudo o que ele escreveu no terminal."""
    resultado = subprocess.run([sys.executable, script], input=entrada or "", capture_output=True,
                               text=True, encoding="utf-8", cwd=PASTA,
                               env={**os.environ, "PYTHONIOENCODING": "utf-8"})
    return resultado.stdout + resultado.stderr


def limpar(texto, manter_menu):
    """Remove o menu repetido e as linhas 'Pressione Enter' para o print ficar enxuto."""
    if not manter_menu and INICIO_MENU in texto:
        inicio = texto.index(INICIO_MENU)
        menu = texto[inicio:texto.index("Escolha uma opção:", inicio)]
        texto = texto.replace(menu, "")
    linhas = [linha for linha in texto.splitlines() if "Pressione Enter" not in linha]
    return "\n".join(linhas).strip() + "\n"


def salvar(nome, texto, titulo):
    """Salva o texto em .txt e desenha um 'print' de terminal em .png."""
    (DESTINO / f"{nome}.txt").write_text(texto, encoding="utf-8")
    linhas = texto.splitlines()
    largura = max(len(linha) for linha in linhas)
    altura = 0.6 + len(linhas) * 0.165
    fig = plt.figure(figsize=(max(8, largura * 0.079 + 0.4), altura), facecolor="#1a1a19")
    fig.text(0.01, 1 - 0.25 / altura, f"$ {titulo}", color="#86b6ef", family="monospace", fontsize=9, va="top")
    fig.text(0.01, 1 - 0.5 / altura, texto, color="#f0efec", family="monospace", fontsize=9,
             va="top", linespacing=1.22)
    fig.savefig(DESTINO / f"{nome}.png", dpi=110, facecolor="#1a1a19")
    plt.close(fig)
    print(f"  {nome}.png ({len(linhas)} linhas)")


def main():
    DESTINO.mkdir(parents=True, exist_ok=True)
    print("Recriando a base simulada...")
    gerar_base.gerar_base()
    print("Gerando prints de execução:")
    for nome, titulo, entrada, manter_menu in ROTEIROS:
        script = "simulacao_computacional.py" if entrada is None else "codigo_fonte.py"
        salvar(nome, limpar(executar(script, entrada), manter_menu), titulo)
    salvar("12_testes_automaticos", executar("testes.py").strip() + "\n", "python testes.py")
    print(f"Prints salvos em: {DESTINO.relative_to(PASTA)}")


if __name__ == "__main__":
    main()
