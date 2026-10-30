# Chess Challenge III — Motor de Xadrez

Motor de xadrez desenvolvido em Python para participação no **Chess Challenge III — ICEV 2026**.

O projeto tem como objetivo construir um motor capaz de analisar posições, pesquisar possibilidades e selecionar movimentos de forma autônoma, com execução local e sem dependência de serviços externos durante as partidas.

A implementação utiliza **Negamax com poda Alfa-Beta, aprofundamento iterativo, busca de quiescência, tabela de transposição e ordenação avançada de movimentos**.

> **Estado atual:** motor funcional, com a etapa de otimização da busca concluída, 82 testes automatizados aprovados, benchmarks registrados e partidas completas de self-play. A preparação competitiva ainda está em desenvolvimento.

## 1. Tecnologias utilizadas

| Tecnologia | Finalidade |
|---|---|
| Python 3.14 | Ambiente utilizado no desenvolvimento |
| python-chess | Representação do tabuleiro, regras e movimentos legais |
| pytest | Testes automatizados |
| Tkinter | Interface visual para self-play |
| setuptools | Empacotamento e instalação |
| Git e GitHub | Versionamento e colaboração |

O projeto não exige GPU dedicada, banco de dados, Docker, modelos neurais ou conexão com APIs externas.

O Tkinter normalmente acompanha as instalações convencionais do Python no Windows.

## 2. Arquitetura

O motor foi organizado em componentes independentes:

```text
Interface CLI / Self-play
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
          |       |
          |       +---- Capturas e promoções
          |       +---- Killer Moves
          |       +---- History Heuristic
          |
          +---- Tabela de transposição
          |       |
          |       +---- Hash Zobrist
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
│   ├── ordering_benchmark.csv
│   ├── search_benchmark.csv
│   └── self_play.pgn
├── docs/
├── scripts/
│   ├── benchmark_ordering.py
│   ├── benchmark_search.py
│   ├── self_play.py
│   └── self_play_visual.py
├── src/
│   └── chess_engine/
│       ├── evaluation/
│       │   ├── __init__.py
│       │   ├── base.py
│       │   └── heuristic.py
│       ├── models/
│       │   ├── __init__.py
│       │   └── loader.py
│       ├── search/
│       │   ├── __init__.py
│       │   ├── metrics.py
│       │   ├── move_ordering.py
│       │   ├── negamax.py
│       │   ├── quiescence.py
│       │   └── transposition.py
│       ├── utils/
│       │   ├── __init__.py
│       │   └── time_manager.py
│       ├── __init__.py
│       ├── board.py
│       └── engine.py
├── tests/
│   ├── __init__.py
│   ├── test_board.py
│   ├── test_engine.py
│   ├── test_evaluation.py
│   ├── test_final_validation.py
│   ├── test_metrics.py
│   ├── test_move_ordering_advanced.py
│   ├── test_search.py
│   ├── test_self_play.py
│   ├── test_transposition.py
│   └── test_transposition_key.py
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

A implementação `HeuristicEvaluator` considera o material e alguns critérios posicionais, incluindo centralização de cavalos e bispos e avanço de peões.

| Peça | Valor em centipeões |
|---|---:|
| Peão | 100 |
| Cavalo | 320 |
| Bispo | 330 |
| Torre | 500 |
| Dama | 900 |
| Rei | 0 |

A pontuação é positiva para vantagem das brancas e negativa para vantagem das pretas.

A avaliação ainda não contempla de forma abrangente segurança do rei, mobilidade, estrutura de peões ou planejamento estratégico.

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

**Última validação informada: 82 testes aprovados.**

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

### 6.3. Self-play

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

1. **Avaliação estratégica simplificada:** faltam critérios mais completos de mobilidade, segurança do rei, estrutura de peões e fase da partida.
2. **Profundidade limitada:** posições complexas podem consumir todo o tempo disponível antes de atingir a profundidade máxima.
3. **Busca em Python:** o custo computacional limita a quantidade de posições pesquisadas por segundo.
4. **Controle de tempo por movimento:** ainda não existe gerenciamento completo do relógio de uma partida oficial.
5. **Interface competitiva pendente:** a interface visual atual serve ao self-play, não à entrada e execução de lances em partidas oficiais.
6. **Sem avaliação neural:** nenhum modelo de aprendizado de máquina participa atualmente das decisões.
7. **Força competitiva não medida:** ainda faltam partidas comparativas contra motores de referência e conjuntos padronizados de posições táticas.
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

- [ ] Tabelas peça-casa mais completas.
- [ ] Segurança do rei.
- [ ] Estrutura de peões.
- [ ] Mobilidade e atividade das peças.
- [ ] Avaliação adaptativa por fase da partida.
- [ ] Testes posicionais e táticos.
- [ ] Comparação de desempenho entre versões do avaliador.

### Etapa 4 — Preparação competitiva

- [ ] Interface adequada para jogar com brancas ou pretas.
- [ ] Entrada confiável dos movimentos do adversário.
- [ ] Gerenciamento do tempo restante da partida.
- [ ] Recuperação de estado após interrupções, quando permitida.
- [ ] Testes prolongados de estabilidade.
- [ ] Partidas contra motores de referência.
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
- Respeito ao tempo disponível.
- Entrega e validação do código-fonte conforme o regulamento.

A arquitetura foi projetada para execução local, mas a conformidade completa com o regulamento ainda precisa ser validada.

## 10. Autoria e referências técnicas

Este projeto está sendo desenvolvido como uma implementação independente para o Chess Challenge III.

A equipe estudou conceitos presentes no projeto **Xeque-LFM**, disponibilizado como referência técnica:

https://github.com/xInovatechTecnologia/xeque-lfm

A referência é utilizada para compreender decisões arquiteturais e estratégias gerais de construção de motores de xadrez.

O código deste projeto é desenvolvido independentemente, utilizando algoritmos clássicos amplamente conhecidos, como Negamax e poda Alfa-Beta.

A utilização de bibliotecas e eventuais modelos externos deverá respeitar suas respectivas licenças e condições de uso.

## 11. Próximo objetivo

A próxima etapa concentra-se na **qualidade da avaliação das posições**.

Após otimizar a busca, o objetivo é melhorar a capacidade do motor de identificar vantagens estratégicas, antecipar ameaças e selecionar movimentos mais fortes.

As prioridades são:

1. Avaliação posicional.
2. Segurança do rei e estrutura de peões.
3. Mobilidade e atividade das peças.
4. Testes táticos e comparações entre versões.

**Meta:** desenvolver um motor de xadrez funcional, autoral, executável offline e progressivamente mais competitivo, mantendo baixo consumo de recursos computacionais.
