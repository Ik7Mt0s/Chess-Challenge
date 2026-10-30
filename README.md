# Chess Challenge III — Motor de Xadrez

Motor de xadrez desenvolvido em Python para participação no **Chess Challenge III — ICEV 2026**.

O projeto tem como objetivo desenvolver um motor capaz de analisar posições, explorar possibilidades e selecionar movimentos de xadrez de forma autônoma, com execução local e sem dependência de serviços externos durante as partidas.

Atualmente, o motor utiliza **Negamax com poda Alfa-Beta, avaliação heurística de material e aprofundamento iterativo**. A arquitetura foi organizada para permitir melhorias nos algoritmos de busca e avaliação, além de uma possível integração futura com modelos de inteligência artificial.

> **Estado atual:** versão inicial funcional (v0.1.0). O motor já consegue selecionar movimentos legais e jogar partidas pelo terminal, mas ainda não está otimizado ou validado para uso competitivo.

## 1. Tecnologias utilizadas

| Tecnologia | Finalidade |
|---|---|
| Python 3.14 | Ambiente utilizado no desenvolvimento inicial |
| python-chess | Representação do tabuleiro, regras e validação de movimentos |
| pytest | Testes automatizados |
| setuptools | Empacotamento e instalação do projeto |
| Git e GitHub | Versionamento e colaboração |

O projeto não exige GPU dedicada, modelos GGUF, banco de dados, Docker ou conexão com APIs externas.

## 2. Arquitetura

O motor está dividido em componentes independentes:

```text
Entrada do jogador / posição
              |
              v
       ChessBoard
       (python-chess)
              |
              v
        ChessEngine
              |
              v
    Busca Negamax + Alfa-Beta
              |
       +------+------+
       |             |
       v             v
 Ordenação       Avaliação
 de jogadas      heurística
       |             |
       +------+------+
              |
              v
     Melhor movimento
              |
              v
       Interface CLI
```

A lógica de avaliação está separada da busca. Isso permite substituir ou complementar o avaliador heurístico sem reconstruir toda a aplicação.

### Estrutura do projeto

```text
Chess Challenge/
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
│       │   ├── move_ordering.py
│       │   └── negamax.py
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
│   └── test_search.py
├── benchmarks/
├── docs/
├── scripts/
├── main.py
├── pyproject.toml
├── requirements.txt
├── .gitignore
└── README.md
```

## 3. Funcionalidades implementadas

### 3.1. Gerenciamento do tabuleiro

**Arquivo:** `src/chess_engine/board.py`

A classe `ChessBoard` encapsula o `python-chess` e oferece operações para:

- Inicializar uma partida na posição padrão ou a partir de uma FEN.
- Listar movimentos legais.
- Executar movimentos em notação SAN ou UCI.
- Desfazer movimentos.
- Reiniciar o tabuleiro.
- Consultar a posição atual em FEN.
- Identificar o encerramento da partida e consultar seu resultado.

O projeto utiliza o `python-chess` para implementar as regras oficiais, incluindo roque, promoção, en passant, xeque e xeque-mate.

### 3.2. Avaliação heurística

**Arquivos:**
- `src/chess_engine/evaluation/base.py`
- `src/chess_engine/evaluation/heuristic.py`

O contrato `PositionEvaluator` estabelece que um avaliador recebe um tabuleiro e retorna uma pontuação inteira.

Na implementação atual:

- Pontuação positiva indica vantagem das brancas.
- Pontuação negativa indica vantagem das pretas.
- A pontuação é expressa em centipeões.

Valores materiais utilizados:

| Peça | Valor |
|---|---:|
| Peão | 100 |
| Cavalo | 320 |
| Bispo | 330 |
| Torre | 500 |
| Dama | 900 |
| Rei | 0 |

A avaliação é calculada pela diferença entre o material das brancas e o das pretas.

**Limitação:** a avaliação atual não considera diretamente atividade das peças, segurança do rei, estrutura de peões, mobilidade ou vantagens posicionais.

### 3.3. Negamax com poda Alfa-Beta

**Arquivo:** `src/chess_engine/search/negamax.py`

O Negamax é uma variante do Minimax utilizada em jogos de soma zero.

O algoritmo explora movimentos possíveis, alternando a perspectiva entre os jogadores. A poda Alfa-Beta reduz a exploração de ramos que não podem melhorar a decisão encontrada até aquele momento.

A implementação atual inclui:

- Busca recursiva até uma profundidade definida.
- Poda Alfa-Beta.
- Avaliação de posições nas folhas da busca.
- Reconhecimento de xeque-mate.
- Tratamento de posições empatadas.
- Verificação cooperativa do limite de tempo.
- Restauração do tabuleiro após explorar cada movimento.

**Limitação:** a busca ainda não utiliza quiescência, tabela de transposição ou técnicas avançadas de redução de profundidade.

### 3.4. Ordenação de movimentos

**Arquivo:** `src/chess_engine/search/move_ordering.py`

Antes de explorar os movimentos, o motor atribui prioridades com base em características simples:

- Capturas.
- Valor da peça capturada e da peça atacante.
- Promoções.
- Movimentos que dão xeque.

Os movimentos são ordenados para que alternativas potencialmente relevantes sejam analisadas primeiro.

Essa ordenação melhora a oportunidade de realizar podas Alfa-Beta, mas não garante que os primeiros movimentos sejam os melhores.

Nenhum movimento legal é descartado exclusivamente pela ordenação.

### 3.5. Aprofundamento iterativo

**Arquivo:** `src/chess_engine/engine.py`

A classe `ChessEngine` coordena a escolha de movimentos.

O motor realiza buscas progressivas:

```text
Profundidade 1
      |
Profundidade 2
      |
Profundidade 3
      |
     ...
```

O melhor movimento encontrado em uma profundidade concluída é preservado.

Se o limite de tempo for atingido, o motor retorna o melhor resultado disponível de uma iteração concluída ou um movimento legal de reserva.

O resultado da busca é representado pela estrutura `SearchResult`, que contém:

| Campo | Descrição |
|---|---|
| `move` | Movimento selecionado |
| `score` | Pontuação calculada |
| `depth` | Profundidade concluída |
| `elapsed` | Tempo utilizado na busca |

### 3.6. Controle de tempo

**Arquivo:** `src/chess_engine/utils/time_manager.py`

O `TimeManager` utiliza `time.monotonic()` para acompanhar o tempo transcorrido e calcular o prazo final da busca.

A exceção `SearchTimeout` sinaliza quando o limite é atingido.

Atualmente, esse controle limita o tempo de uma busca individual. Ele ainda não gerencia o relógio completo de uma partida de torneio.

### 3.7. Preparação para modelos de IA

**Arquivo:** `src/chess_engine/models/loader.py`

O módulo `ModelLoader` reserva um ponto de integração para modelos externos.

No momento, ele verifica a existência do arquivo informado, mas não carrega nem executa modelos.

**Nenhum modelo neural está integrado ao motor nesta versão.**

A arquitetura poderá ser estendida para utilizar avaliações neurais, políticas de movimentos ou outras estratégias, conforme os resultados dos testes e os recursos computacionais disponíveis.

## 4. Instalação e execução

### 4.1. Pré-requisitos

- Windows, Linux ou macOS.
- Python 3.11 ou superior, conforme a configuração atual do projeto.
- Git.
- Terminal PowerShell, Bash ou equivalente.

O ambiente de desenvolvimento inicial utiliza Python 3.14.

### 4.2. Clonar o repositório

```powershell
git clone https://github.com/Ik7Mt0s/Chess-Challenge.git
cd Chess-Challenge
```

### 4.3. Criar o ambiente virtual

No Windows, com Python 3.14 instalado:

```powershell
py -3.14 -m venv .venv
```

Ativar:

```powershell
.\.venv\Scripts\Activate.ps1
```

No Linux ou macOS:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 4.4. Instalar as dependências

Na raiz do projeto:

```powershell
python -m pip install -e ".[dev]"
```

O modo `editable` permite modificar o código-fonte sem reinstalar o pacote a cada alteração.

O projeto utiliza o `pyproject.toml` como configuração principal de dependências.

### 4.5. Validar a instalação

```powershell
python -c "import chess_engine; print('Motor configurado com sucesso!')"
```

### 4.6. Executar o motor

```powershell
python main.py
```

Na interface atual, o usuário joga com as peças brancas e o motor responde com as pretas.

É possível inserir movimentos em SAN ou UCI:

```text
e4
Nf3
O-O
e2e4
g1f3
```

Comandos adicionais:

- `sair`: encerra a execução.
- `desfazer`: desfaz um turno completo, quando disponível.

O terminal apresenta o tabuleiro e, após cada jogada do motor, informa o movimento escolhido, a profundidade concluída, a avaliação e o tempo utilizado.

**Importante:** a interface atual é uma demonstração local. Ainda não possui a operação completa necessária para partidas físicas com escolha de cor e controle do relógio oficial.

## 5. Testes automatizados

O projeto utiliza `pytest`.

Para executar todos os testes:

```powershell
python -m pytest -v
```

Para executar um arquivo específico:

```powershell
python -m pytest tests/test_engine.py -v
```

### Cobertura funcional atual

| Arquivo | Validações |
|---|---|
| `test_board.py` | Posição inicial, movimentos SAN/UCI, movimentos ilegais, desfazer e xeque-mate |
| `test_evaluation.py` | Equilíbrio material, vantagens de material e preservação do tabuleiro |
| `test_search.py` | Avaliação inicial, preservação da posição, xeque-mate e afogamento |
| `test_engine.py` | Legalidade do movimento escolhido, preservação da posição, partidas encerradas, profundidade inválida e prazo curto |

Os testes existentes validam comportamentos fundamentais, mas não demonstram força competitiva nem cobrem todas as situações possíveis do xadrez.

Ainda serão necessários testes mais extensos de regras, táticas, desempenho e confiabilidade.

## 6. Limitações conhecidas

A versão atual é um protótipo funcional, com limitações importantes:

1. **Avaliação apenas material:** não identifica adequadamente muitas vantagens posicionais e ameaças estratégicas.
2. **Ausência de busca de quiescência:** a avaliação pode ocorrer durante sequências táticas ainda não resolvidas.
3. **Ausência de tabela de transposição:** posições equivalentes podem ser pesquisadas repetidamente.
4. **Ordenação básica:** não utiliza histórico de jogadas, killer moves ou análise mais sofisticada de capturas.
5. **Profundidade limitada:** o custo computacional aumenta rapidamente conforme a profundidade da busca.
6. **Controle de tempo simplificado:** não considera automaticamente o tempo restante no relógio oficial.
7. **Interface limitada:** o modo de demonstração permite jogar apenas com as brancas.
8. **Sem avaliação neural:** o módulo de modelos ainda é apenas uma estrutura para integração futura.
9. **Sem benchmarks competitivos registrados:** ainda não existem resultados suficientes para estimar a força do motor.

## 7. Roadmap de desenvolvimento

### Fase 1 — Fundação do projeto

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

### Fase 2 — Melhorias do motor

- [ ] Avaliação posicional com tabelas peça-casa.
- [ ] Segurança do rei e estrutura de peões.
- [ ] Avaliação adaptativa por fase da partida.
- [ ] Busca de quiescência.
- [ ] Tabela de transposição.
- [ ] Melhorias na ordenação de movimentos.
- [ ] Tratamento estratégico de empates reivindicáveis.
- [ ] Otimização do desempenho em CPU.

### Fase 3 — Preparação competitiva

- [ ] Interface adequada para jogar com brancas ou pretas.
- [ ] Entrada confiável dos movimentos do adversário.
- [ ] Gerenciamento do tempo restante da partida.
- [ ] Recuperação de estado após interrupções, quando permitida.
- [ ] Testes completos de regras especiais e finais.
- [ ] Testes prolongados de estabilidade.
- [ ] Benchmarks em diferentes posições.
- [ ] Partidas de avaliação contra motores de referência.
- [ ] Validação de funcionamento totalmente offline.

### Fase 4 — Integração opcional de IA

- [ ] Investigar modelos compatíveis com o hardware disponível.
- [ ] Definir contrato para avaliação neural ou política de movimentos.
- [ ] Implementar carregamento e inferência local.
- [ ] Comparar o motor heurístico com a versão híbrida.
- [ ] Medir consumo de memória, tempo por posição e desempenho em partidas.
- [ ] Manter apenas melhorias que demonstrem benefícios práticos.

A integração de IA é opcional e dependerá da viabilidade técnica. O objetivo principal é desenvolver um motor confiável e competitivo, não utilizar um modelo neural obrigatoriamente.

## 8. Estratégia de avaliação e benchmarks

A evolução do motor deverá ser acompanhada por medições reproduzíveis.

As principais métricas planejadas são:

| Métrica | Objetivo |
|---|---|
| Tempo por jogada | Verificar se o motor responde dentro do orçamento |
| Nós pesquisados | Medir o volume de posições exploradas |
| Nós por segundo | Avaliar o desempenho da busca |
| Profundidade alcançada | Acompanhar a capacidade de exploração |
| Taxa de vitórias | Comparar versões em partidas |
| Resultados táticos | Verificar resolução de posições de teste |
| Consumo de memória | Garantir execução em computadores modestos |

Sempre que possível, as versões serão comparadas utilizando o mesmo hardware, as mesmas posições e condições equivalentes.

Os diretórios `benchmarks/` e `docs/` foram reservados para os resultados e a documentação dessas análises.

## 9. Requisitos do campeonato

O projeto está sendo desenvolvido para o Chess Challenge III — ICEV 2026.

Entre os requisitos relevantes estão:

- Execução local durante as partidas.
- Ausência de dependência de APIs ou softwares online durante o jogo.
- Escolha autônoma dos movimentos pelo programa.
- Registro dos movimentos realizados pelo adversário.
- Respeito ao tempo disponível.
- Entrega e validação do código-fonte conforme o regulamento.

A arquitetura atual foi projetada para execução local, mas **a conformidade completa com o regulamento ainda precisa ser validada**.

A interface de operação, o controle do relógio e os testes de estabilidade são prioridades antes da competição.

## 10. Autoria e referências técnicas

Este projeto está sendo desenvolvido como uma implementação independente para o Chess Challenge III.

A equipe estudou conceitos presentes no projeto **Xeque-LFM**, disponibilizado por um professor como referência técnica:

https://github.com/xInovatechTecnologia/xeque-lfm

A referência é utilizada para compreender decisões arquiteturais e estratégias gerais de construção de motores de xadrez.

O código deste projeto é desenvolvido independentemente, utilizando algoritmos clássicos amplamente conhecidos, como Negamax e poda Alfa-Beta.

A utilização de bibliotecas e eventuais modelos externos deverá respeitar suas respectivas licenças e condições de uso.

## 11. Próximo objetivo

A prioridade imediata é transformar a implementação inicial em um motor mais confiável e capaz de avaliar posições além da vantagem material.

O próximo ciclo de desenvolvimento deverá concentrar-se em:

1. Avaliação posicional.
2. Busca de quiescência.
3. Testes táticos e de desempenho.
4. Melhorias no gerenciamento de tempo.

**Meta:** obter um motor de xadrez funcional, autoral, executável offline e progressivamente mais competitivo, mantendo baixo consumo de recursos computacionais.
