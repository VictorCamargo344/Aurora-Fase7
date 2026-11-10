####################################################################
# REGRESSÃO — modelo linear simples: consumo da colônia x temperatura.
#   consumo_total(t) = a + b * temperatura(t)
# O modelo é usado para prever o consumo da noite e, com isso,
# estimar a autonomia da bateria.
####################################################################

import matplotlib.pyplot as plt
import numpy as np
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.model_selection import train_test_split

from src.banco import abrir_banco, carregar_bateria, carregar_leituras
from src.config import PASTA_GRAFICOS, RAIZ
from src.graficos import COR_SUPERFICIE, COR_TEXTO, CORES_SERIES, estilizar
from src.terminal import ler_numero

TEMPERATURA_NOTURNA_PADRAO = -68.0


## Treina a regressão: 70% dos ciclos treinam o modelo e 30% testam (dados nunca vistos).
def treinar_regressao(df):
    # Um ponto por hora: temperatura da colônia x consumo somado de todos os módulos.
    por_ciclo = df.groupby("ciclo").agg(temperatura=("temperatura_c", "mean"), consumo=("consumo_kwh", "sum"))
    if len(por_ciclo) < 10:
        raise ValueError("São necessários pelo menos 10 ciclos para treinar a regressão.")
    x = por_ciclo[["temperatura"]].to_numpy()
    y = por_ciclo["consumo"].to_numpy()
    x_treino, x_teste, y_treino, y_teste = train_test_split(x, y, test_size=0.3, random_state=42)
    modelo = LinearRegression().fit(x_treino, y_treino)
    previsto = modelo.predict(x_teste)
    return {"modelo": modelo, "a": float(modelo.intercept_), "b": float(modelo.coef_[0]),
            "r2_teste": r2_score(y_teste, previsto), "r2_treino": modelo.score(x_treino, y_treino),
            "mae": mean_absolute_error(y_teste, previsto),
            "rmse": float(np.sqrt(mean_squared_error(y_teste, previsto))),
            "correlacao": float(np.corrcoef(x[:, 0], y)[0, 1]),
            "x": x[:, 0], "y": y, "n_treino": len(y_treino), "n_teste": len(y_teste)}


## Prevê o consumo por hora na temperatura informada e quantas horas a bateria aguenta sem sol.
## Só conta a energia ACIMA da carga mínima (abaixo dela a bateria se degrada).
def estimar_autonomia(reg, temperatura, carga_pct, bateria):
    consumo_previsto = float(reg["modelo"].predict(np.array([[temperatura]]))[0])
    disponivel = max(0.0, (carga_pct - bateria["carga_minima_pct"]) / 100 * bateria["capacidade_kwh"])
    horas = disponivel / consumo_previsto if consumo_previsto > 0 else float("inf")
    return consumo_previsto, disponivel, horas


def grafico_regressao(reg, arquivo):
    fig, ax = plt.subplots(figsize=(9, 4.8), facecolor=COR_SUPERFICIE)
    ax.scatter(reg["x"], reg["y"], s=30, color=CORES_SERIES[0], alpha=0.75,
               edgecolor=COR_SUPERFICIE, linewidth=1, label="Leituras (1 ponto = 1 hora)")
    xs = np.linspace(reg["x"].min(), reg["x"].max(), 50)
    ax.plot(xs, reg["a"] + reg["b"] * xs, color=CORES_SERIES[1], linewidth=2,
            label=f"Reta: consumo = {reg['a']:.2f} {reg['b']:+.3f}·T   (R² teste = {reg['r2_teste']:.2f})")
    estilizar(ax, "Modelo linear: consumo da colônia x temperatura externa",
              "Temperatura externa (°C)", "Consumo da colônia (kWh/h)")
    ax.legend(frameon=False, fontsize=9, labelcolor=COR_TEXTO)
    fig.tight_layout()
    fig.savefig(arquivo, dpi=130)
    plt.close(fig)


## Opção 11: treina, interpreta, salva o gráfico e estima a autonomia.
def menu_regressao():
    print("\n--- MODELO LINEAR SIMPLES: CONSUMO x TEMPERATURA ---")
    with abrir_banco() as con:
        df = carregar_leituras(con)
        bateria = carregar_bateria(con)
    reg = treinar_regressao(df)
    print(f"  Dados: {len(reg['y'])} ciclos ({reg['n_treino']} para treino, {reg['n_teste']} para teste)")
    print(f"  Correlação de Pearson (temperatura x consumo): r = {reg['correlacao']:.3f}")
    print(f"\n  Equação: consumo (kWh/h) = {reg['a']:.3f} + ({reg['b']:.4f}) x temperatura (°C)")
    print(f"  Interpretação: a cada 1 °C a menos, a colônia consome {abs(reg['b']):.3f} kWh a mais por hora")
    print(f"                 (aquecimento); em 10 °C de queda são {abs(reg['b']) * 10:.2f} kWh/h a mais.")
    print(f"\n  R² no treino = {reg['r2_treino']:.3f} | R² no teste = {reg['r2_teste']:.3f}")
    print(f"  Erro médio absoluto (MAE) = {reg['mae']:.2f} kWh/h | RMSE = {reg['rmse']:.2f} kWh/h")

    PASTA_GRAFICOS.mkdir(exist_ok=True)
    arquivo = PASTA_GRAFICOS / "regressao_consumo_temperatura.png"
    grafico_regressao(reg, arquivo)
    print(f"  Gráfico salvo em: {arquivo.relative_to(RAIZ)}")

    print("\n  Previsão de apoio à decisão (autonomia noturna da bateria):")
    temperatura = ler_numero(f"  Temperatura prevista para a noite (°C) [{TEMPERATURA_NOTURNA_PADRAO}]: ",
                             float, -150, 50, padrao=TEMPERATURA_NOTURNA_PADRAO)
    carga_atual = float(df.sort_values("ciclo")["carga_bateria_pct"].iloc[-1])
    carga = ler_numero(f"  Carga atual da bateria (%) [{carga_atual:.1f}]: ", float, 0, 100, padrao=carga_atual)
    consumo, disponivel, horas = estimar_autonomia(reg, temperatura, carga, bateria)
    print(f"\n  Consumo previsto a {temperatura:.1f} °C: {consumo:.2f} kWh/h")
    print(f"  Energia disponível acima do mínimo de {bateria['carga_minima_pct']:.0f}%: {disponivel:.1f} kWh")
    print(f"  Autonomia estimada sem geração solar: {horas:.1f} horas")
