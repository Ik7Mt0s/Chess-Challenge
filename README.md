
# Chess Challenge III — Motor de Xadrez

Motor de xadrez desenvolvido em Python para participação no **Chess Challenge III — ICEV 2026**.

O projeto tem como objetivo construir um motor capaz de analisar posições, pesquisar possibilidades e selecionar movimentos de forma autônoma, com execução local e sem dependência de serviços externos durante as partidas.

A implementação utiliza **Negamax com poda Alfa-Beta, aprofundamento iterativo, busca de quiescência, tabela de transposição e ordenação avançada de movimentos**.

> **Estado atual:** as etapas de fundação, otimização da busca e evolução da avaliação estão implementadas. O projeto também possui integração local com Stockfish 19, testes automatizados, benchmarks e ferramentas de análise de desempenho. A preparação para o formato oficial do torneio continua em desenvolvimento.

## 1. Tecnologias utilizadas

| Tecnologia | Finalidade |
|---|---|
| Python 3.14 | Linguagem e ambiente de desenvolvimento |
| python-chess | Tabuleiro, movimentos legais e regras do xadrez |
| pytest | Testes automatizados |
| Tkinter | Interfaces gráficas de partidas |
| Stockfish 19 | Motor adversário para testes competitivos |
| setuptools | Instalação e empacotamento |
| Git e GitHub | Versionamento e colaboração |

O projeto não exige GPU dedicada, banco de dados, Docker, modelos neurais ou APIs externas.

O Stockfish é utilizado exclusivamente como adversário externo nos experimentos. O motor desenvolvido neste projeto continua responsável por todas as suas próprias decisões.

## 2. Arquitetura

O motor foi organizado em componentes independentes:

```text
Interface CLI / Self-play / Stockfish
                |
                v
           ChessEngine
                |
       +--------+--------+
       |                 |
       v                 v
  TimeManager     Iterative Deepening
                         |
                         v
                  Negamax + Alfa-Beta
                         |
              +----------+----------+
              |          |          |
              v          v          v
         Ordenação   Transposition  Quiescence
         de lances      Table        Search
              |          |
              v          v
         Killer Moves  Zobrist Hash
         History
         Heuristic
              |
              v
       HeuristicEvaluator
              |
              v
         Melhor lance
```

O `ChessEngine` coordena a pesquisa, enquanto os módulos especializados implementam avaliação, ordenação, cache e controle de tempo.

A separação entre avaliação e busca permite aprimorar cada componente independentemente.

### Estrutura do projeto

```text
Chess Challenge/
├── benchmarks/
│   ├── draw_rules_validation/
│   ├── move_ordering_v2/
│   ├── profiling/
│   ├── search_ordering_v2/
│   ├── stockfish_matches/
│   │   ├── original/
│   │   └── optimized/
│   ├── evaluation_benchmark.csv
│   ├── ordering_benchmark.csv
│   ├── search_benchmark.csv
│   └── self_play.pgn
├── docs/
├── engines/
│   └── stockfish/
│       └── stockfish-windows-x86-64-universal.exe
├── scripts/
│   ├── benchmark_evaluation.py
│   ├── benchmark_evaluation_matches.py
│   ├── benchmark_move_ordering_v2.py
│   ├── benchmark_ordering.py
│   ├── benchmark_search.py
│   ├── benchmark_search_ordering_v2.py
│   ├── profile_engine.py
│   ├── self_play.py
│   ├── self_play_visual.py
│   ├── stockfish_match_visual.py
│   └── validate_draw_rules.py
├── src/
│   └── chess_engine/
│       ├── evaluation/
│       │   ├── base.py
│       │   └── heuristic.py
│       ├── models/
│       │   └── loader.py
│       ├── search/
│       │   ├── draw_rules.py
│       │   ├── metrics.py
│       │   ├── move_ordering.py
│       │   ├── negamax.py
│       │   ├── quiescence.py
│       │   └── transposition.py
│       ├── utils/
│       │   └── time_manager.py
│       ├── board.py
│       └── engine.py
├── tests/
├── main.py
├── pyproject.toml
├── requirements.txt
├── .gitignore
└── README.md
```

## 3. Funcionalidades implementadas

### 3.1. Gerenciamento do tabuleiro

**Arquivo:** `src/chess_engine/board.py`

A classe `ChessBoard` encapsula operações do `python-chess`:

- Inicialização de partidas e posições FEN.
- Listagem de movimentos legais.
- Execução de movimentos SAN e UCI.
- Desfazer movimentos.
- Reinicialização do tabuleiro.
- Identificação de xeque-mate e empates.
- Consulta do resultado da partida.

As regras do xadrez são tratadas pelo `python-chess`, enquanto a escolha dos movimentos é responsabilidade do motor desenvolvido neste projeto.

### 3.2. Avaliação heurística

**Arquivos:**
- `src/chess_engine/evaluation/base.py`
- `src/chess_engine/evaluation/heuristic.py`

O contrato `PositionEvaluator` define a interface de avaliação de posições.

A implementação `HeuristicEvaluator` considera material, tabelas peça-casa e critérios posicionais, adaptados à fase da partida.

| Peça | Valor em centipeões |
|---|---:|
| Peão | 100 |
| Cavalo | 320 |
| Bispo | 330 |
| Torre | 500 |
| Dama | 900 |
| Rei | 0 |

Também são considerados:

- Segurança do rei.
- Estrutura de peões.
- Peões dobrados, isolados e passados.
- Mobilidade das peças.
- Centralização.
- Atividade das torres.
- Fase da partida.

Os pesos são heurísticas iniciais e ainda não foram calibrados por experimentos competitivos em larga escala.

### 3.3. Negamax com poda Alfa-Beta

**Arquivo:** `src/chess_engine/search/negamax.py`

O Negamax pesquisa continuações possíveis, alternando a perspectiva entre os jogadores.

A poda Alfa-Beta evita explorar ramos que não podem melhorar o resultado da pesquisa.

A implementação inclui:

- Busca recursiva por profundidade.
- Poda Alfa-Beta.
- Reconhecimento de posições terminais.
- Integração com quiescência.
- Consulta e armazenamento na tabela de transposição.
- Ordenação avançada de movimentos.
- Verificação do limite de tempo.
- Restauração do tabuleiro após cada exploração.

### 3.4. Busca de quiescência

**Arquivo:** `src/chess_engine/search/quiescence.py`

A busca de quiescência reduz o efeito horizonte, evitando encerrar imediatamente a avaliação em determinadas posições taticamente instáveis.

A implementação considera principalmente capturas e promoções. Quando o jogador está em xeque, analisa as respostas legais necessárias.

A busca permanece sujeita ao controle de tempo.

### 3.5. Tabela de transposição

**Arquivo:** `src/chess_engine/search/transposition.py`

A tabela de transposição armazena resultados de posições já pesquisadas para reduzir trabalho repetido.

A identificação utiliza hash Zobrist e informações adicionais relacionadas ao histórico da posição.

Cada entrada registra:

- Profundidade pesquisada.
- Avaliação.
- Tipo de limite (`EXACT`, `LOWER` ou `UPPER`).
- Melhor movimento encontrado.

A tabela possui capacidade limitada, configurada por padrão para 20.000 entradas.

O cache permanece em memória durante a execução.

### 3.6. Ordenação avançada de movimentos

**Arquivo:** `src/chess_engine/search/move_ordering.py`

A ordenação prioriza movimentos potencialmente relevantes antes da busca.

Os critérios incluem:

- Melhor movimento da tabela de transposição.
- Capturas, considerando atacante e vítima.
- Promoções.
- Xeques.
- Killer Moves.
- History Heuristic.

A ordenação não elimina movimentos legais. Seu objetivo é aumentar a eficiência da poda Alfa-Beta.

A implementação também permite comparar duas estratégias de pontuação:

- **Original:** considera a pontuação de xeques em movimentos tranquilos.
- **Otimizada:** evita esse cálculo antecipado para reduzir o custo da ordenação.

A configuração `score_quiet_checks` permite alternar entre as estratégias nos experimentos.

### 3.7. Aprofundamento iterativo

**Arquivo:** `src/chess_engine/engine.py`

O motor pesquisa profundidades progressivas:

```text
Profundidade 1
      |
Profundidade 2
      |
Profundidade 3
      |
     ...
```

O melhor resultado de uma iteração concluída é preservado.

Caso o limite de tempo seja atingido, o motor retorna o resultado da última profundidade concluída ou um movimento legal de reserva.

O objeto `SearchResult` inclui:

| Campo | Descrição |
|---|---|
| `move` | Movimento selecionado |
| `score` | Avaliação da busca |
| `depth` | Profundidade concluída |
| `elapsed` | Tempo utilizado |
| `status` | Estado da busca |
| `metrics` | Estatísticas da pesquisa |
| `cache` | Estatísticas da tabela de transposição |

### 3.8. Controle de tempo

**Arquivo:** `src/chess_engine/utils/time_manager.py`

O `TimeManager` utiliza `time.monotonic()` para acompanhar o tempo de execução.

A exceção `SearchTimeout` permite interromper cooperativamente a busca quando o prazo é atingido.

O controle atual considera o orçamento de tempo de cada movimento, não o relógio completo de uma partida oficial.

### 3.9. Métricas de busca

**Arquivo:** `src/chess_engine/search/metrics.py`

O motor registra:

- Nós pesquisados pelo Negamax.
- Nós pesquisados pela quiescência.
- Total de nós.
- Cortes Alfa-Beta.
- Consultas e acertos da tabela de transposição.

Essas informações permitem comparar configurações do motor e acompanhar sua evolução.

### 3.10. Detecção otimizada de empates

**Arquivo:** `src/chess_engine/search/draw_rules.py`

O projeto possui uma implementação otimizada para verificações de empate durante a busca.

O objetivo é reduzir o custo das verificações repetidas sem alterar o comportamento esperado das regras.

A equivalência entre as implementações pode ser verificada por meio do script `validate_draw_rules.py`.

### 3.11. Preparação para modelos de IA

**Arquivo:** `src/chess_engine/models/loader.py`

O módulo reserva um ponto de integração para modelos externos.

Atualmente, não existe modelo neural integrado ao motor.

A utilização futura de avaliação neural dependerá de testes de desempenho, consumo de recursos e benefícios demonstrados.

## 4. Instalação e execução

### 4.1. Pré-requisitos

- Python 3.11 ou superior.
- Git.
- Terminal PowerShell, Bash ou equivalente.

O desenvolvimento e os testes recentes foram realizados com Python 3.14.

### 4.2. Clonar o repositório

```powershell
git clone https://github.com/Ik7Mt0s/Chess-Challenge.git
cd Chess-Challenge
```

### 4.3. Criar o ambiente virtual

No Windows:

```powershell
py -3.14 -m venv .venv
.\.venv\Scripts\Activate.ps1
```

No Linux ou macOS:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 4.4. Instalar as dependências

```powershell
python -m pip install -e ".[dev]"
```

### 4.5. Validar a instalação

```powershell
python -c "import chess_engine; print('Motor configurado com sucesso!')"
```

### 4.6. Jogar contra o motor no terminal

```powershell
python main.py
```

O jogador controla as peças brancas e o motor responde com as pretas.

São aceitos movimentos SAN ou UCI:

```text
e4
Nf3
O-O
e2e4
g1f3
```

Comandos disponíveis:

- `sair`: encerra a execução.
- `desfazer`: desfaz um turno completo, quando disponível.

### 4.7. Self-play automatizado

```powershell
python scripts/self_play.py --depth 3 --time 1 --max-plies 100
```

O script coloca duas instâncias do motor para jogar entre si.

Durante a execução, apresenta movimentos, profundidade, avaliação e tempo utilizado.

Ao final, informa o resultado e salva a partida em formato PGN.

### 4.8. Self-play visual

```powershell
python scripts/self_play_visual.py --depth 3 --time 1
```

A interface utiliza Tkinter para apresentar a partida em um tabuleiro gráfico.

Funcionalidades:

- Iniciar e continuar.
- Pausar.
- Executar um lance por vez.
- Reiniciar.
- Ajustar o intervalo visual.
- Acompanhar o histórico.
- Consultar profundidade, avaliação e tempo.
- Exportar a partida em PGN.

A interface visual é destinada ao acompanhamento de partidas entre bots, não à operação em partidas oficiais do campeonato.

## 5. Integração com Stockfish 19

O projeto permite colocar o `ChessEngine` para enfrentar o **Stockfish 19**, um motor de xadrez externo, por meio de uma interface gráfica desenvolvida com Tkinter.

**Arquivo:** `scripts/stockfish_match_visual.py`

A comunicação ocorre pelo protocolo **UCI (Universal Chess Interface)**, utilizando `chess.engine` do `python-chess`.

O Stockfish é executado como adversário independente. Ele não fornece avaliações ou movimentos para o nosso motor durante suas buscas.

### 5.1. Instalação do Stockfish no Windows

1. Acesse [stockfishchess.org/download](https://stockfishchess.org/download/).
2. Baixe o executável adequado ao processador.
3. Extraia o conteúdo para `engines/stockfish/`.
4. Verifique se o executável está no caminho esperado:

```text
engines/stockfish/stockfish-windows-x86-64-universal.exe
```

Para testar no PowerShell:

```powershell
& ".\engines\stockfish\stockfish-windows-x86-64-universal.exe"
```

No console do Stockfish, digite:

```text
uci
```

A resposta deve conter:

```text
uciok
```

Para encerrar:

```text
quit
```

> O executável do Stockfish não é instalado pelo `pip`. Recomenda-se manter os binários externos fora do versionamento Git.

### 5.2. Partida individual contra Stockfish

Para executar uma partida com nosso motor de brancas, profundidade 3, três segundos por lance e Stockfish limitado a 1320 Elo:

```powershell
python scripts/stockfish_match_visual.py --depth 3 --our-time 3 --stockfish-time 3 --elo 1320 --our-color white
```

Para jogar com as pretas:

```powershell
python scripts/stockfish_match_visual.py --depth 3 --our-time 3 --stockfish-time 3 --elo 1320 --our-color black
```

Para enfrentar Stockfish configurado para 1800 Elo:

```powershell
python scripts/stockfish_match_visual.py --depth 3 --our-time 3 --stockfish-time 3 --elo 1800 --our-color white
```

### 5.3. Confrontos automatizados

O script permite executar baterias de partidas contra diferentes configurações de Elo do Stockfish.

Exemplo:

```powershell
python scripts/stockfish_match_visual.py --depth 3 --our-time 3 --stockfish-time 3 --elo-levels 1320 1500 1800 --games-per-level 2
```

Esse comando executa:

| Elo configurado | Partidas |
|---|---:|
| 1320 | 2 |
| 1500 | 2 |
| 1800 | 2 |
| **Total** | **6** |

As partidas alternam as cores do nosso motor para permitir comparações mais equilibradas.

Cada motor recebe um orçamento de até 3 segundos por lance.

O nosso motor também permanece limitado à profundidade máxima configurada em `--depth`.

### 5.4. Comparação entre ordenação original e otimizada

O projeto permite comparar duas estratégias de ordenação de movimentos.

**Estratégia original**

```powershell
python scripts/stockfish_match_visual.py --score-quiet-checks true --depth 3 --our-time 3 --stockfish-time 3 --elo-levels 1320 1500 1800 --games-per-level 2
```

**Estratégia otimizada**

```powershell
python scripts/stockfish_match_visual.py --score-quiet-checks false --depth 3 --our-time 3 --stockfish-time 3 --elo-levels 1320 1500 1800 --games-per-level 2
```

A diferença entre as estratégias é o cálculo antecipado da pontuação de xeques em movimentos tranquilos.

| Configuração | Comportamento |
|---|---|
| `true` | Calcula a pontuação de xeques na ordenação |
| `false` | Evita esse cálculo antecipado |

A otimização não remove os movimentos legais da pesquisa.

O objetivo é reduzir o custo computacional da ordenação, permitindo que o motor utilize melhor seu orçamento de tempo.

A redução de custo não garante, isoladamente, maior força competitiva.

### 5.5. Experimentos com tempos diferentes

**Teste rápido — 0,1 segundo para Stockfish**

```powershell
python scripts/stockfish_match_visual.py --score-quiet-checks false --depth 3 --our-time 3 --stockfish-time 0.1 --elo-levels 1320 1500 1800 --games-per-level 2
```

Esse experimento é útil para comparações rápidas, mas concede ao nosso motor um orçamento de busca maior.

**Teste equilibrado por orçamento — 3 segundos para cada motor**

```powershell
python scripts/stockfish_match_visual.py --score-quiet-checks false --depth 3 --our-time 3 --stockfish-time 3 --elo-levels 1320 1500 1800 --games-per-level 2
```

Esse experimento concede o mesmo orçamento nominal por lance aos dois motores.

Entretanto, isso não significa igualdade de força: Stockfish utiliza algoritmos, estruturas e otimizações diferentes.

Além disso, a profundidade máxima 3 continua sendo uma limitação exclusiva do nosso motor.

### 5.6. Parâmetros de execução

| Parâmetro | Descrição |
|---|---|
| `--stockfish` | Caminho do executável Stockfish |
| `--depth` | Profundidade máxima do nosso motor |
| `--our-time` | Tempo máximo de busca do nosso motor por lance |
| `--stockfish-time` | Tempo de busca concedido ao Stockfish por lance |
| `--elo` | Elo-alvo configurado do Stockfish |
| `--elo-levels` | Lista de níveis de Elo para uma bateria |
| `--games-per-level` | Quantidade de partidas por nível |
| `--our-color` | Cor do nosso motor |
| `--score-quiet-checks` | Ativa ou desativa a pontuação antecipada de xeques tranquilos |
| `--max-plies` | Limite de meios-lances |

Para consultar a lista de parâmetros aceita pela versão instalada:

```powershell
python scripts/stockfish_match_visual.py --help
```

### 5.7. Resultados dos confrontos

Os experimentos automatizados armazenam seus resultados em:

```text
benchmarks/
└── stockfish_matches/
    ├── original/
    │   └── run_YYYYMMDD_HHMMSS_XXXXXX/
    │       ├── game_001_elo_1320_white.pgn
    │       ├── game_001_elo_1320_white_moves.csv
    │       └── summary.csv
    └── optimized/
        └── run_YYYYMMDD_HHMMSS_XXXXXX/
            ├── game_001_elo_1320_white.pgn
            ├── game_001_elo_1320_white_moves.csv
            └── summary.csv
```

Os arquivos possuem funções diferentes:

- **PGN:** histórico completo dos movimentos da partida.
- **CSV por partida:** informações de desempenho e busca.
- **summary.csv:** resultados consolidados da bateria.

Os nomes dos diretórios permitem preservar experimentos anteriores sem misturar as configurações original e otimizada.

### 5.8. Limitações dos experimentos

O Stockfish pode ser configurado com `UCI_LimitStrength` e `UCI_Elo` para reduzir sua força.

O Elo informado é um alvo de configuração, não uma classificação competitiva medida ou garantida.

Também é importante considerar:

- O tempo configurado é um orçamento por lance, não o relógio completo da partida.
- O tempo de inicialização e comunicação com o processo Stockfish pode acrescentar sobrecarga.
- O limite de profundidade do nosso motor não limita a profundidade do Stockfish.
- Uma bateria de poucas partidas não permite estimar com precisão a força do motor.
- Partidas interrompidas por limite de meios-lances devem ser tratadas como inconclusivas, não como empates.

Para uma comparação mais rigorosa, é necessário aumentar a quantidade de partidas, alternar cores e manter configurações reproduzíveis.

## 6. Testes automatizados

O projeto utiliza `pytest`.

Para executar todos os testes:

```powershell
python -m pytest -q
```

Para executar com informações detalhadas:

```powershell
python -m pytest -v
```

Para executar somente a validação final:

```powershell
python -m pytest tests/test_final_validation.py -v
```

Os testes abrangem:

- Gerenciamento do tabuleiro.
- Avaliação heurística.
- Busca Negamax.
- Quiescência.
- Controle de tempo.
- Tabela de transposição.
- Ordenação avançada.
- Métricas de busca.
- Integridade do estado do tabuleiro.
- Detecção de empates.
- Self-play.
- Integração das estratégias de busca.

Os testes verificam correção e estabilidade funcional, mas não comprovam força competitiva.

## 7. Benchmarks e análise de desempenho

Os benchmarks permitem comparar diferentes configurações do motor e acompanhar o impacto das otimizações.

### 7.1. Profiling

Identifica funções que consomem mais tempo durante a busca.

```powershell
python scripts/profile_engine.py --depth 3 --time 3 --repeats 3
```

Resultados:

```text
benchmarks/profiling/
```

### 7.2. Busca e tabela de transposição

Compara configurações da busca e utilização do cache.

```powershell
python scripts/benchmark_search.py --depth 3 --time 3
```

Resultado:

```text
benchmarks/search_benchmark.csv
```

### 7.3. Ordenação durante a busca

Compara as estratégias original e otimizada durante a execução completa do motor.

```powershell
python scripts/benchmark_search_ordering_v2.py --depth 3 --time 3 --repeats 3
```

Resultados:

```text
benchmarks/search_ordering_v2/
```

### 7.4. Ordenação isolada

Mede o custo computacional da ordenação utilizando posições extraídas de partidas PGN.

```powershell
python scripts/benchmark_move_ordering_v2.py --max-positions 200 --repeats 5
```

Resultados:

```text
benchmarks/move_ordering_v2/
```

**Importante:** esse benchmark precisa encontrar partidas PGN no diretório de entrada.

Portanto, execute primeiro uma bateria contra Stockfish ou forneça um diretório com partidas existentes.

Para utilizar outro diretório:

```powershell
python scripts/benchmark_move_ordering_v2.py --input benchmarks/stockfish_matches --max-positions 200 --repeats 5
```

### 7.5. Validação de empates

Compara a implementação original com a otimizada.

```powershell
python scripts/validate_draw_rules.py --sample-every 1 --repeats 3
```

Resultados:

```text
benchmarks/draw_rules_validation/
```

O benchmark utiliza posições de partidas PGN para verificar equivalência e medir desempenho.

### 7.6. Avaliação heurística

Compara versões da avaliação e seu impacto sobre o desempenho.

```powershell
python scripts/benchmark_evaluation.py --depth 3 --time 10 --evaluation-repetitions 300 --repetitions 3 --output benchmarks/evaluation_competition_performance_10s.csv
```

A avaliação mais completa pode consumir mais tempo por posição. Por isso, é importante medir tanto a qualidade das decisões quanto o custo computacional.

### 7.7. Partidas comparativas da avaliação

Comparação com o avaliador anterior:

```powershell
python scripts/benchmark_evaluation_matches.py --opponents baseline --pairs 2 --depth 3 --time 3 --max-plies 60 --csv-output benchmarks/evaluation_competition_baseline.csv --pgn-output benchmarks/evaluation_competition_baseline.pgn
```

Comparação com componentes da avaliação desativados:

```powershell
python scripts/benchmark_evaluation_matches.py --opponents no_mobility no_pawn_structure no_king_safety --pairs 1 --depth 3 --time 3 --max-plies 60 --csv-output benchmarks/evaluation_competition_ablations.csv --pgn-output benchmarks/evaluation_competition_ablations.pgn
```

Esses experimentos permitem analisar a contribuição de diferentes componentes da avaliação.

## 8. Ordem recomendada para validação

Após alterações importantes no motor, recomenda-se executar os experimentos nesta ordem:

1. Testes automatizados.
2. Profiling do motor.
3. Benchmark da busca.
4. Benchmark da ordenação durante a busca.
5. Partidas contra Stockfish com a estratégia original.
6. Partidas contra Stockfish com a estratégia otimizada.
7. Benchmark isolado de ordenação, utilizando os PGNs gerados.
8. Validação das regras de empate.

Essa sequência evita executar benchmarks dependentes de PGNs antes de gerar os arquivos necessários.

Os resultados anteriores devem ser preservados para permitir comparações históricas.

## 9. Limitações conhecidas

Apesar das melhorias, o motor ainda possui limitações relevantes:

1. **Avaliação estratégica:** os critérios heurísticos precisam de calibração e testes adicionais.
2. **Profundidade limitada:** posições complexas podem consumir todo o orçamento antes de concluir a profundidade desejada.
3. **Desempenho em Python:** o custo computacional limita a quantidade de posições pesquisadas por segundo.
4. **Controle de tempo:** ainda não existe gerenciamento completo do relógio oficial de 25 minutos por jogador.
5. **Interface competitiva:** a interface visual atual é destinada a experimentos e não à operação oficial do campeonato.
6. **Avaliação neural:** nenhum modelo de aprendizado de máquina participa das decisões.
7. **Força competitiva:** os confrontos existentes ainda são insuficientes para estimar um rating confiável.
8. **Quiescência:** existem oportunidades adicionais de otimização em posições táticas complexas.
9. **Tabela de transposição:** o comportamento em posições complexas ainda precisa de investigação e profiling adicional.

## 10. Roadmap de desenvolvimento

### Etapa 1 — Fundação do projeto

- [x] Estrutura modular em Python.
- [x] Configuração de dependências.
- [x] Gerenciamento do tabuleiro.
- [x] Avaliação heurística inicial.
- [x] Negamax com poda Alfa-Beta.
- [x] Ordenação básica de movimentos.
- [x] Aprofundamento iterativo.
- [x] Controle de tempo por busca.
- [x] Interface inicial pelo terminal.
- [x] Testes automatizados iniciais.

### Etapa 2 — Otimização da busca

- [x] Busca de quiescência.
- [x] Tabela de transposição.
- [x] Hash Zobrist com informações adicionais de histórico.
- [x] Ordenação avançada de movimentos.
- [x] Killer Moves.
- [x] History Heuristic.
- [x] Métricas de busca.
- [x] Benchmarks comparativos.
- [x] Self-play automatizado.
- [x] Interface visual de self-play.
- [x] Testes de validação e estabilidade funcional.

### Etapa 3 — Evolução da avaliação

- [x] Tabelas peça-casa por tipo de peça e fase da partida.
- [x] Segurança do rei.
- [x] Estrutura de peões.
- [x] Mobilidade e atividade das peças.
- [x] Avaliação adaptativa por fase da partida.
- [x] Testes posicionais, táticos e de simetria.
- [x] Comparação reproduzível entre avaliações.

### Etapa 4 — Preparação competitiva

- [ ] Interface adequada para jogar com brancas ou pretas.
- [ ] Entrada confiável dos movimentos do adversário.
- [ ] Gerenciamento do tempo restante da partida.
- [ ] Recuperação de estado após interrupções, quando permitida.
- [ ] Testes prolongados de estabilidade.
- [x] Integração visual local com Stockfish 19.
- [x] Execução de baterias automatizadas contra Stockfish.
- [x] Comparação entre estratégias de ordenação.
- [ ] Séries competitivas com amostras maiores.
- [ ] Testes contra Stockfish com 3 segundos por lance.
- [ ] Avaliação robusta da força de jogo.
- [ ] Validação de funcionamento totalmente offline.
- [ ] Verificação de conformidade com o regulamento.

### Etapa 5 — Integração opcional de IA

- [ ] Investigar modelos compatíveis com o hardware disponível.
- [ ] Definir contrato para avaliação neural ou política de movimentos.
- [ ] Implementar carregamento e inferência local.
- [ ] Comparar o motor heurístico com uma versão híbrida.
- [ ] Medir consumo de memória e desempenho.
- [ ] Manter apenas melhorias com benefícios demonstrados.

A integração de IA é opcional. O objetivo principal permanece o desenvolvimento de um motor autoral, confiável e progressivamente mais competitivo.

## 11. Requisitos do campeonato

O projeto está sendo desenvolvido para o **Chess Challenge III — ICEV 2026**.

Entre os requisitos relevantes estão:

- Execução local durante as partidas.
- Ausência de dependência de serviços online durante o jogo.
- Escolha autônoma dos movimentos.
- Registro dos movimentos realizados pelo adversário.
- Cada jogador dispõe de 25 minutos para a partida.
- Os jogadores operam o relógio e movem as peças no tabuleiro físico.
- O edital prevê envio do software por Git até 04/11/2026.
- A realização do evento está prevista para 06/11/2026.
- Entrega e validação do código-fonte conforme o regulamento.

O regulamento oficial está publicado em:

[Edital Chess Challenge III — iCEV 2026](https://www.somosicev.com/wp-content/uploads/2026/09/Chess-Challenge-III-1.pdf)

Como o torneio não define segundos fixos por lance, os benchmarks utilizam limites de tempo por busca apenas para manter os experimentos reproduzíveis.

A conformidade operacional completa ainda precisa ser validada.

## 12. Autoria e referências técnicas

Este projeto está sendo desenvolvido como uma implementação independente para o Chess Challenge III.

A equipe estudou conceitos presentes no projeto **Xeque-LFM**, disponibilizado como referência técnica:

https://github.com/xInovatechTecnologia/xeque-lfm

A referência é utilizada para compreender decisões arquiteturais e estratégias gerais de construção de motores de xadrez.

O código deste projeto é desenvolvido independentemente, utilizando algoritmos clássicos amplamente conhecidos, como Negamax e poda Alfa-Beta.

O Stockfish é utilizado como motor adversário externo, exclusivamente para experimentos e avaliação competitiva.

A utilização de bibliotecas e eventuais modelos externos deverá respeitar suas respectivas licenças e condições de uso.

## 13. Próximo objetivo

A próxima etapa do Chess Challenge III é **melhorar a eficiência da busca e aumentar a força competitiva do motor**.

As prioridades são:

1. Investigar os gargalos identificados pelo profiling.
2. Melhorar o aproveitamento da tabela de transposição.
3. Reduzir o custo da busca em posições complexas.
4. Aprimorar o gerenciamento do tempo.
5. Avaliar novas técnicas de busca, como Principal Variation Search e Late Move Reductions, mediante testes controlados.
6. Executar séries de partidas contra Stockfish com 3 segundos por lance para cada motor.
7. Preparar a interface e o controle de tempo para as condições oficiais do campeonato.

**Meta:** entregar um motor de xadrez autoral, estável, executável offline e progressivamente mais competitivo, com decisões independentes e desempenho demonstrado por testes reproduzíveis.
