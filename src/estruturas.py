####################################################################
# ESTRUTURAS DE DADOS — fila de prioridade (heap) e janela deslizante (deque).
#   (O dicionário de módulos fica em banco.carregar_modulos.)
####################################################################

import heapq
from collections import deque

JANELA_MEDIA_MOVEL = 24   # horas usadas na média móvel


class FilaAlertas:
    """
    Fila de prioridade implementada com heap binário (módulo heapq).
    Ordem de atendimento:
      1º menor gravidade (1 = crítico), 2º menor prioridade do módulo
      (1 = mais essencial), 3º ciclo mais recente.
    Inserir e retirar custam O(log n); ver o mais urgente custa O(1).
    Uma lista comum exigiria reordenar tudo (O(n log n)) a cada alerta novo.
    """

    def __init__(self):
        self._heap = []
        self._contador = 0   # desempate: garante que nunca se comparem dois dicionários

    def inserir(self, alerta):
        # O sinal de menos no ciclo faz o mais recente vir primeiro.
        chave = (alerta["gravidade"], alerta["prioridade"], -alerta["ciclo"], self._contador)
        heapq.heappush(self._heap, (chave, alerta))
        self._contador += 1

    def atender(self):
        """Remove e devolve o alerta mais urgente (ou None se a fila estiver vazia)."""
        return heapq.heappop(self._heap)[1] if self._heap else None

    def proximos(self, n):
        """Os n alertas mais urgentes, sem removê-los."""
        return [item[1] for item in heapq.nsmallest(n, self._heap)]

    def contagem_por_gravidade(self):
        contagem = {1: 0, 2: 0, 3: 0}
        for _, alerta in self._heap:
            contagem[alerta["gravidade"]] += 1
        return contagem

    def __len__(self):
        return len(self._heap)


## Média móvel com deque de tamanho máximo (janela deslizante).
## Ao inserir o 25º valor, o mais antigo sai sozinho, em O(1),
## e a soma é atualizada sem recalcular a janela inteira.
def media_movel(valores, janela=JANELA_MEDIA_MOVEL):
    janela_atual = deque(maxlen=janela)
    soma = 0.0
    medias = []
    for valor in valores:
        if len(janela_atual) == janela:
            soma -= janela_atual[0]          # valor que vai sair da janela
        janela_atual.append(valor)
        soma += valor
        medias.append(soma / len(janela_atual))
    return medias
