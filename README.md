# Chess Challenge III — Motor de Xadrez

Motor de xadrez desenvolvido em Python para participação no **Chess Challenge III — ICEV 2026**.

O projeto tem como objetivo construir um motor capaz de analisar posições, pesquisar possibilidades e selecionar movimentos de forma autônoma, com execução local e sem dependência de serviços externos durante as partidas.

A implementação utiliza **Negamax com poda Alfa-Beta, aprofundamento iterativo, busca de quiescência, tabela de transposição e ordenação avançada de movimentos**.

> **Estado atual:** etapas 1 e 2 concluídas. A Etapa 3 está implementada e validada por testes e benchmarks reproduzíveis; 91 testes automatizados passam. Os dados atuais ainda não comprovam aumento de força competitiva. A preparação para operar no formato do torneio está em desenvolvimento.

## 1. Tecnologias utilizadas

| Tecnologia | Finalidade |
|---|---|
| Python 3.14 | Ambiente utilizado no desenvolvimento |
| python-chess | Representação do tabuleiro, regras e movimentos legais |
| pytest | Testes automatizados |
| Tkinter | Interfaces visuais de self-play e ChessEngine vs Stockfish |
| Stockfish 19 (opcional) | Motor adversário externo para partidas locais de avaliação |
| setuptools | Empacotamento e instalação |
| Git e GitHub | Versionamento e colaboração |

O projeto não exige GPU dedicada, banco de dados, Docker, modelos neurais ou conexão com APIs externas.

O Tkinter normalmente acompanha as instalações convencionais do Python no Windows.

## 2. Arquitetura

O motor foi organizado em componentes independentes:
```text
Interface CLI / Self-play / Partidas contra Stockfish

          |

          v

     ChessEngine

          |

          +---- TimeManager

          |

          +---- Iterative Deepening

          |

          v

   Negamax + Alfa-Beta

          |

          +---- Ordenação de movimentos

          |       |

          |       +---- Capturas e promoções

          |       +---- Killer Moves

          |       +---- History Heuristic

          |

          +---- Tabela de transposição

          |       |

          |       +---- Hash Zobrist

          |

          +---- Busca de quiescência

          |

          v

   HeuristicEvaluator

          |

          v

    Melhor movimento
```
O `ChessEngine` coordena a busca, enquanto os módulos especializados implementam a avaliação, a ordenação, o cache e o controle de tempo.

A separação entre avaliação e busca permite aprimorar a função heurística ou integrar novos avaliadores sem reescrever o algoritmo principal.

### Estrutura do projeto
```text
Chess Challenge/

├── benchmarks/

│   ├── ordering_benchmark.csv

│   ├── search_benchmark.csv

│   └── self_play.pgn

├── docs/

├── scripts/

│   ├── benchmark_ordering.py

│   ├── benchmark_search.py

│   ├── self_play.py

│   └── self_play_visual.py

├── src/

│   └── chess_engine/

│       ├── evaluation/

│       │   ├── __init__.py

│       │   ├── base.py

│       │   └── heuristic.py

│       ├── models/

│       │   ├── __init__.py

│       │   └── loader.py

│       ├── search/

│       │   ├── __init__.py

│       │   ├── metrics.py

│       │   ├── move_ordering.py

│       │   ├── negamax.py

│       │   ├── quiescence.py

│       │   └── transposition.py

│       ├── utils/

│       │   ├── __init__.py

│       │   └── time_manager.py

│       ├── __init__.py

│       ├── board.py

│       └── engine.py

├── tests/

│   ├── __init__.py

│   ├── test_board.py

│   ├── test_engine.py

│   ├── test_evaluation.py

│   ├── test_final_validation.py

│   ├── test_metrics.py

│   ├── test_move_ordering_advanced.py

│   ├── test_search.py

│   ├── test_self_play.py

│   ├── test_transposition.py

│   └── test_transposition_key.py

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

O contrato `PositionEvaluator` define a interface para avaliação de posições.

A implementação `HeuristicEvaluator` considera material, tabelas peça-casa geradas por fórmulas simples e critérios posicionais. As tabelas mudam conforme a fase da partida: o rei é mantido mais protegido no meio-jogo e recebe incentivo para centralizar no final.

| Peça | Valor em centipeões |
|---|---:|
| Peão | 100 |
| Cavalo | 320 |
| Bispo | 330 |
| Torre | 500 |
| Dama | 900 |
| Rei | 0 |

A pontuação é positiva para vantagem das brancas e negativa para vantagem das pretas.

Também são considerados:

- Segurança do rei por proteção de peões e pressão sobre casas próximas.

- Estrutura de peões, com penalidades para peões dobrados e isolados e bônus para peões passados.

- Mobilidade de cavalos, bispos, torres e damas, limitada para evitar pontuações exageradas.

- Atividade por centralização, avanço de peões e presença de torres na sétima fileira.

Os pesos são heurísticas iniciais, não valores calibrados por partidas em larga escala. A avaliação ainda não modela profundamente finais, peões atrasados, casas fracas ou planos estratégicos.

### 3.3. Negamax com poda Alfa-Beta

**Arquivo:** `src/chess_engine/search/negamax.py`

O Negamax pesquisa continuações possíveis, alternando a perspectiva entre os jogadores.

A poda Alfa-Beta evita explorar ramos que não podem melhorar o resultado da busca.

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

A quiescência reduz o efeito horizonte, evitando encerrar imediatamente a avaliação em determinadas posições taticamente instáveis.

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

### 3.7. Aprofundamento iterativo

**Arquivo:** `src/chess_engine/engine.py`

O `ChessEngine` pesquisa profundidades progressivas:
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

Também são disponibilizadas estatísticas de consultas e acertos da tabela de transposição.

Essas informações permitem comparar configurações do motor e acompanhar sua evolução.

### 3.10. Preparação para modelos de IA

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
git clone https\://github.com/Ik7Mt0s/Chess-Challenge.git

cd Chess-Challenge
```
### 4.3. Criar o ambiente virtual

No Windows:
```powershell
py -3.14 -m venv .venv

..venv\Scripts\Activate.ps1
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

São aceitos movimentos em SAN ou UCI, por exemplo:
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
python scripts/self_play.py --depth 3 --time 1 --max-plies 1000
```
O script coloca duas instâncias do motor para jogar entre si.

Durante a execução, apresenta:

- Movimento realizado.

- Profundidade concluída.

- Avaliação.

- Tempo utilizado.

Ao final, informa o resultado e salva a partida em formato PGN.

### 4.8. Self-play visual
```powershell
python scripts/self_play_visual.py --depth 3 --time 1
```
A interface utiliza Tkinter para apresentar a partida em um tabuleiro gráfico.

Funcionalidades:

- Iniciar e continuar a partida.

- Pausar.

- Executar um lance por vez.

- Reiniciar.

- Ajustar o intervalo visual entre movimentos.

- Acompanhar o histórico.

- Consultar profundidade, avaliação e tempo.

- Exportar a partida em PGN.

As buscas são executadas em threads separadas para manter a interface responsiva.

A interface visual é destinada ao acompanhamento de partidas entre bots, não à operação em partidas oficiais do campeonato.

### 4.9. Partidas locais contra o Stockfish 19

**Arquivo:** `scripts/stockfish_match_visual.py`

O projeto permite colocar o `ChessEngine` para enfrentar o **Stockfish 19**, um motor de xadrez externo, por meio de uma interface visual em Tkinter. A comunicação é feita pelo protocolo **UCI (Universal Chess Interface)**, usando `chess.engine` do `python-chess`, já incluído nas dependências.

Essa funcionalidade é destinada a **testes e comparação de desempenho**. O Stockfish calcula exclusivamente seus próprios lances; o `ChessEngine` continua utilizando sua implementação independente de Negamax, Alfa-Beta, quiescência e avaliação heurística. **O Stockfish não é uma rede neural integrada ao nosso motor.** As partidas funcionam localmente, sem API ou conexão com a internet após a instalação.

#### Instalação do Stockfish no Windows

1. Baixe o executável adequado ao seu processador em [stockfishchess.org/download](https://stockfishchess.org/download/).
2. Extraia o arquivo na pasta `engines/stockfish/` do projeto.
3. Na configuração utilizada durante o desenvolvimento, o executável é `engines/stockfish/stockfish-windows-x86-64-universal.exe`.
4. Para conferir a instalação, execute no PowerShell, a partir da raiz do projeto:
```powershell
& ".\engines\stockfish\stockfish-windows-x86-64-universal.exe"
```
No console do Stockfish, digite `uci`. A resposta deve conter `uciok`. Para encerrar, digite `quit`.

> O executável do Stockfish **não é instalado pelo `pip`** e deve ser baixado separadamente. Recomenda-se incluir `/engines/stockfish/` no `.gitignore`, evitando versionar binários externos.

#### Iniciar uma partida

Com o ambiente virtual ativado, execute na raiz do repositório:
```powershell
python scripts/stockfish_match_visual.py --depth 3 --our-time 1 --stockfish-time 0.1 --elo 1320 --our-color white
```
Esse comando coloca nosso motor de **brancas**, com profundidade máxima 3 e até 1 segundo de busca por lance, contra o Stockfish configurado para **1320 Elo** e 0,1 segundo de busca por lance.

Para jogar com as **pretas**:
```powershell
python scripts/stockfish_match_visual.py --depth 3 --our-time 1 --stockfish-time 0.1 --elo 1320 --our-color black
```
Para aumentar a dificuldade do adversário:
```powershell
python scripts/stockfish_match_visual.py --depth 3 --our-time 1 --stockfish-time 0.1 --elo 1800 --our-color white
```
#### Parâmetros disponíveis

| Parâmetro | Padrão | Descrição |
|---|---:|---|
| `--stockfish` | `engines/stockfish/stockfish-windows-x86-64-universal.exe` | Caminho do executável do Stockfish |
| `--depth` | `3` | Profundidade máxima de busca do nosso `ChessEngine` |
| `--our-time` | `1.0` | Limite de tempo por lance do nosso motor, em segundos |
| `--stockfish-time` | `0.1` | Tempo de busca do Stockfish por lance, em segundos |
| `--elo` | `1320` | Força-alvo configurada do Stockfish, de `1320` a `3190` |
| `--our-color` | `white` | Cor do nosso motor: `white` ou `black` |
| `--max-plies` | `300` | Limite de meios-lances antes de encerrar como inconclusiva |

O script configura o Stockfish com `UCI_LimitStrength=True` e `UCI_Elo` para reduzir sua força. O Elo é um **alvo de configuração**, não uma classificação medida ou garantida. O parâmetro `--depth` afeta apenas o nosso motor. O Stockfish utiliza uma thread e 16 MB de hash por padrão nessa integração, para reduzir o consumo de recursos.

Para usar outro executável ou uma instalação em outro diretório, informe `--stockfish` com o caminho correspondente.

#### Controles da interface

- **Iniciar / Continuar:** executa automaticamente os próximos lances.
- **Pausar:** impede a aplicação de novos lances até continuar; a busca já iniciada pode terminar em segundo plano.
- **Próximo lance:** avança uma jogada por vez.
- **Reiniciar:** inicia outra partida quando não houver busca em andamento.
- **Salvar PGN:** exporta a partida para análise posterior, com sugestão de destino na pasta `benchmarks/`.
- **Intervalo entre movimentos:** ajusta a velocidade de apresentação dos lances.

A interface exibe o tabuleiro, histórico de movimentos, tempo de execução, informações da busca do nosso motor e resultado final. Caso o limite de meios-lances seja alcançado sem término pelas regras do xadrez, a partida é **inconclusiva**, não um empate.

**Limitações atuais:** o Stockfish é iniciado como processo separado a cada lance dele, o que acrescenta tempo de inicialização. A dificuldade é definida na linha de comando e, para alterá-la, é necessário reiniciar o script. O tempo informado é um orçamento por lance, não um relógio completo de competição. Os confrontos contra o Stockfish ainda não constituem uma medição robusta da força do nosso motor; para isso, serão necessárias várias partidas com cores alternadas e condições controladas.

## 5. Testes automatizados

O projeto utiliza `pytest`.

Para executar todos os testes:
```powershell
python -m pytest -v
```
Para executar somente a validação final:
```powershell
python -m pytest tests/test_final_validation.py -v
```
**Última validação: 91 testes aprovados em 31/10/2026.**

Os testes abrangem:

- Gerenciamento do tabuleiro.

- Avaliação heurística.

- Busca Negamax.

- Quiescência e posições terminais.

- Controle de tempo e timeout.

- Tabela de transposição.

- Chaves e histórico de posições.

- Ordenação avançada.

- Métricas de busca.

- Integridade do estado do tabuleiro.

- Consistência entre configurações.

- Self-play.

Os testes validam comportamentos importantes, mas não comprovam força competitiva ou ausência de todos os possíveis defeitos.

## 6. Benchmarks e resultados

Os scripts de benchmark permitem comparar configurações do motor em posições de abertura, meio-jogo e final.

### 6.1. Tabela de transposição

Executar:
```powershell
python scripts/benchmark_search.py
```
Resultados registrados, com profundidade 3:

| Posição | Sem cache | Com cache | Redução de nós |
|---|---:|---:|---:|
| Abertura | 1.628 | 1.207 | 25,9% |
| Meio-jogo | 23.843 | 12.896 | 45,9% |
| Final | 1.027 | 905 | 11,9% |

Os resultados estão registrados em `benchmarks/search_benchmark.csv`.

### 6.2. Ordenação avançada

Executar:
```powershell
python scripts/benchmark_ordering.py --depth 3 --time 30 --repetitions 3
```
Resultados registrados:

| Posição | Ordenação original | Avançada | Redução de nós |
|---|---:|---:|---:|
| Abertura | 1.207 | 1.143 | 5,3% |
| Meio-jogo | 12.896 | 8.350 | 35,3% |
| Final | 905 | 391 | 56,8% |

Tempos medianos das três repetições:

| Posição | Original | Avançada |
|---|---:|---:|
| Abertura | 0,794 s | 0,603 s |
| Meio-jogo | 6,246 s | 4,686 s |
| Final | 0,161 s | 0,086 s |

As configurações mantiveram os mesmos movimentos e avaliações nas três posições testadas.

Os resultados estão registrados em `benchmarks/ordering_benchmark.csv`.

Esses benchmarks demonstram ganhos de eficiência nas posições avaliadas. Não representam, isoladamente, um aumento comprovado de força competitiva.

### 6.3. Comparação da avaliação

O benchmark mede o custo da avaliação e compara o lance escolhido pela versão anterior e pela Etapa 3 em quatro posições. Para reproduzir a execução registrada:
```powershell
python scripts/benchmark_evaluation.py --depth 3 --time 10 --evaluation-repetitions 300 --repetitions 3 --output benchmarks/evaluation_competition_performance_10s.csv
```
Nas quatro posições, as duas versões escolheram o mesmo lance e concluíram a profundidade 3. O rendimento abaixo é a mediana de três repetições:

| Posição | Lance | Avaliações/s anterior | Avaliações/s Etapa 3 | Profundidade concluída (anterior / Etapa 3) |
|---|---|---:|---:|---:|
| Abertura | Nf3 | 31.859,0 | 10.072,5 | 3 / 3 |
| Meio-jogo | d4 | 32.872,0 | 12.596,3 | 3 / 3 |
| Final | f4 | 77.806,9 | 51.584,5 | 3 / 3 |
| Peão passado | e7 | 95.721,3 | 70.928,7 | 3 / 3 |

O throughput da avaliação da Etapa 3 foi menor nas quatro posições: aproximadamente 68% na abertura, 62% no meio-jogo, 34% no final e 26% na posição com peão passado. Com 10 segundos disponíveis, as duas versões concluíram profundidade 3 no meio-jogo; nessa posição, a busca levou medianas de 4,25 s e 4,87 s, respectivamente. As escolhas iguais nesta amostra não provam força equivalente. Os tempos, nós, pontuações e resultados completos ficam em `benchmarks/evaluation_competition_performance_10s.csv`.

### 6.4. Partidas pareadas e ablações da avaliação

As partidas usam o mesmo motor de busca e limite de tempo para as duas versões, alternam as cores em cada par e atribuem a diferença à avaliação. Para reproduzir os confrontos:
```powershell
python scripts/benchmark_evaluation_matches.py --opponents baseline --pairs 2 --depth 3 --time 3 --max-plies 60 --csv-output benchmarks/evaluation_competition_baseline.csv --pgn-output benchmarks/evaluation_competition_baseline.pgn

python scripts/benchmark_evaluation_matches.py --opponents no_mobility no_pawn_structure no_king_safety --pairs 1 --depth 3 --time 3 --max-plies 60 --csv-output benchmarks/evaluation_competition_ablations.csv --pgn-output benchmarks/evaluation_competition_ablations.pgn
```
O avaliador completo enfrentou a avaliação anterior em duas aberturas, com as cores invertidas: uma vitória e três partidas que chegaram ao limite de 60 meios-lances. Nas ablações, contra a avaliação completa, a versão sem mobilidade teve uma derrota e uma partida inconclusiva; sem estrutura de peões, duas inconclusivas; sem segurança do rei, duas inconclusivas. Não houve amostra suficiente para estimar força, declarar superioridade ou recalibrar os pesos. Os CSVs contêm profundidade, nós, tempo, cor e motivo de término; os PGNs guardam as partidas. Partidas inconclusivas não contam como empate.

O `--time 3` é um limite fixo por busca usado para comparação controlada, não uma reprodução do relógio oficial. O limite de 60 meios-lances reduz a duração do experimento e também causa partidas inconclusivas; os dados devem ser usados como diagnóstico, não como rating competitivo.

### 6.5. Self-play

Uma execução recente utilizou:
```powershell
python scripts/self_play.py --depth 3 --time 1 --max-plies 1000
```
Resultado observado:

| Métrica | Resultado |
|---|---|
| Resultado | 1-0 |
| Encerramento | Xeque-mate |
| Meios-lances | 111 |
| Tempo total | 88,55 s |
| Profundidade máxima | 3 |

A partida incluiu capturas, promoção de peão e encerramento por xeque-mate.

O PGN está disponível em `benchmarks/self_play.pgn`.

## 7. Limitações conhecidas

Apesar das melhorias, o motor ainda possui limitações relevantes:

1. **Avaliação estratégica ainda simples:** os novos critérios são heurísticas iniciais e precisam ser calibrados em posições e partidas diversas.

2. **Profundidade limitada:** posições complexas podem consumir todo o tempo disponível antes de atingir a profundidade máxima.

3. **Busca em Python:** o custo computacional limita a quantidade de posições pesquisadas por segundo.

4. **Controle de tempo da partida:** ainda não existe gerenciamento completo do relógio oficial de 25 minutos por jogador. O benchmark atual impõe um limite fixo a cada busca.

5. **Interface competitiva pendente:** a interface visual atual serve ao self-play, não à entrada e execução de lances em partidas oficiais.

6. **Sem avaliação neural:** nenhum modelo de aprendizado de máquina participa atualmente das decisões.

7. **Força competitiva sem medição robusta:** os confrontos internos desta etapa tiveram poucas partidas decisivas. Ainda faltam partidas contra motores de referência e conjuntos padronizados de posições táticas.

8. **Quiescência e desempenho:** ainda existem oportunidades de otimização em posições táticas complexas.

## 8. Roadmap de desenvolvimento

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

- [x] Segurança do rei por abrigo de peões e pressão nas casas vizinhas.

- [x] Estrutura de peões dobrados, isolados e passados.

- [x] Mobilidade e atividade das peças.

- [x] Avaliação adaptativa por fase da partida.

- [x] Testes posicionais, táticos e de simetria.

- [x] Comparação reproduzível entre a avaliação anterior e a atual.

### Etapa 4 — Preparação competitiva

- [ ] Interface adequada para jogar com brancas ou pretas.

- [ ] Entrada confiável dos movimentos do adversário.

- [ ] Gerenciamento do tempo restante da partida.

- [ ] Recuperação de estado após interrupções, quando permitida.

- [ ] Testes prolongados de estabilidade.

- [x] Integração visual local para partidas contra Stockfish 19.
- [ ] Realizar séries controladas de partidas contra motores de referência.

- [ ] Avaliação de força de jogo.

- [ ] Validação de funcionamento totalmente offline.

- [ ] Verificação de conformidade com o regulamento.

### Etapa 5 — Integração opcional de IA

- [ ] Investigar modelos compatíveis com o hardware disponível.

- [ ] Definir contrato para avaliação neural ou política de movimentos.

- [ ] Implementar carregamento e inferência local.

- [ ] Comparar o motor heurístico com uma versão híbrida.

- [ ] Medir consumo de memória, tempo por posição e desempenho.

- [ ] Manter apenas melhorias com benefícios demonstrados.

A integração de IA é opcional. O objetivo principal permanece o desenvolvimento de um motor autoral, confiável e progressivamente mais competitivo.

## 9. Requisitos do campeonato

O projeto está sendo desenvolvido para o Chess Challenge III — ICEV 2026.

Entre os requisitos relevantes estão:

- Execução local durante as partidas.

- Ausência de dependência de serviços online durante o jogo.

- Escolha autônoma dos movimentos.

- Registro dos movimentos realizados pelo adversário.

- Cada jogador dispõe de 25 minutos para a partida; os jogadores operam o relógio e movem as peças no tabuleiro físico.

- O edital prevê envio do software por Git até 04/11/2026 e realização do evento em 06/11/2026.

- Entrega e validação do código-fonte conforme o regulamento.

O regulamento oficial está publicado em [Edital Chess Challenge III — iCEV 2026](https\://www.somosicev.com/wp-content/uploads/2026/09/Chess-Challenge-III-1.pdf). Como o torneio não define segundos por lance, o benchmark de avaliação usa um limite fixo por busca apenas para manter as versões sob o mesmo orçamento. A conformidade operacional completa ainda precisa ser validada na Etapa 4.

## 10. Autoria e referências técnicas

Este projeto está sendo desenvolvido como uma implementação independente para o Chess Challenge III.

A equipe estudou conceitos presentes no projeto **Xeque-LFM**, disponibilizado como referência técnica:

https\://github.com/xInovatechTecnologia/xeque-lfm

A referência é utilizada para compreender decisões arquiteturais e estratégias gerais de construção de motores de xadrez.

O código deste projeto é desenvolvido independentemente, utilizando algoritmos clássicos amplamente conhecidos, como Negamax e poda Alfa-Beta.

A utilização de bibliotecas e eventuais modelos externos deverá respeitar suas respectivas licenças e condições de uso.

## 11. Próximo objetivo

A Etapa 3 está concluída como implementação e validação inicial. Os benchmarks não demonstraram evidência suficiente para alterar os pesos nem provar ganho competitivo; uma calibração mais ampla pode ser feita se surgirem mais posições e jogos de referência. O próximo trabalho é avançar para a **Etapa 4 — Preparação competitiva**: implementar a interface de operação, integrar o registro de lances adversários para o torneio, gerenciar o relógio da partida e realizar séries controladas de partidas contra o Stockfish.

**Meta:** entregar um motor autoral, estável, executável offline e preparado para a operação real do campeonato.
