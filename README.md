
# Chess Challenge III — Motor de Xadrez

Motor de xadrez autoral desenvolvido em Python para o
**Chess Challenge III — iCEV 2026**.

O projeto implementa um sistema de busca e avaliação
capaz de selecionar movimentos de forma autônoma,
executando localmente e sem depender de APIs externas.

A configuração competitiva utiliza avaliação híbrida,
combinando uma heurística posicional com uma rede
neural convolucional treinada para avaliar posições.

## 1. Estado atual

O ChessEngine possui:

- Negamax com poda Alfa-Beta.
- Aprofundamento iterativo.
- Controle de tempo por lance.
- Busca de quiescência.
- Tabela de transposição com hash Zobrist.
- Ordenação de capturas, promoções e xeques.
- Killer Moves e History Heuristic.
- Avaliação heurística posicional.
- Rede neural convolucional em PyTorch.
- Avaliação híbrida com peso neural configurável.
- Cache de inferências neurais.
- Interface gráfica para operação de partidas.
- Integração com Stockfish 19 para testes.
- Testes automatizados e benchmarks reproduzíveis.
- Exportação de partidas em PGN e métricas em CSV.

O Stockfish é utilizado somente como adversário
externo nos experimentos. Ele não participa das
decisões internas do ChessEngine.

## 2. Configuração competitiva

A configuração de referência foi selecionada para
preservar o comportamento que já demonstrou conseguir
vencer o Stockfish 19 com o nível configurado para
2000 Elo.

| Componente | Configuração |
|---|---|
| Avaliador | HybridEvaluator |
| Modelo | weights/simple_chess_net.pth |
| Peso neural | 0.40 (40%) |
| Peso heurístico | 0.60 (60%) |
| Heurística | HeuristicEvaluator original |
| Orçamento neural | 128 inferências novas por busca |
| Threshold heurístico | 300 centipawns |
| Cache neural | 4096 posições |
| Profundidade inicial | 4 |
| Aprofundamento iterativo | Ativado |
| Tempo de referência | 5 segundos por lance |
| Tabela de transposição | Ativada |
| Capacidade da TT | 20000 entradas |
| Ordenação avançada | Ativada |
| Pontuação de xeques tranquilos | Ativada |
| Quiescência | Versão corrigida |

A variante experimental `KingSafetyHeuristicEvaluator`
não foi ativada, pois os benchmarks não demonstraram
ganho consistente de desempenho.

### 2.1. Como funciona a avaliação híbrida

A avaliação combina duas abordagens:

1. **Heurística:** material, mobilidade, estrutura de
   peões, segurança do rei e outros aspectos posicionais.
2. **Rede neural:** predição numérica da avaliação
   de uma posição a partir da disposição das peças.

Quando a inferência neural é utilizada, a combinação
é calculada por:

```text
avaliacao = 0.60 * heuristica + 0.40 * neural
```

O percentual não significa que a rede é consultada
em todas as posições.

O motor possui:

- Limite de inferências novas por busca.
- Cache para reutilizar inferências existentes.
- Threshold para evitar consultas neurais em posições
  com avaliação heurística muito elevada.

Quando alguma dessas restrições impede uma nova
inferência, a posição pode ser avaliada somente
pela heurística.

Isso reduz custo computacional, mas também representa
uma limitação da avaliação híbrida atual.

### 2.2. Profundidade e tempo

A configuração `max_depth=4` é utilizada como
parâmetro inicial do motor.

Com `use_full_time=True`, esse valor não funciona
como limite máximo de profundidade.

O ChessEngine continua tentando buscas mais profundas
enquanto houver tempo disponível.

Somente iterações integralmente concluídas substituem
o melhor resultado anterior.

Se o tempo acabar durante uma iteração, o motor
preserva o melhor lance da última profundidade
concluída.

O orçamento competitivo de referência é de
**5 segundos por lance**.

Esse orçamento é independente do controle do
relógio físico da partida.

## 3. Tecnologias

| Tecnologia | Finalidade |
|---|---|
| Python | Linguagem principal |
| python-chess | Regras, tabuleiro e movimentos |
| PyTorch | Execução da rede neural |
| NumPy | Representação numérica das posições |
| Tkinter | Interface gráfica |
| pytest | Testes automatizados |
| Stockfish 19 | Adversário externo de referência |
| Git | Versionamento |

O sistema foi desenvolvido para execução local.

A inferência neural utiliza CPU e não exige GPU
dedicada para funcionar.

O desempenho depende do processador e da memória
disponíveis.

## 4. Arquitetura

```text
            Interface / Scripts
                    |
                    v
                ChessEngine
                    |
                    v
          Iterative Deepening
                    |
                    v
            Negamax + Alfa-Beta
                    |
          +---------+---------+
          |         |         |
          v         v         v
      Ordering     TT     Quiescence
          |                   |
          +---------+---------+
                    |
                    v
             HybridEvaluator
                    |
             +------+------+
             |             |
             v             v
       Heuristica      Rede neural
          60%              40%
             |             |
             +------+------+
                    |
                    v
              Avaliacao
                    |
                    v
              Melhor lance
```

### Componentes principais

**`src/chess_engine/engine.py`**

Coordena a busca, o tempo disponível, as iterações
de profundidade e a seleção final de movimentos.

**`src/chess_engine/search/negamax.py`**

Implementa Negamax com poda Alfa-Beta, integração
com tabela de transposição e avaliação de posições
terminais.

**`src/chess_engine/search/quiescence.py`**

Continua a análise em posições táticas por meio
de capturas e promoções, com tratamento especial
das respostas a xeques.

**`src/chess_engine/search/move_ordering.py`**

Ordena movimentos usando critérios táticos,
Killer Moves e History Heuristic.

**`src/chess_engine/search/transposition.py`**

Armazena resultados de posições pesquisadas
para reduzir cálculos repetidos.

**`src/chess_engine/evaluation/heuristic.py`**

Avalia material, mobilidade, estrutura de peões,
segurança do rei, peças e características posicionais.

**`src/chess_engine/evaluation/neural.py`**

Carrega a rede treinada, realiza inferências e
combina as avaliações heurística e neural.

**`src/chess_engine/neural/model.py`**

Define a arquitetura convolucional SimpleChessNet.

**`src/chess_engine/neural/representation.py`**

Transforma o tabuleiro em um tensor com 12 canais,
representando os tipos de peças de ambos os lados.

## 5. Instalação

### 5.1. Clonar o repositório

```powershell
git clone https://github.com/Ik7Mt0s/Chess-Challenge.git
cd Chess-Challenge
```

### 5.2. Criar ambiente virtual

No Windows:

```powershell
py -3.14 -m venv .venv
.\.venv\Scripts\Activate.ps1
```

### 5.3. Instalar dependências

```powershell
python -m pip install -e ".[dev]"
```

A instalação deve incluir `python-chess`, `numpy`,
`torch` e `pytest`.

Se o ambiente já estiver configurado, basta ativar
o `.venv` existente.

### 5.4. Pesos neurais

O arquivo utilizado pela configuração competitiva é:

```text
weights/simple_chess_net.pth
```

Esse arquivo precisa existir localmente.

Caso os pesos não estejam incluídos no repositório,
eles devem ser disponibilizados separadamente para
executar o modo híbrido.

A aplicação não baixa o modelo automaticamente.

## 6. Executar a interface de competição

Execute na raiz do projeto:

```powershell
python main.py
```

A interface Tkinter permite:

- Escolher jogar de brancas ou pretas.
- Registrar os movimentos do adversário.
- Calcular os movimentos do ChessEngine.
- Visualizar o tabuleiro e os lances legais.
- Consultar a avaliação e a profundidade alcançada.
- Desfazer movimentos.
- Registrar partidas e métricas em arquivos.

### Configuração inicial

A interface inicia com:

```text
Modelo: simple_chess_net.pth
Avaliador: HybridEvaluator
Peso neural: 40%
Orcamento neural: 128
Profundidade inicial: 4
Tempo por lance: 5 segundos
Busca iterativa por tempo: ativada
```

A cor do motor, a profundidade inicial e o tempo
por lance podem ser ajustados na interface.

A versão atual não implementa uma política automática
completa para administrar o relógio de 25 minutos
de cada jogador.

### Como operar

1. Execute `python main.py`.
2. Escolha a cor do ChessEngine.
3. Confirme as configurações.
4. Clique em **Iniciar nova partida**.
5. Registre os lances do adversário pelo tabuleiro.
6. Quando for a vez do ChessEngine, clique em
   **Calcular jogada do motor**.
7. Reproduza o lance indicado no tabuleiro físico.
8. Repita o processo até o término da partida.

Quando o motor joga de pretas, é necessário registrar
primeiro o lance das brancas.

### Logs da interface

As partidas são armazenadas em:

```text
competition_logs/
    game_YYYYMMDD_HHMMSS_XXXXXX/
        game.pgn
        moves.csv
        state.json
```

O PGN contém o histórico dos movimentos e metadados
da configuração utilizada.

O CSV registra informações dos lances, incluindo
profundidade, avaliação e métricas da busca.

O JSON registra o estado e os parâmetros da partida.

## 7. Confrontos contra Stockfish 19

O projeto possui um script visual para executar
partidas e baterias de comparação com Stockfish 19.

Arquivo:

```text
scripts/stockfish_match_visual.py
```

O Stockfish é executado como processo externo
e se comunica pelo protocolo UCI.

### 7.1. Configuração de referência: Stockfish 2000

Este é o comando utilizado para a configuração
que registrou uma vitória em 32 lances:

```powershell
python scripts/stockfish_match_visual.py --model weights/simple_chess_net.pth --neural-weight 0.4 --depth 4 --our-time 5 --stockfish-time 5 --elo-levels 2000 --games-per-level 2
```

Parâmetros principais:

| Parâmetro | Valor | Significado |
|---|---|---|
| `--model` | simple_chess_net.pth | Pesos da rede |
| `--neural-weight` | 0.4 | Peso de 40% nas avaliações híbridas |
| `--depth` | 4 | Profundidade configurada |
| `--our-time` | 5 | Tempo do ChessEngine por lance |
| `--stockfish-time` | 5 | Tempo do Stockfish por lance |
| `--elo-levels` | 2000 | Nível configurado do Stockfish |
| `--games-per-level` | 2 | Duas partidas |

A execução utiliza a estratégia original de
pontuação dos xeques tranquilos.

As baterias alternam as cores do nosso motor.

Na configuração utilizada nos experimentos,
o motor tenta aproveitar o tempo disponível por meio
do aprofundamento iterativo.

### 7.2. Resultados registrados

Com a rede `simple_chess_net.pth`, peso neural de
40% e cinco segundos por lance, foram registradas:

| Partida | Cor do ChessEngine | Resultado |
|---|---|---|
| 1 | Brancas | Vitória em 32 lances |
| 2 | Pretas | Derrota em 25 lances |

A primeira partida terminou com:

```text
31. c8=Q h4
32. Qc6#
```

O resultado da bateria foi de uma vitória e
uma derrota.

Esses resultados demonstram que o ChessEngine
conseguiu vencer uma partida contra Stockfish 19
configurado para o alvo de 2000 Elo.

Entretanto, essa amostra não permite afirmar que
o ChessEngine possui rating de 2000 Elo, nem que
consegue vencer esse adversário consistentemente.

### 7.3. Limitações da comparação

O parâmetro de Elo do Stockfish utiliza seu mecanismo
de limitação de força.

Esse valor é um alvo de configuração, não uma
medição independente do rating do ChessEngine.

Além disso:

- Stockfish e ChessEngine possuem algoritmos diferentes.
- O limite nominal de tempo não implica igualdade de força.
- Os resultados variam conforme a posição e as cores.
- Duas partidas são insuficientes para medir um rating.
- O desempenho do ChessEngine depende do hardware local.

### 7.4. Arquivos produzidos

Os resultados dos confrontos ficam organizados em:

```text
benchmarks/
    stockfish_matches/
        original/
            run_YYYYMMDD_HHMMSS_XXXXXX/
                game_001_elo_2000_white.pgn
                game_001_elo_2000_white_moves.csv
                game_002_elo_2000_black.pgn
                game_002_elo_2000_black_moves.csv
                summary.csv
```

A estrutura permite consultar partidas, resultados
e métricas posteriormente.

Para conhecer todos os argumentos disponíveis:

```powershell
python scripts/stockfish_match_visual.py --help
```

## 8. Treinamento neural

A implementação neural utiliza uma rede convolucional
chamada `SimpleChessNet`.

Entrada:

```text
(batch_size, 12, 8, 8)
```

Saída:

```text
Escalar normalizado entre -1 e 1
```

A avaliação representa a posição do ponto de vista
do jogador ativo e é convertida para centipawns
antes de ser combinada com a avaliação heurística.

O modelo competitivo foi ajustado com posições
extraídas de partidas do Lichess.

No ajuste fino registrado, foram amostradas
aproximadamente um milhão de posições, distribuídas
entre treinamento e validação, ao longo de seis épocas.

O erro de validação diminuiu durante o treinamento.

Essa redução indica melhoria na métrica utilizada
no treinamento, mas não garante aumento equivalente
na força competitiva do motor.

O treinamento não precisa ser repetido para
executar o ChessEngine.

## 9. Benchmarks

O projeto contém ferramentas para investigar
desempenho, custo computacional e características
das buscas.

### Benchmark de posições

```powershell
python scripts/benchmark_search.py --pgn "benchmarks/stockfish_matches/original/run_20261104_205222_951944/game_002_elo_2000_black.pgn" --model weights/simple_chess_net.pth --weight 0.4 --budget 128 --time 5 --depth 4 --full-time --sample-step 3 --max-positions 15 --profiles baseline
```

O benchmark apresenta:

- Movimento escolhido.
- Avaliação em centipawns.
- Profundidade concluída.
- Tempo gasto.
- Nós de Negamax.
- Nós de quiescência.
- Nós por segundo.
- Inferências neurais executadas.
- Inferências ignoradas por limite.
- Reutilizações do cache neural.

### Resultados de otimização

Foram comparados orçamentos de 64 e 128
inferências neurais por busca.

O orçamento 64 apresentou melhor velocidade
e maior profundidade média em alguns conjuntos
de posições.

Entretanto, os experimentos não demonstraram
uma melhoria competitiva suficiente para substituir
a configuração de referência de 128 inferências.

Também foi avaliada uma variante experimental
de segurança do rei.

Essa variante não foi adotada porque apresentou
custo adicional e resultados inconclusivos quanto
à qualidade dos movimentos.

## 10. Testes automatizados

Para executar todos os testes:

```powershell
python -m pytest tests/ -q
```

Para executar somente os testes de melhorias
da busca:

```powershell
python -m pytest tests/test_search_improvements.py -q
```

Para validar o orçamento neural:

```powershell
python -m pytest tests/test_neural_budget.py -q
```

Os testes verificam aspectos como:

- Legalidade dos movimentos.
- Integridade do estado do tabuleiro.
- Negamax e Alfa-Beta.
- Quiescência.
- Xeques e xeque-mate.
- Tabela de transposição.
- Ordenação dos movimentos.
- Controle de tempo.
- Avaliações heurísticas e neurais.
- Cache neural.
- Limites de inferência.
- Integração entre componentes.

A suíte foi executada durante o desenvolvimento,
e os testes passaram após a revisão do cache neural.

Os testes funcionais não comprovam, isoladamente,
a força competitiva do ChessEngine.

## 11. Limitações conhecidas

**Profundidade em posições táticas**

Algumas posições exigem grande quantidade de buscas
de quiescência e impedem o aprofundamento desejado
dentro do tempo disponível.

**Consumo computacional**

A implementação utiliza Python e PyTorch em CPU,
o que limita o número de nós pesquisados por segundo.

**Orçamento neural**

O número máximo de inferências pode fazer com que
posições diferentes sejam tratadas por combinações
distintas de avaliação.

**Segurança do rei**

O motor ainda pode escolher avanços de peões
que deixam o próprio rei vulnerável.

**Tempo de partida**

O sistema controla tempo por lance, mas não gerencia
automaticamente todo o relógio oficial.

**Força competitiva**

Os confrontos disponíveis são insuficientes para
estimar com confiança o Elo real do ChessEngine.

## 12. Requisitos do campeonato

O projeto foi desenvolvido considerando
o Chess Challenge III — iCEV 2026.

Entre os requisitos identificados no regulamento
estão a operação local, a seleção autônoma de
movimentos e o registro dos lances do adversário.

O regulamento também prevê relógio físico
de 25 minutos por jogador.

O software não depende de conexão com serviços
externos para calcular seus movimentos.

O atendimento completo às regras operacionais
e de entrega deve ser conferido no edital oficial.

Referência:

[Edital Chess Challenge III — iCEV 2026](https://www.somosicev.com/wp-content/uploads/2026/09/Chess-Challenge-III-1.pdf)

## 13. Autoria e referências

Projeto desenvolvido de forma independente,
utilizando técnicas clássicas de construção
de motores de xadrez e modelos de aprendizado
de máquina.

Conceitos técnicos estudados incluem:

- Negamax.
- Poda Alfa-Beta.
- Aprofundamento iterativo.
- Quiescência.
- Tabelas de transposição.
- Heurísticas posicionais.
- Redes neurais convolucionais.

Repositório utilizado como referência conceitual:

https://github.com/xInovatechTecnologia/xeque-lfm

O Stockfish é utilizado como adversário externo
para validação e experimentos, sem substituir
o mecanismo de escolha de movimentos do projeto.

## 14. Execução recomendada

Para operar o ChessEngine durante uma partida:

```powershell
python main.py
```

Para repetir o confronto de referência
contra Stockfish 19 configurado para 2000 Elo:

```powershell
python scripts/stockfish_match_visual.py --model weights/simple_chess_net.pth --neural-weight 0.4 --depth 4 --our-time 5 --stockfish-time 5 --elo-levels 2000 --games-per-level 2
```

**Configuração preservada:**
HybridEvaluator, rede com 40% de peso,
heurística original, 128 inferências neurais
por busca e aprofundamento iterativo com
cinco segundos de referência por lance.

O objetivo da entrega é disponibilizar um
motor autoral, funcional, executável localmente
e com desempenho demonstrado por testes e
partidas registradas.
