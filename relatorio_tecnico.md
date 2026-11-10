# Relatório Técnico — SIFSM, Fase 7

**Sistema Integrado de Futuro Sustentável em Marte — Aurora Siger**
**Tema da fase:** gestão energética sustentável da colônia (consumo, geração e autonomia das baterias)
**Curso:** Ciência da Computação — FIAP

---

## 1. Contexto da solução

Uma colônia em Marte depende quase totalmente de energia solar. O dia marciano é parecido com o terrestre, mas as noites são muito frias (cerca de −75 °C), o que aumenta o consumo com aquecimento. Além disso, tempestades de poeira podem bloquear a maior parte da luz por dias seguidos. Nessas condições, a pergunta operacional é: **"a bateria aguenta até o sol voltar? E, se não aguentar, o que desligar primeiro?"**

O SIFSM, nesta fase, é um protótipo em Python que:

1. guarda em banco de dados os módulos da colônia, o banco de baterias e as leituras horárias dos sensores;
2. aplica uma **regra booleana** que detecta risco energético e decide o **corte de carga** de módulos não essenciais;
3. organiza os alertas em uma **fila de prioridade**;
4. **simula** a bateria em vários cenários, inclusive tempestades sorteadas (Monte Carlo);
5. usa **regressão linear** para prever o consumo noturno e estimar a autonomia da bateria;
6. integra tudo no fluxo **"Analisar sustentabilidade da colônia"**, que termina numa recomendação técnica validada por critérios socioambientais.

## 2. Organização dos arquivos

A organização segue a mesma estrutura das fases anteriores: o arquivo principal na raiz só monta o menu e chama as funções. A lógica fica em `src/` (um arquivo por assunto) e os dados ficam em `data/`.

```
Aurora-Fase7/
├── codigo_fonte.py              ← ARQUIVO PRINCIPAL (menu; não calcula nada)
├── simulacao_computacional.py   ← simulação da bateria, SymPy, Monte Carlo
├── testes.py                    ← 19 testes automáticos (unittest)
├── circuito_logico.png
├── relatorio_tecnico.md · README.md · link_video.txt
├── data/
│   ├── script_banco.sql         ← criação das tabelas (SQLite)
│   ├── aurora_siger.db          ← banco já populado
│   └── dados_aurora_siger.csv   ← base simulada (1008 leituras)
├── src/
│   ├── config.py                ← caminhos e constantes
│   ├── terminal.py              ← leitura validada (tratamento de erros) e tabelas
│   ├── banco.py                 ← conexão SQLite e carregamento dos dados
│   ├── crud.py                  ← cadastrar, listar, alterar, excluir, leituras
│   ├── regra_booleana.py        ← regra, limiares, tabela-verdade, consumo esperado
│   ├── decisao.py               ← regra aplicada às leituras + circuito no terminal
│   ├── estruturas.py            ← fila de prioridade (heap) e média móvel (deque)
│   ├── alertas.py               ← geração, gravação e atendimento de alertas
│   ├── regressao.py             ← modelo linear e autonomia da bateria
│   ├── analise.py               ← "Analisar sustentabilidade" e análise final
│   ├── graficos.py              ← paleta e estilo dos gráficos
│   ├── gerar_base.py            ← cria o banco e a base simulada
│   ├── gerar_circuito.py        ← desenha o circuito_logico.png
│   └── gerar_prints_execucao.py ← gera os prints reais da execução
└── graficos_ou_imagens/         ← gráficos e prints_execucao/
```

A `simulacao_computacional.py` fica na raiz, e não em `src/`, porque o enunciado pede esse nome de arquivo na entrega quando a simulação é separada do código principal.

## 3. Descrição dos dados

Os dados são **simulados** pelo `src/gerar_base.py`, com semente fixa (`42`), então qualquer pessoa obtém exatamente a mesma base.

**Módulos (6):**

| ID | Nome | Tipo | Prioridade | Status | Consumo base (kWh/dia) |
|---|---|---|---|---|---|
| 1 | Habitat Alpha | habitação | 1 | ativo | 45 |
| 2 | MedBase | médico | 2 | ativo | 38 |
| 3 | Reator Solar | energia | 2 | ativo | 20 |
| 4 | BioLab | laboratório | 3 | ativo | 30 |
| 5 | LogiStore | armazenagem | 4 | ativo | 25 |
| 6 | TerraBot | mineração | 5 | manutenção | 55 |

**Bateria:** banco LiFePO4 de 500 kWh, carga inicial de 70%, mínimo operacional de 20% e eficiência de carga de 95%.

**Leituras:** 168 ciclos (7 dias × 24 h) × 6 módulos = **1008 leituras**, sem nulos e sem duplicatas.

| Coluna | Unidade | Como é gerada |
|---|---|---|
| `temperatura_c` | °C | −45 − 30·cos(2π(h−3)/24) + ruído. Mínima de cerca de −75 °C às 3 h e máxima de cerca de −15 °C às 15 h. **É a mesma para a colônia inteira em cada ciclo** |
| `luminosidade_lux` | lux | 40 000·sen(π(h−6)/12) entre 6 h e 18 h e **zero à noite** |
| `umidade_interna_pct` | % | Umidade interna controlada, perto de 40% |
| `consumo_kwh` | kWh | Base/24 + aquecimento (0,02 kWh por °C abaixo de −15 °C) + iluminação + penalidade de status + ruído |
| `geracao_kwh` | kWh | Só no Reator Solar: 55·sen(π(h−6)/12), com pico de 55 kWh ao meio-dia |
| `carga_bateria_pct` | % | Calculada hora a hora pela equação da bateria (seção 8) a partir do saldo da colônia |

**Eventos planejados na base**, para que as análises tenham o que detectar:

- **Tempestade de poeira nos dias 5 e 6:** a luz e a geração caem para 35%.
- **Duas anomalias de consumo:** BioLab no dia 3, das 13 h às 17 h (+2 kWh/h, falha de isolamento), e LogiStore no dia 6, das 2 h às 4 h (+1,5 kWh/h, falha de refrigeração).

**Calibração:** o pico solar e a capacidade da bateria foram escolhidos para que, em dias de céu limpo, a geração cubra de 106% a 109% do consumo e a bateria oscile entre 40% e 100%. Na tempestade, a cobertura cai para 36%, a bateria chega a 0% no dia 6 e se recupera no dia 7. Esse comportamento permite mostrar operação normal, crise e recuperação com os mesmos dados.

## 4. Banco de dados

Usamos **SQLite**: não precisa de servidor nem de instalação (já vem com o Python) e o arquivo `.db` vai junto na entrega. O `data/script_banco.sql` pode ser executado várias vezes, porque apaga e recria as tabelas.

```
modulos (1) ──< leituras (N)
   │  └──────< alertas (N)
   └─────────< manutencoes (N)
baterias (cadastro do banco de baterias)
```

**Integridade garantida pelo próprio banco:**

- `CHECK` em faixas físicas: consumo ≥ 0, carga e umidade entre 0 e 100, temperatura entre −150 e 50 °C, hora entre 0 e 23, prioridade entre 1 e 5, status em uma lista fechada, `resolvido` igual a 0 ou 1;
- `UNIQUE (id_modulo, ciclo)`: impede duas leituras do mesmo módulo na mesma hora;
- `UNIQUE` em `modulos.nome` e em `modulos.codigo_sensor`;
- `FOREIGN KEY ... ON DELETE CASCADE`: excluir um módulo apaga as leituras, os alertas e as manutenções dele, sem deixar registros órfãos. O sistema ativa `PRAGMA foreign_keys = ON` em toda conexão;
- índice em `leituras(ciclo)` para acelerar as consultas por hora.

Os testes automáticos confirmam que o banco rejeita consumo negativo, bateria acima de 100%, prioridade 9 e leitura duplicada, e que a exclusão em cascata funciona.

## 5. CRUD e tratamento de erros

| Operação | Opção do menu | Tabela |
|---|---|---|
| Cadastrar | 1 (módulo), 5 (leitura) | `modulos`, `leituras` |
| Listar / consultar | 2 (módulos), 6 (leituras por módulo, por dia ou por ciclo) | idem |
| Alterar | 3 (Enter mantém o valor atual) | `modulos` |
| Excluir | 4 (com confirmação e aviso da cascata) | `modulos` e dependentes |

**Tratamento de erros** em três camadas:

1. **Entrada:** `ler_numero`, `ler_texto`, `ler_sim_nao` e `ler_codigo_sensor` repetem a pergunta até receber um valor válido. Elas cobrem texto no lugar de número, valor fora da faixa, campo vazio e código hexadecimal mal formatado, e aceitam vírgula decimal.
2. **Banco:** `sqlite3.IntegrityError` é capturado e vira uma mensagem clara (nome duplicado, leitura repetida no mesmo ciclo). As gravações usam transação (`with con:`), então nada fica pela metade.
3. **Sistema:** cada opção do menu roda dentro de `try/except` (`FileNotFoundError`, `sqlite3.Error`, `ValueError`), então um erro não derruba o programa. Se o banco não existir, o sistema oferece gerá-lo. `Ctrl+C` e o fim da entrada encerram o programa com uma mensagem amigável.

Evidência: `graficos_ou_imagens/prints_execucao/04_tratamento_de_erros.png`.

## 6. Regra booleana e circuito lógico

**Variáveis (lidas dos sensores e do cadastro):**

| Variável | Significado | Critério |
|---|---|---|
| **A** | bateria baixa | carga < 30% |
| **G** | geração suficiente | geração solar do ciclo ≥ consumo total da colônia |
| **E** | consumo excessivo | consumo do módulo > 140% do esperado para aquela hora |
| **P** | módulo essencial | prioridade ≤ 2 (Habitat, MedBase, Reator) |

**Regra:**

```
RISCO = (A · ¬G) + E          → alarme
CORTE = RISCO · ¬P            → relé que coloca o módulo em modo de economia
```

**Interpretação:** existe risco quando a bateria está baixa e o sol não dá conta da demanda, ou quando um módulo está consumindo demais. Em caso de risco, **só os módulos não essenciais são cortados**. Os essenciais (suporte à vida e saúde) ficam ligados e apenas são sinalizados. O teste `test_corte_nunca_atinge_modulo_essencial` percorre as 16 linhas da tabela-verdade para garantir isso.

**Consumo esperado:** é a **mediana** das leituras do módulo naquela hora do dia. Usamos a mediana, e não a média, porque ela não é distorcida pelas próprias anomalias que queremos encontrar.

**Calibração do limiar de E:** com 125%, o critério detectava as 8 horas anômalas, mas gerava 57 falsos alarmes. Com **140%**, continua detectando 8 de 8 e cai para 17 falsos alarmes (1,7% das leituras). Com 150%, já deixava de detectar 3 anomalias.

**Circuito (`circuito_logico.png`):** usa 2 portas NOT, 2 AND e 1 OR. Num protótipo físico, por exemplo um Arduino:

- **A** viria de um medidor de carga da bateria;
- **G** de um comparador entre o medidor solar e o medidor de consumo;
- **E** de um sensor de corrente do módulo;
- **P** de uma chave de configuração;
- **RISCO** acionaria um LED ou alarme e **CORTE** um relé.

O menu (opção 8) mostra o circuito em texto e a tabela-verdade completa e regera a imagem.

## 7. Estruturas de dados

| Estrutura | Onde | Por quê |
|---|---|---|
| **Fila de prioridade (heap binário, `heapq`)** — classe `FilaAlertas` | Alertas (opções 9 e 12) | O operador precisa atender primeiro o alerta mais grave. A chave é `(gravidade, prioridade do módulo, −ciclo)`: crítico antes de alto, Habitat antes de TerraBot e, no empate, o mais recente primeiro. Inserir e remover custam **O(log n)** e ver o mais urgente custa O(1). Ordenar uma lista a cada novo alerta custaria O(n log n) |
| **Dicionário (tabela hash)** | `carregar_modulos` → `{id: módulo}` | Cada leitura precisa da prioridade e do nome do módulo. A busca por ID custa O(1), em vez de percorrer a lista |
| **Deque com `maxlen` (janela deslizante)** | `media_movel` | A média móvel das últimas 24 h. Quando entra o 25º valor, o mais antigo sai sozinho em O(1), e a soma é atualizada incrementalmente. A memória fica limitada a 24 valores |
| **Vetores e matrizes NumPy** | Simulação | `consumo[ciclo, módulo]` permite somas e operações vetorizadas, rápidas e com memória contígua |

## 8. Simulação computacional e conceitos matemáticos

### 8.1 Equação de diferenças da bateria

O estado de carga evolui hora a hora (Δt = 1 h):

```
saldo(t)  = geração(t) − consumo(t)
carga(t+1) = carga(t) + 0,95·saldo(t)    se saldo > 0   (carregando, com perdas)
carga(t+1) = carga(t) + saldo(t)         se saldo ≤ 0   (descarregando)
carga limitada ao intervalo [0, 500 kWh]
```

Isso é uma integração numérica (método de Euler) do balanço de energia. **Validação:** o modelo reproduz a carga gravada no banco com diferença máxima de **0,0000 pontos percentuais**.

### 8.2 Cenários determinísticos (7 dias)

| Cenário | Carga final | Horas < 20% | Energia não atendida (apagão) | Energia economizada |
|---|---|---|---|---|
| Registrado, sem corte | 33,6% | 34 | **276,5 kWh** | — |
| Registrado + corte de carga | 34,5% | 32 | **88,7 kWh** | 206,6 kWh |
| Tempestade severa (dias 5–7, 20% de luz), sem corte | 0% | 50 | 552,8 kWh | — |
| Tempestade severa + corte | 0% | 48 | 246,9 kWh | 320,0 kWh |

O corte de carga decidido pela regra booleana **reduz o apagão em 68%**. Uma busca de capacidade (de 50 em 50 kWh) mostra que a bateria precisaria de **650 kWh com corte de carga** (ou 900 kWh sem corte) para atravessar a semana registrada sem apagão. A capacidade atual é 500 kWh.

### 8.3 Integral da curva solar (SymPy)

A potência solar é modelada como P(t) = Pp·sen(π(t − 6)/12) entre 6 h e 18 h. Com SymPy:

```
E = ∫₆¹⁸ Pp·sen(π(t−6)/12) dt = 24·Pp/π
```

- Com o pico estimado nos dados (Pp = 55,01 kWh), a energia teórica é **420,2 kWh/dia**. A soma das leituras horárias (soma de Riemann) dá **418,1 kWh/dia**, uma diferença de 0,5%.
- Resolvendo `24·Pp/π = 394,4` (o consumo médio diário) com `sympy.solve`, chega-se ao **pico mínimo para autossuficiência: Pp ≥ 51,6 kWh**. O campo solar atual (55 kWh) tem folga de apenas cerca de 7%.

### 8.4 Monte Carlo (500 tempestades sorteadas)

Em cada execução são sorteados:

- o dia de início da tempestade (1 a 7);
- a duração (1 a 3 dias);
- a intensidade (20% a 60% da luz);
- a variação de demanda (95% a 110%).

| Estratégia | P(carga < 20%) | P(apagão) | Carga mínima média |
|---|---|---|---|
| Sem corte de carga | 92,8% | **81,8%** | 3,4% |
| Com corte de carga | 88,6% | **57,6%** | 6,6% |

**Interpretação:** com a bateria atual, quase qualquer tempestade leva a colônia abaixo do mínimo operacional. O corte de carga reduz a probabilidade de apagão em cerca de 24 pontos percentuais, mas não a elimina. O problema é estrutural: a capacidade de armazenamento é insuficiente.

Gráficos: `simulacao_cenarios_bateria.png`, `simulacao_monte_carlo.png` e `simulacao_curva_solar_integral.png`.

## 9. Modelo linear simples

- **Variável prevista:** consumo total da colônia por hora (kWh/h).
- **Variável explicativa:** temperatura externa (°C).
- **Por que essa variável:** ela tem a maior correlação com o consumo (r = −0,90) e pode ser prevista com antecedência.

Usamos `LinearRegression` do scikit-learn, com 70% dos ciclos para treino e 30% para teste (`random_state=42`).

```
consumo = 8,814 − 0,1650 · temperatura
```

| Métrica | Valor |
|---|---|
| R² treino / teste | 0,824 / **0,768** |
| MAE / RMSE (teste) | 1,56 / 1,82 kWh/h |

**Interpretação:**

- A cada 1 °C a menos, a colônia consome **0,165 kWh/h a mais** (aquecimento). Uma noite 10 °C mais fria custa 1,65 kWh a mais por hora.
- O R² de 0,77 indica que a temperatura sozinha explica cerca de 77% da variação do consumo. O restante vem principalmente da iluminação (luminosidade e tempestades) e do ruído.
- Os valores de R² no treino e no teste são próximos, então não há sinal de sobreajuste.

**Uso na decisão:**

- **Autonomia = energia acima do mínimo ÷ consumo previsto.**
- No estado final da base (bateria em 33,6%, noite a −60 °C), o consumo previsto é de 18,7 kWh/h. A energia útil é de 68 kWh, o que dá **3,6 h de autonomia**. O sol só volta a cobrir o consumo em cerca de 9 h, e por isso o sistema recomenda o corte de carga imediato.

## 10. Fluxo integrado: "Analisar sustentabilidade da colônia" (opção 12)

1. **Consulta ao banco:** situação atual, balanço das últimas 24 h e média móvel por módulo (deque).
2. **Regra booleana** aplicada a cada módulo no ciclo atual (A, G, E, P → RISCO, CORTE).
3. **Fila de prioridade** com os alertas das últimas 24 h (heapq).
4. **Simulação das próximas 24 h** a partir da carga atual, em 4 cenários: céu limpo ou tempestade, com ou sem corte.
5. **Regressão linear:** consumo noturno previsto e autonomia.
6. **Recomendação técnica:**
   - urgência (autonomia de 3,6 h contra 9 h até o sol), com os módulos a cortar;
   - plano de contingência para tempestade;
   - módulos com consumo anômalo;
   - ampliação da bateria para pelo menos 650 kWh no longo prazo.
7. **Validação socioambiental:** seis critérios marcados como [OK] ou [ATENÇÃO] (seção 13).

Evidência: `graficos_ou_imagens/prints_execucao/10_analisar_sustentabilidade.png`.

## 11. Proposta de integração de IA (agentes, ferramentas, fluxos e guardrails)

O protótipo atual é determinístico, o que é proposital: decisões que afetam o suporte à vida precisam ser explicáveis. A proposta é acrescentar uma camada de agentes **por cima** das funções já existentes, que passam a ser as **ferramentas** dos agentes.

| Agente | Responsabilidade | Ferramentas (funções já implementadas) |
|---|---|---|
| **Monitor** | Lê as leituras novas a cada ciclo e dispara a análise quando há risco | `carregar_leituras`, `avaliar_ciclo`, `gerar_alertas` |
| **Planejador** | Testa planos alternativos (quais módulos cortar, por quanto tempo) e escolhe o de menor impacto | `projetar_24h`, `simular_bateria`, `estimar_autonomia`, `capacidade_minima_sem_apagao` |
| **Comunicador** | Explica a recomendação ao operador em linguagem simples, citando as variáveis | `mensagem_alerta`, saída da validação socioambiental |

**Fluxo:** nova leitura → Monitor (regra booleana) → se houver RISCO, o Planejador simula alternativas → **guardrails** → o Comunicador apresenta o plano → **o operador humano aprova** → o sistema executa e registra no banco.

**Guardrails:**

1. **Restrição dura fora do modelo:** nenhum plano pode cortar um módulo com P = 1. Isso é verificado em código (`avaliar_regra`), não pela IA.
2. **Aprovação humana obrigatória** para qualquer corte, e fallback automático para a regra booleana se a IA estiver indisponível ou der uma resposta inválida.
3. **Ações limitadas a uma lista branca** de ferramentas, com limites de parâmetros (ex.: o corte nunca vai abaixo de 30% do consumo do módulo).
4. **Validação de dados** antes de qualquer decisão: as constraints do banco e as faixas físicas já existentes.
5. **Auditoria:** cada recomendação fica registrada com as variáveis de entrada (tabela `alertas`), para revisão posterior.
6. **Explicabilidade:** toda saída cita A, G, E, P e os números da simulação que a justificam.

Como a comunicação entre Terra e Marte tem atraso de 4 a 24 minutos, esses agentes precisariam rodar **localmente na colônia** (seção 12).

## 12. Arquitetura computacional, processamento, memória e aceleração

- **Processamento local (edge):** o atraso de 4 a 24 minutos de comunicação com a Terra exige que toda a decisão rode na colônia. O protótipo inteiro roda em um computador comum: a simulação completa (com 500 execuções de Monte Carlo) leva poucos segundos e os 19 testes, menos de 1 s.
- **Custo computacional:**
  - uma simulação é O(T·M), com T = 168 horas e M = 6 módulos;
  - o Monte Carlo é O(N·T·M): são 1000 simulações (500 sorteios × 2 estratégias) e cerca de 500 mil avaliações da regra (500 × 168 × 6, na estratégia com corte);
  - a fila de alertas é O(log n) por operação;
  - a busca de módulo é O(1).
- **Memória:**
  - a base inteira tem cerca de 1000 linhas por 15 colunas, menos de 1 MB em RAM (DataFrame do Pandas);
  - o SQLite fica em disco e usa um índice em `ciclo`;
  - o deque limita a média móvel a 24 valores;
  - as matrizes NumPy são contíguas, o que favorece a cache do processador.
- **Aceleração possível:**
  - o Monte Carlo é "embaraçosamente paralelo", porque cada execução é independente. Ele pode ser distribuído entre núcleos (`multiprocessing`) ou vetorizado sobre as execuções com NumPy, e em escala maior rodaria em GPU;
  - a regra booleana, por ser um circuito combinacional de 5 portas, pode ser implementada em hardware (FPGA ou microcontrolador). Isso dá resposta em microssegundos e funciona mesmo se o computador principal falhar.
- **Eficiência energética do próprio sistema:** em Marte, a computação também consome a energia que estamos tentando economizar. Por isso a arquitetura recomendada é:
  - microcontroladores de baixo consumo para a regra (sempre ligados);
  - o processador principal para a simulação e a regressão, acionado só sob demanda (a cada ciclo ou quando há alerta).

## 13. Sustentabilidade, cidadania digital e impacto socioambiental

- **Sustentabilidade energética:** a colônia é 100% solar. O sistema evita desperdício (prevê o déficit antes que ele aconteça) e mostra quantitativamente onde investir: a simulação aponta que ampliar a bateria de 500 para 650 kWh elimina o apagão da semana registrada.
- **Vida em primeiro lugar e equidade:** o corte segue um critério objetivo e público (a prioridade do módulo), e nunca atinge habitação, saúde ou geração. A decisão não depende de quem pede, e sim de uma regra conhecida por todos.
- **Transparência e explicabilidade:** cada alerta mostra os números e as variáveis que o geraram, e a tabela-verdade é pública. Qualquer colono consegue entender por que um módulo foi desligado.
- **Humano no controle:** o sistema **recomenda** e o operador decide. Isso evita a automação cega de decisões que afetam pessoas.
- **Cidadania digital:**
  - os sensores medem módulos, não pessoas, e as leituras de habitação são agregadas por módulo, o que preserva a privacidade dos moradores;
  - o banco tem validações para que dados errados não gerem decisões erradas;
  - limitação reconhecida: falta autenticação e um registro de quem alterou o quê (seção 14).
- **Acessibilidade:** as mensagens estão em português claro, os gráficos usam uma paleta segura para daltônicos e os limiares aparecem com rótulo, não só com cor.
- **Paralelo com a Terra:** o mesmo raciocínio vale para microrredes solares em comunidades isoladas (comunidades ribeirinhas da Amazônia, ilhas, áreas rurais sem rede elétrica). Lá também é preciso priorizar postos de saúde e escolas quando a energia é escassa, de forma justa e transparente.

## 14. Limitações

1. Os dados são simulados (7 dias). O uso real exigiria calibrar os parâmetros com sensores.
2. A regressão usa só a temperatura. A luminosidade (tempestades) também afeta o consumo, e o R² de 0,77 reflete isso.
3. A bateria tem eficiência constante, sem degradação, autodescarga ou perda de capacidade no frio.
4. O consumo esperado vem dos próprios dados. Um módulo recém-cadastrado não tem perfil (usamos o consumo base como alternativa na projeção, e E = falso na regra).
5. Os limiares são fixos (30% e 140%). O critério E ainda gera 17 falsos alarmes em 1008 leituras.
6. O corte de carga é instantâneo e fixo em 30% do consumo. Na prática existem tempos de religamento e cargas que não podem ser reduzidas.
7. O alerta de risco energético é gerado por módulo, o que repete a mesma causa em vários módulos no mesmo ciclo.
8. O SQLite é local e de usuário único, sem autenticação nem trilha de auditoria de alterações. A tabela `manutencoes` existe no banco, mas ainda não tem CRUD no menu.

## 15. Possíveis melhorias

- Regressão múltipla (temperatura, luminosidade e hora) ou modelos não lineares.
- Agentes de IA com os guardrails descritos na seção 11.
- Sensores reais (Arduino ou ESP32) enviando leituras ao banco e o circuito de corte implementado em hardware.
- Previsão de tempestades para antecipar o corte de carga, em vez de reagir quando a bateria já está baixa.
- Limiares adaptativos aprendidos com o histórico. Corte de carga gradual (vários níveis de economia).
- CRUD de manutenções, autenticação de operadores e registro de auditoria.
- Painel gráfico (dashboard) em tempo real.

## 16. Como executar e verificar

```
pip install numpy pandas matplotlib scikit-learn sympy
python codigo_fonte.py            # sistema completo (menu)
python simulacao_computacional.py # simulação isolada
python testes.py                  # 19 testes automáticos
python -m src.gerar_base          # recria a base simulada do zero
python -m src.gerar_prints_execucao  # regera os prints de execução
```

Prints da execução real: `graficos_ou_imagens/prints_execucao/` (01 a 12).
