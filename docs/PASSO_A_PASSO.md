# Passo a passo do projeto SIFSM, Fase 7

Este guia explica **o que foi feito, por que foi feito e como funciona**, na ordem em que o projeto foi construído. A ideia é que, depois de ler, você consiga explicar qualquer parte do projeto, inclusive responder às perguntas do professor.

---

## 0. A ideia em uma frase

> A colônia vive de energia solar. À noite e nas tempestades de poeira, ela depende da bateria. O SIFSM responde: **"a bateria aguenta até o sol voltar? Se não aguentar, o que desligar primeiro, sem colocar vidas em risco?"**

Todo o resto do projeto existe para responder essa pergunta:

| Pergunta | Ferramenta usada |
|---|---|
| Onde estão os dados? | Banco SQLite e CSV |
| Tem risco agora? | Regra booleana |
| Qual alerta atender primeiro? | Fila de prioridade (heap) |
| O que acontece se...? | Simulação e Monte Carlo |
| Quanto vamos consumir esta noite? | Regressão linear |
| O que fazer? | Recomendação com critérios socioambientais |

### Mapa dos arquivos

É a mesma estrutura das fases 5 e 6:

- o `codigo_fonte.py` na raiz **não calcula nada**: ele mostra o menu (`if/elif`) e chama as funções;
- a lógica fica em `src/`, um arquivo por assunto;
- os dados ficam em `data/`.

```
codigo_fonte.py (MENU) ──chama──> src/crud.py, src/decisao.py, src/alertas.py,
                                  src/regressao.py, src/analise.py
                                  e simulacao_computacional.py (raiz)

src/gerar_base.py ──(executa)──> data/script_banco.sql ──> data/aurora_siger.db
                                                       └──> data/dados_aurora_siger.csv

src/regra_booleana.py <── usada por decisao, alertas, simulação e circuito
src/estruturas.py     <── heap (FilaAlertas) e deque (media_movel)
src/terminal.py       <── todas as leituras do teclado (tratamento de erros)
src/banco.py          <── todas as conexões com o SQLite
src/config.py         <── todos os caminhos de arquivo
```

| Arquivo em `src/` | O que tem |
|---|---|
| `config.py` | Caminhos (`data/`, `graficos_ou_imagens/`) e constantes |
| `terminal.py` | `ler_numero`, `ler_texto`, `ler_sim_nao`... (tratamento de erros) e `imprimir_tabela` |
| `banco.py` | `abrir_banco`, `carregar_modulos` (dicionário), `carregar_leituras`, opção 14 |
| `crud.py` | Opções 1 a 6 |
| `regra_booleana.py` | A regra em si: fórmula, limiares, tabela-verdade |
| `decisao.py` | A regra aplicada às leituras do banco (opção 7) e o circuito (opção 8) |
| `estruturas.py` | `FilaAlertas` (heap) e `media_movel` (deque) |
| `alertas.py` | Geração, gravação e atendimento dos alertas (opção 9) |
| `regressao.py` | Modelo linear e autonomia (opção 11) |
| `analise.py` | "Analisar sustentabilidade" (opção 12) e análise final (opção 13) |
| `graficos.py` | Cores e estilo comuns dos gráficos |
| `gerar_base.py`, `gerar_circuito.py`, `gerar_prints_execucao.py` | Scripts que geram a base, o circuito e os prints |

A `simulacao_computacional.py` fica na raiz, e não em `src/`, porque o enunciado exige esse nome de arquivo na entrega.

### Como rodar

Todos os comandos são executados **a partir da pasta raiz do projeto**:

```
pip install numpy pandas matplotlib scikit-learn sympy
python codigo_fonte.py               # o sistema (menu)
python testes.py                     # 19 testes automáticos: todos devem dar "ok"
python simulacao_computacional.py    # só a simulação
python -m src.gerar_base             # recria a base do zero
python -m src.gerar_prints_execucao  # regera os prints de execução
```

Os scripts de `src/` rodam com `python -m src.nome` (sem o `.py`). Assim o Python enxerga a pasta raiz e os imports `from src...` funcionam.

Se o `data/aurora_siger.db` for apagado, o próprio sistema oferece recriá-lo. A opção 14 do menu também recria a base.

---

## 1. Diagnóstico da base original (o que mudou e por quê)

A sua base original tinha uma estrutura boa (módulos, leituras, alertas e manutenções), mas havia problemas que impediriam o projeto de cumprir o tema:

| Problema encontrado | Correção feita |
|---|---|
| **Não havia nenhum dado de bateria**, e o tema é "autonomia das baterias" | Criei a tabela `baterias` e a coluna `carga_bateria_pct` nas leituras |
| A geração cobria só 24% do consumo, então a bateria ficaria sempre zerada e tudo daria "crítico" | Recalibrei a geração (pico de 55 kWh) e a bateria (500 kWh). Dias normais ficam saudáveis e uma **tempestade nos dias 5 e 6** cria a crise |
| O consumo base de cada módulo era usado na geração dos dados, mas não era salvo | Coluna `consumo_base_kwh_dia` |
| Cada módulo tinha uma temperatura diferente na mesma hora | O ambiente agora é sorteado **uma vez por hora para a colônia toda** |
| Havia luz à noite (ruído) | Luminosidade zerada à noite |
| A umidade não fazia sentido para o ambiente externo de Marte | Renomeada para `umidade_interna_pct` (ar controlado do módulo) |
| Só existia o `ciclo`, sem dia e hora | Colunas `dia` e `hora` (ciclo 1 = dia 1, 0 h) |
| Faltavam regras de integridade | `NOT NULL`, `CHECK`, `UNIQUE` e `ON DELETE CASCADE` |
| O gerador quebrava se o banco não existisse | O gerador executa o `.sql` antes de inserir os dados |
| Faltava o arquivo de dados exigido na entrega | O gerador exporta o `dados_aurora_siger.csv` |

Também **injetei duas anomalias de consumo de propósito** (BioLab no dia 3 e LogiStore no dia 6). Elas servem para provar que a regra booleana detecta consumo anormal.

---

## 2. Banco de dados (`data/script_banco.sql`, `src/gerar_base.py`, `src/banco.py`)

### Conceitos

- **Chave primária (PK):** identifica cada linha (`id_modulo`).
- **Chave estrangeira (FK):** liga a leitura ao módulo. Não dá para cadastrar uma leitura de um módulo que não existe.
- **`ON DELETE CASCADE`:** se o módulo for excluído, as leituras dele também são. Assim não sobram dados "órfãos".
- **`CHECK`:** o banco recusa valores fisicamente impossíveis, como consumo negativo ou bateria acima de 100%.
- **`UNIQUE (id_modulo, ciclo)`:** impede duas leituras do mesmo módulo na mesma hora.
- **Transação (`with con:`):** ou grava tudo, ou não grava nada.
- **Semente aleatória (`random.seed(42)`):** os números "aleatórios" saem sempre iguais. Isso torna a base **reproduzível**: o professor gera exatamente os mesmos dados.

### Como o gerador funciona

Para cada hora (ciclo), o gerador:

1. sorteia o ambiente da hora (temperatura com cosseno, luz com seno);
2. calcula o consumo de cada módulo: base + aquecimento (quanto mais frio, mais consumo) + iluminação + status + anomalia + ruído;
3. calcula a geração solar (só no Reator Solar);
4. aplica o **saldo da colônia** (geração − consumo) na bateria.

**Por que SQLite?** Não precisa de servidor nem de instalação (vem com o Python) e o arquivo vai junto no `.zip`. O avaliador roda o projeto sem configurar nada.

---

## 3. CRUD (opções 1 a 6 do menu)

CRUD = **C**reate, **R**ead, **U**pdate, **D**elete (cadastrar, consultar, alterar e excluir).

| Opção | O que faz | Função no código |
|---|---|---|
| 1 | Cadastra um módulo | `cadastrar_modulo` |
| 2 | Lista os módulos com o total de leituras e a média de consumo | `listar_modulos` |
| 3 | Altera um módulo. **Enter mantém o valor atual** | `alterar_modulo` |
| 4 | Exclui um módulo (pede confirmação e avisa da cascata) | `excluir_modulo` |
| 5 | Registra uma leitura de sensores | `registrar_leitura` |
| 6 | Consulta leituras por módulo, por dia ou por ciclo | `consultar_leituras` |

Todos usam **SQL com `?`** (consultas parametrizadas). Isso evita SQL injection, porque o valor digitado nunca é colado direto no comando SQL.

---

## 4. Tratamento de erros

São três camadas, do usuário até o sistema:

1. **Na digitação** (`ler_numero`, `ler_texto`, `ler_sim_nao`, `ler_codigo_sensor`): a função repete a pergunta até o valor ser válido. Ela trata texto no lugar de número (`try/except ValueError`), valor fora da faixa, campo obrigatório vazio e código de sensor fora do formato `0x0000`.
2. **No banco:** se o banco recusar (nome repetido, leitura duplicada), o `sqlite3.IntegrityError` é capturado e vira uma mensagem amigável.
3. **No menu:** cada opção roda dentro de um `try/except`, então nenhum erro derruba o programa. `Ctrl+C` encerra com uma mensagem educada. Se o banco não existir, o sistema oferece criá-lo.

**Para demonstrar:** no menu, digite `abc`, depois `99`, e tente cadastrar o módulo "Habitat Alpha" de novo. Veja o print `04_tratamento_de_erros.png`.

---

## 5. Regra booleana e circuito lógico (`src/regra_booleana.py`, `src/decisao.py`, opções 7 e 8)

### As 4 variáveis (cada uma é Verdadeiro ou Falso)

| Variável | Pergunta | Fica verdadeira quando |
|---|---|---|
| **A** | A bateria está baixa? | carga < 30% |
| **G** | O sol está dando conta? | geração ≥ consumo total da colônia |
| **E** | Este módulo está consumindo demais? | consumo > 140% do normal para aquela hora |
| **P** | Este módulo é essencial? | prioridade 1 ou 2 |

### A regra

```
RISCO = (A AND NOT G) OR E
CORTE = RISCO AND NOT P
```

**Em português:** há risco se a bateria está baixa **e** o sol não dá conta, **ou** se o módulo está gastando demais. Se há risco **e** o módulo **não** é essencial, ele é colocado em economia (corte de carga). Módulos essenciais nunca são cortados.

### Exemplo real: ciclo 141 (dia 6, 20 h, no meio da tempestade)

A bateria está em 0% (A = 1) e não há sol (G = 0), então `A AND NOT G = 1` e RISCO = 1 para todos os módulos:

- Habitat, MedBase e Reator têm P = 1, então `CORTE = 1 AND NOT 1 = 0`: **ficam ligados**;
- BioLab, LogiStore e TerraBot têm P = 0, então CORTE = 1: **vão para economia**.

Para ver isso no sistema: opção 7 → 1 → ciclo 141.

### Por que 140% e não 120%?

Eu testei com os dados:

| Limiar | Anomalias detectadas | Falsos alarmes |
|---|---|---|
| 125% | 8 de 8 | 57 |
| **140%** | **8 de 8** | **17** |
| 150% | 5 de 8 | 6 |

O limiar de 140% é o ponto que pega todas as anomalias com o menor número de alarmes falsos.

### O "normal para aquela hora"

É a **mediana** do consumo do módulo naquela hora ao longo dos 7 dias. A mediana não é puxada pelos valores extremos (as próprias anomalias). A média seria.

### O circuito

- **¬G** sai de uma porta NOT;
- **A·¬G** sai de uma porta AND;
- **(A·¬G) + E** sai de uma porta OR, e o resultado é o **RISCO**;
- **¬P** sai de outra porta NOT;
- **RISCO·¬P** sai de outra porta AND, e o resultado é o **CORTE**.

No total são 5 portas. Num Arduino, A, G e E viriam de sensores, P de uma chave, RISCO acenderia um LED e CORTE acionaria um relé. A imagem `circuito_logico.png` mostra o circuito e a tabela-verdade. **A tabela da imagem é calculada pelo próprio código da regra**, então desenho e programa sempre coincidem.

**Tabela-verdade:** com 4 variáveis existem 2⁴ = 16 combinações, e a tabela mostra a saída de todas.

---

## 6. Estruturas de dados

### Fila de prioridade (heap), classe `FilaAlertas` (opção 9)

**Problema:** a semana tem 188 alertas. Qual atender primeiro?

**Solução:** um **heap binário**, uma árvore guardada numa lista em que o menor elemento fica sempre na posição 0. A "chave" de cada alerta é:

```
(gravidade, prioridade_do_módulo, -ciclo)
```

- **Gravidade** 1 (crítico) vem antes de 2 (alto), que vem antes de 3 (moderado).
- No empate, o módulo mais essencial vem primeiro (Habitat = 1 antes de TerraBot = 5).
- No empate, a hora mais recente vem primeiro. O sinal de menos inverte a ordem do ciclo.

**Por que heap e não lista ordenada?**

- No heap, inserir e retirar custam **O(log n)**: para 188 alertas, cerca de 8 passos;
- numa lista, seria preciso reordenar tudo a cada alerta novo, a O(n log n).

**Gravidade:**

- crítico = bateria baixa sem sol **e** consumo anormal ao mesmo tempo;
- alto = só o risco de energia;
- moderado = só o consumo anormal.

### Dicionário: `carregar_modulos` → `{id: módulo}`

O dicionário é uma tabela hash: encontrar o módulo 4 é instantâneo (O(1)), sem percorrer a lista.

### Deque com `maxlen=24`: `media_movel`

É uma "janela deslizante" das últimas 24 h. Quando entra a 25ª leitura, a mais antiga sai sozinha. Aparece na consulta por módulo (coluna "Média 24h") e na análise de sustentabilidade.

---

## 7. Simulação computacional (`simulacao_computacional.py`, opção 10)

### 7.1 Equação de diferenças, o coração da simulação

A cada hora:

```
saldo = geração − consumo
se saldo > 0:  carga_nova = carga + 0,95 × saldo      (carregando; 5% se perde)
se saldo ≤ 0:  carga_nova = carga + saldo             (descarregando)
carga_nova fica entre 0 e 500 kWh
```

É o mesmo que "integrar" o balanço de energia em passos de 1 hora (método de Euler).

**Prova de que funciona:** a simulação reproduz a bateria gravada no banco com erro de 0,0000.

### 7.2 Os 4 cenários

| Cenário | Apagão na semana |
|---|---|
| Como aconteceu (sem corte) | 276,5 kWh |
| Com a regra booleana cortando cargas | 88,7 kWh (**−68%**) |
| Tempestade severa (3 dias, 20% de luz), sem corte | 552,8 kWh |
| Tempestade severa com corte | 246,9 kWh |

**Dimensionamento:** a simulação testa capacidades de 50 em 50 kWh e mostra que seriam necessários **650 kWh (com corte)** para não haver apagão. Hoje são 500 kWh.

### 7.3 Integral com SymPy (a matemática)

A geração solar segue uma meia senoide: P(t) = Pp · sen(π(t − 6)/12), das 6 h às 18 h. A energia do dia é a **área sob a curva**, ou seja, a integral:

```
∫ de 6 a 18 de Pp·sen(π(t−6)/12) dt = 24·Pp/π
```

O SymPy calcula isso **simbolicamente**, como você faria à mão:

- Com Pp = 55 kWh, a fórmula dá **420,2 kWh/dia**. Somando as leituras hora a hora, dá **418,1** (diferença de 0,5%). Isso confirma que a soma das leituras é uma boa aproximação da integral (soma de Riemann).
- Resolvendo a equação `24·Pp/π = consumo diário`, descobrimos que o pico mínimo para a colônia ser autossuficiente é **51,6 kWh**. Hoje é 55, uma folga pequena.

### 7.4 Monte Carlo

"Monte Carlo" é repetir a simulação muitas vezes com valores sorteados para estimar **probabilidades**. Fizemos 500 tempestades com início, duração e intensidade aleatórios:

| | Probabilidade de apagão |
|---|---|
| Sem corte de carga | 81,8% |
| Com corte de carga | 57,6% |

**Conclusão:** a regra ajuda muito, mas a bateria é pequena demais para a colônia ficar segura. Essa é a recomendação de longo prazo.

---

## 8. Modelo linear simples (opção 11)

**O que prevê:** o consumo total da colônia por hora, a partir da **temperatura**.

**Por que temperatura:** a correlação entre as duas é de −0,90 (forte e negativa: mais frio, mais consumo, por causa do aquecimento). Além disso, a temperatura da noite pode ser prevista com antecedência.

**Como funciona:** o `LinearRegression` encontra a reta que minimiza a soma dos erros ao quadrado (mínimos quadrados):

```
consumo = 8,814 − 0,165 × temperatura
```

**Como ler:**

- **−0,165:** a cada 1 °C a menos, a colônia gasta 0,165 kWh a mais por hora;
- **8,814:** o consumo teórico a 0 °C.

**Como validamos:**

- separamos 70% dos dados para treinar e 30% para testar, e o teste usa dados que o modelo nunca viu;
- **R² = 0,77:** a temperatura explica 77% da variação do consumo. O resto vem da iluminação (tempestades) e do ruído;
- **MAE = 1,56 kWh/h:** em média, o modelo erra 1,56 kWh por hora;
- o R² de treino (0,82) é parecido com o de teste (0,77), então o modelo não "decorou" os dados.

**Para que serve (apoio à decisão):**

```
autonomia = energia acima do mínimo ÷ consumo previsto
```

No fim da semana, a bateria tem 68 kWh úteis e o consumo previsto à noite é de 18,7 kWh/h. Isso dá **3,6 horas**, mas faltam cerca de 9 h para o sol voltar, então é preciso cortar cargas agora.

---

## 9. "Analisar sustentabilidade da colônia" (opção 12), o fluxo completo

É exatamente o exemplo do enunciado, em 7 passos:

1. **Consulta** ao banco: situação atual e médias móveis (deque).
2. **Regra booleana** em cada módulo na hora atual.
3. **Fila de prioridade** com os alertas das últimas 24 h.
4. **Simulação** das próximas 24 h, em 4 cenários.
5. **Regressão:** consumo da noite e autonomia.
6. **Recomendação técnica:** cortar BioLab, LogiStore e TerraBot agora; plano para tempestade; inspecionar consumo anômalo; ampliar a bateria para 650 kWh.
7. **Validação socioambiental:** seis critérios com [OK] ou [ATENÇÃO], como "vida em primeiro lugar" e "humano no controle".

Repare que o critério de **resiliência** aparece como [ATENÇÃO]. O sistema é honesto e mostra que a bateria atual não é suficiente.

## 10. Análise final (opção 13)

Mostra o balanço de cada dia, os totais da regra, da regressão e da simulação, a conclusão, as **limitações** e as **melhorias futuras**.

---

## 11. Decisões que mudaram em relação ao plano inicial

Durante a implementação, algumas escolhas foram ajustadas com base nos testes:

- **G** passou de "há sol (> 0)" para **"a geração cobre o consumo"**. Com a primeira definição, durante a tempestade o fraco sol da tarde desativava o alerta, mesmo com a bateria esvaziando.
- **E** ficou em **140%** em vez de 120% (veja a tabela da seção 5).
- A coluna `data` (texto) de `manutencoes` virou **`dia`** (número), para combinar com o resto da base. Não existe calendário marciano no projeto.
- O código foi organizado como nas fases 5 e 6: `codigo_fonte.py` só com o menu, a lógica em `src/` e os dados em `data/`. A regra fica em um único lugar (`src/regra_booleana.py`) e é reaproveitada pelo menu, pela simulação e pelo desenho do circuito.
- Foi acrescentado o **dimensionamento da bateria** (capacidade mínima), porque o resultado da simulação mostrou que o corte de carga sozinho não resolve. Isso virou uma recomendação concreta.

---

## 12. Perguntas que o professor pode fazer

- **"Por que o corte não elimina o apagão?"** Porque só a carga essencial (Habitat, MedBase e Reator, cerca de 8 kWh/h) já passa do que o sol gera na tempestade. O problema é de capacidade de armazenamento, e a simulação mostra o tamanho certo: 650 kWh.
- **"Por que regressão simples e não múltipla?"** O enunciado pede modelo linear simples. A temperatura é a variável mais correlacionada (r = −0,90). A regressão múltipla está nas melhorias.
- **"O que é R²?"** É a fração da variação do consumo explicada pelo modelo, de 0 a 1. O nosso é 0,77.
- **"Por que heap?"** Para retirar sempre o alerta mais urgente em O(log n), sem reordenar a lista inteira.
- **"Os dados são reais?"** Não, são simulados com modelos físicos simples e semente fixa. Isso está declarado nas limitações.
- **"Onde entra a IA?"** Como proposta (seção 11 do relatório): agentes Monitor, Planejador e Comunicador, usando as funções do sistema como ferramentas, com guardrails. O principal guardrail é que nenhum módulo essencial pode ser cortado, e isso é verificado em código, fora da IA, com aprovação humana obrigatória.

---

## 13. Roteiro do vídeo (máximo de 5 minutos)

**Antes de gravar:**

- rode `python -m src.gerar_base`, para começar com a base limpa;
- aumente a fonte do terminal;
- deixe abertos `circuito_logico.png`, os gráficos de `graficos_ou_imagens/` e o `relatorio_tecnico.md`.

**Dica:** a opção 10 (simulação) leva alguns segundos. Se preferir, mostre a saída já pronta em `prints_execucao/08_...png`.

| # | Tópico do enunciado | O que mostrar na tela | O que falar (resumo) | Tempo |
|---|---|---|---|---|
| 1 | Descrição do sistema | Menu principal (`python codigo_fonte.py`) | "O SIFSM gerencia a energia da colônia: consumo, geração solar e bateria. A pergunta é se a bateria aguenta até o sol voltar." | 0:00–0:20 |
| 2 | Dados e conexão com o banco | `data/script_banco.sql` (tabelas e constraints) + opção 6 → 2 → dia 6 | "SQLite com 5 tabelas, 1008 leituras de 7 dias, e uma tempestade nos dias 5 e 6. O CHECK impede valores impossíveis." | 0:20–0:45 |
| 3 | CRUD | Opção 1 (cadastrar "Estufa Verde"), 2 (listar), 3 (alterar a prioridade), 4 (excluir) | "Cadastro, listagem, alteração com Enter para manter o valor e exclusão em cascata." | 0:45–1:15 |
| 4 | Tratamento de erros | Digitar `abc` no menu e cadastrar "Habitat Alpha" de novo | "Entradas inválidas são repetidas; duplicidade é barrada pelo banco e tratada." | 1:15–1:30 |
| 5 | Regra booleana | Opção 7 → 1 → ciclo 141 | "RISCO = A·¬G + E e CORTE = RISCO·¬P. Na tempestade, os não essenciais vão para economia e os essenciais ficam ligados." | 1:30–1:55 |
| 6 | Circuito lógico | `circuito_logico.png` | "2 NOT, 2 AND e 1 OR. Num Arduino, sensores nas entradas, LED e relé nas saídas. A tabela-verdade tem 16 linhas." | 1:55–2:10 |
| 7 | Estruturas de dados | Opção 9 (fila) e atender 1 alerta | "Heap: o mais grave e mais essencial sai primeiro, em O(log n). Também uso dicionário e deque para a média de 24 h." | 2:10–2:30 |
| 8 | Simulação e matemática | `simulacao_cenarios_bateria.png`, `simulacao_curva_solar_integral.png` e o print 08 | "Equação de diferenças da bateria; o corte reduz o apagão em 68%. A integral com SymPy dá 24·Pp/π = 420 kWh/dia. No Monte Carlo, o apagão cai de 82% para 58%." | 2:30–3:05 |
| 9 | Modelo linear | Opção 11 + `regressao_consumo_temperatura.png` | "Consumo = 8,81 − 0,165·T, R² = 0,77. Cada grau mais frio custa 0,165 kWh/h. Com isso, a autonomia é de 3,4 h." | 3:05–3:30 |
| 10 | Proposta de IA | Seção 11 do relatório | "Agentes Monitor, Planejador e Comunicador, usando as funções do sistema como ferramentas. Guardrails: nunca cortar essenciais, aprovação humana e auditoria." | 3:30–3:50 |
| 11 | Arquitetura computacional | Seção 12 do relatório | "Processamento local por causa do atraso Terra–Marte. O Monte Carlo é paralelizável. A regra pode ir para hardware. A computação também precisa economizar energia." | 3:50–4:05 |
| 12 | Sustentabilidade e cidadania digital | Seção 13 do relatório | "Vida em primeiro lugar, critério transparente e igual para todos, humano no controle, privacidade e acessibilidade. O paralelo são as microrredes isoladas na Terra." | 4:05–4:25 |
| 13 | Demonstração prática | **Opção 12: Analisar sustentabilidade** (rolar devagar) | "Fluxo completo: consulta, regra, fila, simulação, regressão e recomendação: cortar 3 módulos agora e ampliar a bateria para 650 kWh. A validação socioambiental aponta a falta de resiliência." | 4:25–5:00 |

---

## 14. Checklist da entrega (.zip)

- [ ] `codigo_fonte.py` (arquivo principal), `simulacao_computacional.py`, `testes.py` e a pasta `src/`
- [ ] Pasta `data/` com `script_banco.sql`, `aurora_siger.db` e `dados_aurora_siger.csv`
- [ ] `circuito_logico.png`
- [ ] `simulacao_computacional.py`
- [ ] `relatorio_tecnico.md`
- [ ] `README.md` (**você vai escrever**: objetivo, a árvore de arquivos (pode copiar a da seção 2 do relatório), dependências `numpy pandas matplotlib scikit-learn sympy`, `pip install ...` e `python codigo_fonte.py`; avise que os arquivos do enunciado `script_banco.sql` e `dados_aurora_siger.csv` estão em `data/`)
- [ ] `link_video.txt` com o link do YouTube ("Não listado")
- [ ] pasta `graficos_ou_imagens/`
- [ ] (opcional) pasta `docs/`
- [ ] Antes de compactar: rodar `python testes.py` e confirmar "OK".
- [ ] Rodar `python -m src.gerar_prints_execucao` para atualizar todos os prints (ele recria a base no início).
