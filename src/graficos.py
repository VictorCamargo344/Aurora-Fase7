####################################################################
# GRÁFICOS — paleta e estilo comuns a todos os gráficos do sistema.
#   As cores seguem uma ordem fixa, escolhida para ser distinguível
# também por pessoas com daltonismo.
####################################################################

import matplotlib
matplotlib.use("Agg")  # gera os gráficos direto em arquivo, sem abrir janelas

COR_SUPERFICIE = "#fcfcfb"
COR_TEXTO = "#0b0b0b"
COR_TEXTO_2 = "#52514e"
COR_MUTED = "#898781"
COR_GRADE = "#e1e0d9"
COR_EIXO = "#c3c2b7"
CORES_SERIES = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100"]


## Aplica o estilo padrão: título à esquerda, grade discreta, eixos recessivos.
def estilizar(ax, titulo, xlabel, ylabel):
    ax.set_facecolor(COR_SUPERFICIE)
    ax.set_title(titulo, loc="left", color=COR_TEXTO, fontsize=12, pad=12)
    ax.set_xlabel(xlabel, color=COR_TEXTO_2)
    ax.set_ylabel(ylabel, color=COR_TEXTO_2)
    ax.grid(axis="y", color=COR_GRADE, linewidth=0.8)
    ax.set_axisbelow(True)
    for lado in ("top", "right"):
        ax.spines[lado].set_visible(False)
    for lado in ("left", "bottom"):
        ax.spines[lado].set_color(COR_EIXO)
    ax.tick_params(colors=COR_MUTED)
