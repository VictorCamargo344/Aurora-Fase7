"""
SIFSM - Aurora Siger - Fase 7
Gera o desenho do circuito lógico da regra booleana (circuito_logico.png).

    RISCO = (A AND NOT G) OR E
    CORTE = RISCO AND NOT P

As portas são desenhadas com formas do Matplotlib. Ao lado do circuito
fica a tabela-verdade completa (16 combinações), calculada pelo próprio
módulo regra_booleana.py, para garantir que desenho e código coincidam.

Execução isolada (a partir da raiz do projeto):  python -m src.gerar_circuito
"""

from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import Circle, Polygon

from src.config import ARQUIVO_CIRCUITO
from src.regra_booleana import tabela_verdade

TINTA = "#0b0b0b"
TINTA_2 = "#52514e"
FUNDO = "#fcfcfb"
PORTA = "#cde2fb"       # preenchimento das portas
BORDA = "#2a78d6"       # contorno das portas
SAIDA_ATIVA = "#eb6834"


def fio(ax, pontos):
    """Desenha um fio passando pelos pontos (x, y) com segmentos retos."""
    xs, ys = zip(*pontos)
    ax.plot(xs, ys, color=TINTA, linewidth=1.6, solid_capstyle="round", zorder=1)


def juncao(ax, x, y):
    """Ponto de junção (bifurcação de um sinal)."""
    ax.add_patch(Circle((x, y), 0.08, color=TINTA, zorder=3))


def porta_and(ax, x0, y, largura=2.0, altura=2.0):
    """Porta AND: fundo reto e frente semicircular. Devolve o ponto de saída."""
    r = altura / 2
    xm = x0 + largura - r
    arco = [(xm + r * np.cos(t), y + r * np.sin(t)) for t in np.linspace(-np.pi / 2, np.pi / 2, 40)]
    pontos = [(x0, y - r)] + arco + [(x0, y + r)]
    ax.add_patch(Polygon(pontos, closed=True, facecolor=PORTA, edgecolor=BORDA, linewidth=2, zorder=2))
    ax.text(x0 + largura * 0.42, y, "AND", ha="center", va="center", fontsize=9, color=TINTA, zorder=4)
    return (x0 + largura, y)


def porta_or(ax, x0, y, largura=2.0, altura=2.0):
    """Porta OR: fundo côncavo e laterais curvas que se encontram na ponta."""
    r = altura / 2
    ponta = (x0 + largura, y)
    t = np.linspace(0, 1, 40)
    # Curvas de Bézier quadráticas: base -> ponta (inferior) e ponta -> topo (superior)
    inf = [((1 - s) ** 2 * x0 + 2 * (1 - s) * s * (x0 + largura * 0.6) + s ** 2 * ponta[0],
            (1 - s) ** 2 * (y - r) + 2 * (1 - s) * s * (y - r) + s ** 2 * y) for s in t]
    sup = [((1 - s) ** 2 * ponta[0] + 2 * (1 - s) * s * (x0 + largura * 0.6) + s ** 2 * x0,
            (1 - s) ** 2 * y + 2 * (1 - s) * s * (y + r) + s ** 2 * (y + r)) for s in t]
    fundo = [(x0 + 0.3 * np.cos(a), y + r * np.sin(a)) for a in np.linspace(np.pi / 2, -np.pi / 2, 30)]
    ax.add_patch(Polygon(inf + sup + fundo, closed=True, facecolor=PORTA, edgecolor=BORDA,
                         linewidth=2, zorder=2))
    ax.text(x0 + largura * 0.45, y, "OR", ha="center", va="center", fontsize=9, color=TINTA, zorder=4)
    return ponta


def entrada_or(x0, y_centro, y_pino, altura=2.0):
    """Ponto em que um fio encosta no fundo côncavo da porta OR."""
    r = altura / 2
    return x0 + 0.3 * np.sqrt(max(0.0, 1 - ((y_pino - y_centro) / r) ** 2))


def porta_not(ax, x0, y, largura=1.0):
    """Porta NOT: triângulo com a bolinha de negação. Devolve o ponto de saída."""
    pontos = [(x0, y - 0.45), (x0 + largura, y), (x0, y + 0.45)]
    ax.add_patch(Polygon(pontos, closed=True, facecolor=PORTA, edgecolor=BORDA, linewidth=2, zorder=2))
    ax.add_patch(Circle((x0 + largura + 0.1, y), 0.1, facecolor=FUNDO, edgecolor=BORDA, linewidth=2, zorder=2))
    ax.text(x0 + largura * 0.36, y, "NOT", ha="center", va="center", fontsize=6.5, color=TINTA, zorder=4)
    return (x0 + largura + 0.2, y)


def entrada(ax, nome, descricao, y):
    """Rótulo de uma variável de entrada (sensor) à esquerda do circuito."""
    ax.text(0.55, y, nome, ha="right", va="center", fontsize=13, fontweight="bold", color=TINTA)
    ax.text(0.55, y - 0.42, descricao, ha="right", va="top", fontsize=7.5, color=TINTA_2)


def desenhar_circuito(ax):
    """Desenha o circuito completo no eixo informado."""
    # Entradas (sensores do sistema)
    entrada(ax, "A", "sensor de carga\nbateria < 30%", 7.5)
    entrada(ax, "G", "medidor solar\ngeração >= consumo", 5.5)
    entrada(ax, "E", "medidor do módulo\nconsumo > 140% esperado", 3.0)
    entrada(ax, "P", "cadastro do módulo\nprioridade <= 2", 1.0)

    # NOT G -> AND(A, NOT G)
    saida_not_g = porta_not(ax, 2.0, 5.5)
    fio(ax, [(0.8, 5.5), (2.0, 5.5)])
    ax.text(saida_not_g[0] + 0.15, 5.75, "¬G", fontsize=8, color=TINTA_2)
    fio(ax, [(0.8, 7.5), (5.0, 7.5)])
    fio(ax, [saida_not_g, (4.2, 5.5), (4.2, 6.5), (5.0, 6.5)])
    saida_and1 = porta_and(ax, 5.0, 7.0)
    ax.text(7.15, 7.25, "A·¬G", fontsize=8, color=TINTA_2)

    # OR(A·NOT G, E) = RISCO
    x_or, y_or = 9.0, 5.0
    fio(ax, [saida_and1, (8.2, 7.0), (8.2, 5.5), (entrada_or(x_or, y_or, 5.5), 5.5)])
    fio(ax, [(0.8, 3.0), (8.2, 3.0), (8.2, 4.5), (entrada_or(x_or, y_or, 4.5), 4.5)])
    saida_or = porta_or(ax, x_or, y_or)

    # Saída RISCO e ramificação para o AND final
    fio(ax, [saida_or, (15.6, 5.0)])
    juncao(ax, 12.0, 5.0)
    ax.text(15.7, 5.0, "RISCO", va="center", fontsize=12, fontweight="bold", color=SAIDA_ATIVA)
    ax.text(15.7, 4.55, "alarme / LED vermelho", va="top", fontsize=7.5, color=TINTA_2)

    # NOT P -> AND(RISCO, NOT P) = CORTE
    saida_not_p = porta_not(ax, 6.0, 1.0)
    fio(ax, [(0.8, 1.0), (6.0, 1.0)])
    ax.text(saida_not_p[0] + 0.15, 1.25, "¬P", fontsize=8, color=TINTA_2)
    fio(ax, [saida_not_p, (13.0, 1.0)])
    fio(ax, [(12.0, 5.0), (12.0, 2.0), (13.0, 2.0)])
    saida_and2 = porta_and(ax, 13.0, 1.5)
    fio(ax, [saida_and2, (15.6, 1.5)])
    ax.text(15.7, 1.5, "CORTE", va="center", fontsize=12, fontweight="bold", color=SAIDA_ATIVA)
    ax.text(15.7, 1.05, "relé: módulo em economia", va="top", fontsize=7.5, color=TINTA_2)

    ax.set_xlim(-2.6, 19.5)
    ax.set_ylim(-0.3, 8.8)
    ax.set_aspect("equal")
    ax.axis("off")


def desenhar_tabela(ax):
    """Desenha a tabela-verdade (16 linhas) ao lado do circuito."""
    ax.axis("off")
    cabecalho = ["A", "G", "E", "P", "RISCO", "CORTE"]
    linhas = [[str(int(v)) for v in linha] for linha in tabela_verdade()]
    tabela = ax.table(cellText=linhas, colLabels=cabecalho, loc="center", cellLoc="center")
    tabela.auto_set_font_size(False)
    tabela.set_fontsize(8.5)
    tabela.scale(1, 1.25)
    for (lin, col), celula in tabela.get_celld().items():
        celula.set_edgecolor("#e1e0d9")
        if lin == 0:
            celula.set_text_props(fontweight="bold", color=TINTA)
            celula.set_facecolor("#f0efec")
        elif col >= 4 and celula.get_text().get_text() == "1":
            celula.set_text_props(fontweight="bold", color=SAIDA_ATIVA)
    ax.set_title("Tabela-verdade", fontsize=11, color=TINTA)


def gerar_circuito(arquivo=ARQUIVO_CIRCUITO):
    """Gera a imagem completa (circuito + tabela-verdade) e devolve o caminho."""
    fig = plt.figure(figsize=(15, 6.2), facecolor=FUNDO)
    grade = fig.add_gridspec(1, 2, width_ratios=[3.3, 1])
    ax_circuito = fig.add_subplot(grade[0])
    ax_tabela = fig.add_subplot(grade[1])
    desenhar_circuito(ax_circuito)
    desenhar_tabela(ax_tabela)
    fig.suptitle("Circuito lógico de decisão energética   |   RISCO = (A · ¬G) + E      CORTE = RISCO · ¬P",
                 fontsize=13, color=TINTA, x=0.02, ha="left")
    fig.text(0.02, 0.03, "Entradas: 1 = verdadeiro, 0 = falso.  Módulos essenciais (P = 1) nunca são "
             "cortados, apenas sinalizados pelo alarme de RISCO.", fontsize=8.5, color=TINTA_2)
    fig.tight_layout(rect=(0, 0.05, 1, 0.94))
    fig.savefig(arquivo, dpi=140, facecolor=FUNDO)
    plt.close(fig)
    return Path(arquivo)


if __name__ == "__main__":
    caminho = gerar_circuito()
    print(f"Circuito lógico salvo em: {caminho.name}")
