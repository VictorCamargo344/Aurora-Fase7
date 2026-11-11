# Relatório Técnico — SIFSM
## Sistema Integrado de Futuro Sustentável em Marte
**Projeto:** Aurora Siger — Gestão Energética Sustentável da Colônia  
**Instituição:** FIAP  
**Fase:** Projeto Integrador — SIFSM  
**Equipe:** [preencher com os nomes dos integrantes]  
**Ano:** 2026

---

## 1. Resumo do projeto

O Sistema Integrado de Futuro Sustentável em Marte (SIFSM) é um protótipo computacional voltado ao apoio da gestão energética da colônia fictícia Aurora Siger. A solução reúne armazenamento e consulta de dados operacionais, regras booleanas para identificação de risco, organização de alertas, simulação do comportamento de baterias e um modelo linear para apoiar análises de consumo.

O projeto utiliza Python e SQLite, com dados simulados de módulos, baterias e leituras. Seu objetivo é demonstrar como diferentes componentes de software podem trabalhar em conjunto para apoiar decisões relacionadas à autonomia, à eficiência energética e à continuidade de serviços essenciais da colônia.

O protótipo é uma simulação acadêmica: não está conectado a sensores físicos nem controla equipamentos reais. As decisões apresentadas devem ser interpretadas como apoio à análise e não como substitutas da validação humana.

## 2. Contexto, problema e objetivos

Uma colônia em Marte teria recursos limitados e dependeria de sistemas confiáveis para administrar geração, armazenamento e consumo de energia. Uma falha no planejamento energético poderia comprometer módulos importantes, como habitação, suporte médico, agricultura, laboratório e comunicação.

O SIFSM aborda esse cenário por meio dos seguintes objetivos:

- organizar dados dos módulos, baterias e leituras;
- permitir operações de cadastro, consulta, alteração e exclusão;
- aplicar uma regra booleana para sinalizar risco energético e possível corte de cargas não essenciais;
- organizar alertas em uma fila;
- simular a evolução da carga das baterias em diferentes cenários;
- utilizar um modelo linear como apoio à estimativa de consumo;
- apresentar uma proposta conceitual de integração de agentes de IA;
- relacionar as escolhas técnicas à eficiência computacional e à sustentabilidade.

## 3. Organização dos dados, banco de dados e CRUD

### 3.1 Banco utilizado

O protótipo utiliza SQLite, por meio da biblioteca `sqlite3` do Python. O banco é relacional e é estruturado pelo script `script_banco.sql`. O arquivo de banco é gerado ou utilizado pelo próprio sistema.

As tabelas centrais são:

| Tabela | Finalidade |
|---|---|
| `modulos` | Armazenar os módulos da colônia, seus tipos, prioridades, status e consumo-base |
| `baterias` | Registrar capacidade, carga inicial, carga mínima e eficiência do armazenamento |
| `leituras` | Guardar leituras simuladas por módulo e ciclo, como consumo, geração e variáveis ambientais |
| `alertas` | Registrar alertas operacionais |
| `manutencoes` | Manter informações de manutenção |

O esquema SQL utiliza chaves primárias e estrangeiras e restrições (`CHECK`, `NOT NULL` e `UNIQUE`) para reduzir registros inconsistentes. As leituras se relacionam aos módulos por meio de identificadores, permitindo consultar o histórico operacional.

### 3.2 Operações CRUD

O menu do sistema oferece operações para:

- **Create — cadastrar:** inserir módulos e registrar leituras;
- **Read — consultar:** listar módulos e consultar leituras;
- **Update — alterar:** atualizar dados de módulos;
- **Delete — excluir:** remover registros de módulos.

Essas operações permitem que os dados utilizados nas análises sejam mantidos e consultados pelo próprio protótipo. O sistema também disponibiliza a opção de recriar a base simulada.

### 3.3 Tratamento de erros

O código principal utiliza tratamento de exceções para impedir que erros comuns encerrem inesperadamente o fluxo do menu. Entre os casos tratados estão entradas inválidas, arquivos não encontrados e erros relacionados ao SQLite. O usuário recebe mensagens que indicam o tipo de problema.

O tratamento de erros é importante porque operações de banco de dados e entradas fornecidas pelo usuário podem falhar. Em uma versão futura, os registros de erro poderiam ser armazenados em um log para facilitar auditoria e manutenção.

## 4. Circuitos lógicos e regra booleana

O SIFSM utiliza uma regra lógica para identificar risco energético e determinar se uma carga não essencial pode ser sinalizada para corte. A regra é representada no circuito lógico fornecido e pode ser simulada em software.

### 4.1 Entradas

| Variável | Significado | Valor lógico 1 |
|---|---|---|
| `A` | Estado de carga da bateria | Carga abaixo de 30% |
| `G` | Relação entre geração solar e consumo | Geração igual ou superior ao consumo |
| `E` | Consumo do módulo | Consumo acima de 140% do esperado |
| `P` | Prioridade do módulo | Módulo essencial, com prioridade 1 ou 2 |

### 4.2 Expressões

A expressão de risco é:

\[
RISCO = (A \land \neg G) \lor E
\]

A expressão de corte é:

\[
CORTE = RISCO \land \neg P
\]

A primeira expressão sinaliza risco quando a bateria está abaixo do limite e a geração solar não cobre o consumo, ou quando o consumo do módulo está acima do limite esperado.

A segunda expressão só permite sinalizar corte quando existe risco e o módulo não é essencial. Assim, módulos com `P = 1` não são selecionados para corte automático pela regra.

### 4.3 Portas lógicas e tabela-verdade

A implementação utiliza as operações equivalentes às portas:

- **NOT:** inverte o valor lógico de `G` e `P`;
- **AND:** exige que as condições conectadas sejam verdadeiras;
- **OR:** torna a saída verdadeira quando pelo menos uma das condições é verdadeira.

A tabela-verdade do circuito apresenta as 16 combinações possíveis das quatro entradas (`A`, `G`, `E` e `P`) e os resultados de `RISCO` e `CORTE`. A representação visual do circuito está no arquivo `circuito_logico.png`.

O circuito é uma representação lógica do comportamento do sistema. Não se afirma que exista integração física com Arduino, sensores ou atuadores. A montagem em hardware ou no Tinkercad pode ser considerada uma evolução futura.

## 5. Estruturas de dados

O protótipo utiliza estruturas adequadas à organização dos dados e ao fluxo de alertas.

### 5.1 Fila de alertas

A fila é implementada com `deque`, da biblioteca `collections`, e segue o princípio FIFO (*First In, First Out*): o primeiro alerta inserido é o primeiro a ser retirado. Essa estrutura é adequada para organizar uma sequência de alertas ou chamados que aguardam atendimento.

### 5.2 Listas e tuplas

Listas são úteis para reunir conjuntos de registros e leituras que serão percorridos, filtrados ou apresentados. Tuplas podem representar conjuntos de valores que devem permanecer agrupados durante uma operação, sem alteração de sua estrutura.

### 5.3 Relação com o sistema

A fila organiza o fluxo de alertas, enquanto listas e tuplas apoiam a manipulação de conjuntos de dados usados nas consultas e análises. O banco relacional mantém os registros persistentes; as estruturas em memória ajudam o programa a processá-los durante a execução.

O projeto prioriza essas estruturas porque elas atendem às necessidades demonstradas no protótipo. Árvores, tabelas hash e grafos não são apresentados como funcionalidades implementadas nesta versão.

## 6. Simulação computacional e integração matemática

A simulação computacional estuda o comportamento do banco de baterias da colônia ao longo de ciclos de operação. Ela utiliza dados do SQLite e compara cenários energéticos.

### 6.1 Variáveis utilizadas

Entre as variáveis consideradas estão:

- capacidade total da bateria, em kWh;
- carga inicial e carga mínima;
- eficiência de armazenamento;
- geração de energia;
- consumo de energia;
- temperatura externa;
- radiação ou perfil de geração solar;
- ciclo de operação.

### 6.2 Modelo discreto da bateria

A atualização da energia armazenada é realizada em passos de tempo. Definindo o saldo como:

\[
saldo(t) = geração(t) - consumo(t)
\]

a carga seguinte é calculada considerando a eficiência quando há excedente de geração:

\[
carga(t+1) =
\begin{cases}
carga(t) + eficiência \cdot saldo(t), & \text{se } saldo(t) > 0\\
carga(t) + saldo(t), & \text{se } saldo(t) \leq 0
\end{cases}
\]

O resultado é limitado ao intervalo entre zero e a capacidade máxima da bateria. Esse modelo representa, de forma simplificada, o carregamento e o descarregamento do armazenamento.

### 6.3 Cenários simulados

O código prevê a comparação de cenários como:

- cenário registrado, baseado nos dados simulados;
- cenário com corte de cargas não essenciais;
- cenário de tempestade severa sem corte;
- cenário de tempestade severa com corte.

A comparação permite observar como diferentes condições de geração e consumo afetam a carga disponível, as horas abaixo do limite mínimo e a energia não atendida.

### 6.4 Integração definida e numérica

O módulo utiliza SymPy para calcular simbolicamente a energia solar teórica em um perfil diário simplificado. A expressão considera uma curva senoidal entre 6h e 18h:

\[
E = \int_{6}^{18} P_p \sin\left(\frac{\pi(t-6)}{12}\right)dt
= \frac{24P_p}{\pi}
\]

O resultado teórico é comparado com a soma das leituras horárias, que funciona como aproximação numérica baseada nos dados.

### 6.5 Método de Monte Carlo

O método de Monte Carlo é utilizado para executar várias simulações com ocorrências aleatórias de tempestades de poeira. A partir dessas execuções, o sistema estima a frequência com que a carga da bateria fica abaixo do limite mínimo definido.

A quantidade de execuções pode ser informada no menu, com valor padrão de 500. Quanto maior o número de execuções, maior tende a ser a estabilidade da estimativa, embora o resultado continue condicionado às hipóteses e distribuições utilizadas no modelo.

### 6.6 Limitações da simulação

A simulação utiliza dados artificiais e regras simplificadas. Ela não reproduz integralmente o clima marciano, a degradação real de baterias, falhas físicas, perdas elétricas detalhadas ou todos os comportamentos de uma colônia. Portanto, seus resultados servem para comparar cenários dentro do protótipo, não para dimensionar uma instalação real sem validação adicional.

## 7. Modelagem linear aplicada à tomada de decisão

O projeto inclui um módulo de regressão linear associado à análise do consumo energético em função da temperatura. A finalidade é explorar a relação entre as variáveis e produzir uma estimativa que possa apoiar o planejamento energético.

### 7.1 Variáveis do modelo

- **Variável explicativa (`X`):** temperatura registrada;
- **Variável resposta (`y`):** consumo energético do módulo.

A regressão linear simples pode ser representada por:

\[
\hat{y} = \beta_0 + \beta_1X
\]

Em que:

- \(\hat{y}\) é o consumo estimado;
- \(\beta_0\) é o intercepto;
- \(\beta_1\) é o coeficiente associado à temperatura;
- \(X\) é a temperatura utilizada como entrada.

Um coeficiente positivo indica que, nos dados utilizados, temperaturas maiores estão associadas a maior consumo estimado. Um coeficiente negativo indica associação inversa. Essa interpretação não demonstra, por si só, causalidade.

### 7.2 Análise e avaliação

A avaliação deve considerar a dispersão dos dados, a relação entre temperatura e consumo e a diferença entre valores observados e estimados. Quando calculadas pelo módulo, métricas como \(R^2\), MAE ou RMSE podem ajudar a avaliar o ajuste e o erro das previsões.

**Resultados numéricos a inserir após executar a opção 11 do menu:**

| Resultado | Valor obtido na execução |
|---|---|
| Intercepto (\(\beta_0\)) | [preencher com a saída real] |
| Coeficiente da temperatura (\(\beta_1\)) | [preencher com a saída real] |
| \(R^2\) | [preencher, se exibido pelo programa] |
| MAE ou RMSE | [preencher, se exibido pelo programa] |
| Quantidade de registros utilizados | [preencher com a saída real] |

Os valores acima não foram inventados: devem ser copiados da execução efetiva do programa. Se o módulo não calcular alguma dessas métricas, ela não deve ser declarada como resultado obtido.

### 7.3 Limitações do modelo

A regressão depende da qualidade e da quantidade dos dados simulados. O consumo pode ser influenciado por outros fatores, como tipo do módulo, horário, ocupação, estado dos equipamentos e disponibilidade de energia. Por isso, a temperatura isolada não explica necessariamente todo o comportamento do consumo. O modelo deve ser usado como estimativa auxiliar, não como decisão automática.

## 8. Proposta de integração de IA e sistemas multiagentes

A versão atual do SIFSM possui funcionalidades determinísticas em Python, como consultas, regras booleanas, fila de alertas, simulação e regressão. A integração de IA é apresentada nesta seção como **proposta conceitual**, não como um agente de IA já implementado no código.

### 8.1 Arquitetura proposta

Uma evolução possível seria organizar agentes especializados:

1. **Agente triador:** recebe uma solicitação da equipe da colônia e identifica o assunto — energia, manutenção ou consulta de dados.
2. **Agente de energia:** solicita dados de consumo e bateria às ferramentas determinísticas e resume os cenários simulados.
3. **Agente de manutenção:** organiza alertas e consulta o histórico de manutenção.
4. **Agente de dados:** prepara respostas com base nos registros autorizados do banco.

### 8.2 Ferramentas e handoffs

Os agentes não deveriam inventar valores nem alterar diretamente os registros sem autorização. Eles poderiam chamar funções determinísticas já existentes ou futuramente disponibilizadas, por exemplo:

- consultar módulos e leituras;
- executar a regra booleana;
- consultar a fila de alertas;
- executar a simulação da bateria;
- consultar o resultado da regressão.

Um *handoff* ocorreria quando o agente triador encaminhasse uma solicitação ao especialista correspondente. Por exemplo, uma pergunta sobre queda de carga seria encaminhada ao agente de energia.

### 8.3 Guardrails, sessões e RAG

Os guardrails propostos incluem:

- limitar as consultas aos dados necessários e autorizados;
- não permitir que a IA execute corte de energia por conta própria;
- exigir confirmação humana antes de ações operacionais;
- informar quando não houver dados suficientes;
- diferenciar resultados calculados pelo sistema de recomendações geradas pela IA;
- manter registro das consultas e das ferramentas acionadas.

Uma sessão poderia manter o contexto de uma solicitação durante o atendimento. Um mecanismo de RAG poderia recuperar trechos de uma documentação operacional aprovada, como limites de bateria, procedimentos de manutenção e descrição dos módulos. Essa base precisaria ser revisada e atualizada.

A proposta mantém as regras críticas em funções determinísticas e reserva à IA o papel de interpretar solicitações, localizar informações e explicar resultados. A supervisão humana continua necessária.

## 9. Arquitetura computacional e desempenho

O SIFSM pode ser analisado em camadas de processamento, armazenamento e apresentação.

### 9.1 CPU e processamento geral

A CPU executa o programa principal, as operações CRUD, as regras booleanas e o controle do fluxo do menu. Essas tarefas são relativamente leves e podem ser realizadas por um processador de uso geral.

### 9.2 GPU, NPU e TPU

Na versão atual, não há requisito de uso de GPU, NPU ou TPU. Conceitualmente:

- **GPU:** poderia acelerar cálculos paralelos de grande volume, caso as simulações crescessem significativamente;
- **NPU:** poderia ser útil em uma futura aplicação com inferência local de modelos de IA;
- **TPU ou aceleradores específicos:** poderiam atender cargas especializadas de aprendizado de máquina, caso existissem necessidade e infraestrutura compatíveis.

Para o protótipo atual, esses aceleradores não são necessários. Utilizá-los sem demanda poderia aumentar o custo energético e a complexidade sem benefício proporcional.

### 9.3 Memória, armazenamento e movimentação de dados

O SQLite mantém os dados persistentes em arquivo. Durante a execução, os registros consultados são carregados na memória RAM para processamento. A leitura excessiva de dados, cópias desnecessárias e consultas pouco seletivas podem aumentar o tempo de processamento e a movimentação de dados.

Índices e consultas adequadas ajudam a reduzir o trabalho do banco. Em uma implantação maior, seria importante monitorar uso de memória, tempo de consulta, largura de banda e custo energético do processamento.

### 9.4 Computação heterogênea e sustentabilidade

Uma arquitetura futura poderia distribuir tarefas de acordo com sua natureza: controle simples em unidades de baixo consumo, processamento geral na CPU e aceleração especializada apenas quando justificável. Essa distribuição é uma possibilidade arquitetural, não uma implementação física presente no protótipo.

## 10. Sustentabilidade, cidadania digital e impacto socioambiental

A proposta do SIFSM está ligada à sustentabilidade porque busca antecipar situações de escassez e apoiar o uso responsável da energia.

### 10.1 Uso responsável dos recursos

O monitoramento de consumo, geração e carga da bateria ajuda a identificar desequilíbrios energéticos. A regra booleana sinaliza condições de risco e diferencia módulos essenciais dos não essenciais, evitando que a lógica de corte trate todos os módulos da mesma forma.

### 10.2 Simulação para reduzir desperdícios

A comparação de cenários permite estudar previamente o efeito de tempestades e de cortes de cargas não essenciais. Isso pode apoiar decisões de planejamento antes de qualquer mudança operacional real.

### 10.3 Resiliência e autonomia

O armazenamento de energia e a análise da carga mínima contribuem para discutir a resiliência da colônia em períodos de baixa geração. A fila de alertas também ajuda a organizar o tratamento de ocorrências.

### 10.4 Privacidade, transparência e economia dos dados

Dados operacionais podem revelar padrões de atividade e informações sobre a rotina da tripulação. Uma implantação real deveria aplicar controle de acesso, coleta mínima, finalidade definida, registro de consultas e transparência sobre o uso dos dados.

A economia dos dados pode gerar benefícios quando as informações melhoram a operação, mas também cria riscos se forem reutilizadas sem autorização ou sem uma finalidade legítima.

### 10.5 Sustentabilidade digital e responsabilidade

Processamento, armazenamento e sistemas de IA também consomem energia. Por isso, a solução deve evitar processamento desnecessário, priorizar modelos proporcionais à tarefa e avaliar se o benefício de cada recurso justifica seu custo computacional.

As recomendações automatizadas devem ser explicáveis e submetidas à supervisão humana, especialmente quando puderem afetar serviços essenciais.

## 11. Fluxo integrado do sistema

O funcionamento geral do protótipo pode ser resumido assim:

1. O sistema inicia e verifica a disponibilidade do banco de dados.
2. O usuário seleciona uma opção no menu.
3. O sistema cadastra ou consulta módulos e leituras.
4. Os dados podem alimentar a regra booleana, a fila de alertas, a simulação ou o modelo linear.
5. Os resultados são apresentados no terminal e, quando aplicável, em gráficos.
6. O usuário analisa os resultados considerando as limitações do modelo e a prioridade dos módulos.

Esse fluxo integra persistência de dados, lógica de decisão, estruturas de dados e análise computacional em uma única proposta.

## 12. Limitações e melhorias futuras

As principais limitações da versão atual são:

- uso de dados simulados, e não de sensores reais;
- simplificação do comportamento físico das baterias e da geração solar;
- regressão dependente do conjunto de dados disponível;
- integração de IA apresentada conceitualmente, sem agentes autônomos implementados;
- ausência de controle físico de atuadores ou de conexão com hardware.

Como melhorias futuras, o projeto poderia incluir novos dados de operação, comparação de modelos preditivos, registro histórico mais detalhado, visualização interativa, testes automatizados e integração experimental com sensores virtuais ou físicos. Uma camada de agentes poderia ser adicionada com ferramentas controladas, logs e aprovação humana para qualquer ação sensível.

## 13. Conclusão

O SIFSM demonstra como um sistema integrado pode organizar informações operacionais e apoiar decisões relacionadas à gestão energética de uma colônia marciana simulada. A combinação de banco de dados, CRUD, regra booleana, fila de alertas, simulação de baterias e regressão linear oferece uma base para analisar cenários de consumo e disponibilidade de energia.

A proposta também considera que desempenho computacional, privacidade, sustentabilidade digital e supervisão humana fazem parte da qualidade de uma solução tecnológica. Embora o protótipo não represente uma instalação real nem implemente agentes de IA autônomos, ele apresenta uma arquitetura acadêmica que pode ser ampliada de forma gradual e responsável.

---

## 14. Arquivos relacionados à entrega

- `codigo_fonte.py` — ponto de entrada e menu principal;
- `src/` — módulos Python chamados pelo programa principal;
- `script_banco.sql` — criação da estrutura relacional;
- `dados_aurora_siger.csv` — dados simulados;
- `simulacao_computacional.py` — simulação energética e análises matemáticas;
- `circuito_logico.png` — representação da regra booleana e tabela-verdade;
- `README.md` — instruções de instalação e execução;
- `link_video.txt` — link da apresentação, a ser incluído na entrega final.

## 15. Conferência antes da entrega

- [ ] Preencher os nomes dos integrantes.
- [ ] Executar o menu e conferir as operações CRUD.
- [ ] Executar a opção de regra booleana e comparar com a tabela-verdade.
- [ ] Executar a simulação e conferir os gráficos gerados.
- [ ] Executar a regressão e preencher a tabela da seção 7.2 com os resultados reais.
- [ ] Confirmar que o README lista as dependências efetivamente utilizadas (`numpy`, `pandas`, `matplotlib` e `sympy`, além das bibliotecas padrão).
- [ ] Confirmar que a pasta `src/` e todos os módulos importados estão no ZIP.
- [ ] Incluir o link do vídeo não listado no arquivo `link_video.txt`.
- [ ] Testar a execução a partir da pasta final descompactada.
