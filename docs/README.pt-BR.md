<h1 align="center">eleph</h1>

<p align="center">
  <strong>Uma linguagem cujos programas não podem mentir.</strong><br>
  Atos de fala, um histórico que é o único estado, e condições de correção
  derivadas do texto do programa em vez de escritas ao lado dele.
</p>

<p align="center">
  <a href="#instalação">Instalação</a> ·
  <a href="#use-a-partir-do-python">API Python</a> ·
  <a href="#medido-contra-um-benchmark-publicado">Benchmark</a> ·
  <a href="#limites-honestos">Limites</a> ·
  Português ·
  <a href="../README.md">English</a> ·
  <a href="README.es.md">Español</a> ·
  <a href="README.zh-CN.md">中文</a>
</p>

---

*Isaac Mello, 2026. Implementa e estende o **Elephant 2000**, uma linguagem de
programação baseada em atos de fala especificada por John McCarthy (Stanford, 6
de novembro de 1998) e nunca implementada por ele. O design é dele. Os limiares
de completude, as obrigações de compromisso, o runtime incremental e a API
embutível são deste projeto.*

## Por que

Um agente afirma coisas sobre o cadastro de um cliente, e promete fazer coisas.
Hoje nada liga nenhuma das duas à realidade. Filtros de saída verificam o
texto. Nada verifica se uma afirmação decorre do que realmente aconteceu, e
nada acompanha se uma promessa chegou a ser cumprida.

A resposta de McCarthy, escrita antes de o problema existir: faça o programa
dizer apenas o que o seu próprio histórico sustenta, e faça de suas promessas
dívidas que ele precisa quitar. Duas obrigações, ambas dele:

* **Uma resposta deve ser verdadeira.** Todo `yes` ou `no` precisa ser
  consequência lógica do log.
* **Uma promessa deve ser cumprida.** O programa não pode prometer o que seu
  histórico não estabelece, nem prometer aquilo que nenhum caminho por ele
  jamais poderia realizar.

Você não escreve essas condições. O compilador as lê do programa.

```
$ eleph obligations examples/airline_buggy.eleph

  linha 17  question(Caller, has_reservation)
    resposta yes e verdadeira
      supondo   alguma vez make_reservation(P, F)
      entao     (make_reservation(P, F) e desde entao nenhum cancel_reservation(P, F))
```

Em seguida, ele tenta quebrá-las.

```
$ eleph check examples/airline_buggy.eleph

  X   question(Caller, has_reservation)  linha 17  -  resposta yes e verdadeira

      historico que quebra a obrigacao:
        1. make_reservation(P, F)
        2. cancel_reservation(P, F)

      o programa responde yes, a verdade do log e no
```

O bug é uma palavra. O guard pergunta *fez uma reserva* onde deveria perguntar
*tem uma reserva*. São perguntas diferentes e a diferença é o cancelamento.
Este é o próprio exemplo de McCarthy, e a linguagem inteira existe para tornar
essa diferença impossível de passar despercebida.

## O passado é o único estado

Não há atribuição na gramática. Isso não é uma omissão. Não há nada a que
atribuir, porque um fato não é armazenado, ele é uma consulta sobre o que
aconteceu:

```
fact has_reservation(P: Passenger, F: Flight) :=
    make_reservation(P, F) since_not cancel_reservation(P, F)
```

Um elefante nunca esquece. Nada é sobrescrito, então nada pode se desalinhar da
verdade. As próprias falas do programa vão para o mesmo log, de modo que se
pode perguntar a ele o que já disse:

```
if spoke accept to C about make_reservation(P, F):
    decline C
```

## Prova, não amostragem

A verificação limitada de modelos responde a uma pergunta mais fraca do que
queremos: nenhum histórico *de até tamanho N* quebra a obrigação. Para o
fragmento desta linguagem essa lacuna se fecha, porque a verdade de uma fórmula
ao final de um histórico depende apenas da **ordem da última ocorrência de cada
átomo**. `a since_not b` é exatamente "existe um `a` depois do último `b`".
Qualquer configuração dessas é realizada por um histórico com uma posição por
átomo, então um limiar computável

```
N = sum over distinct atoms of k(a),   k(a) = 1, or n+1 under a count
```

faz "nenhum contraexemplo encontrado" significar "nenhum existe". Cada
obrigação é checada no seu próprio limiar:

```
PROVADO  -  6 obrigacoes valem para TODO historico, de qualquer tamanho
```

Isso não é enfeite. `examples/fundo.eleph` só mente depois de sete eventos, e
um limite fixo de seis **o aprova**:

```
$ eleph check examples/fundo.eleph --bound 6
SEM CONTRAEXEMPLO  -  dentro dos limites checados, que nao sao exaustivos aqui

$ eleph check examples/fundo.eleph
X   question(C, elite)  -  resposta yes e verdadeira
    1..7. make_reservation(P, F)
```

Uma fórmula que coloca uma expressão composta sob `since_not` sai do fragmento
linear. A completude passa então a vir do espaço de estados do monitor, `2^k`
para `k` subfórmulas temporais, que é exponencial em princípio e pequeno na
prática. Quando nem isso é viável, o checker diz que a execução não foi
exaustiva em vez de fingir.

## Três afirmações, e os experimentos que as quebrariam

**Limiar.** Nenhum veredito pode mudar acima do limiar computado. Testado
rechecando toda obrigação de todo exemplo com limites e domínios acima dele.

**Correção da derivação.** Se toda obrigação é provada, o runtime nunca recusa.
O runtime recusa exatamente quando a condição de verdade de um ato de fala
falha, e o derivador emite `path condition implies truth condition` para cada
ato desses sobre o mesmo log. Testado martelando programas provados com
passados aleatórios e conversas aleatórias, e confirmando que os não provados
de fato recusam.

**O índice computa o que o log computa.** Veja abaixo.

Eles vivem em `tests/test_soundness.py` e `tests/test_incremental.py`.

## Um histórico que nunca para de crescer

A objeção óbvia a uma linguagem cujo único estado é o seu passado é que
responder a uma pergunta significa ler o passado. Isso é quadrático, e
apareceu: em quatro mil interações isto rodava a 46 eventos por segundo.

Todo operador aqui tem uma recorrência de um passo,
`(a since_not b)@t = a@t or ((a since_not b)@(t-1) and not b@t)`, que é a
leitura por programação dinâmica da lógica temporal de tempo passado. Um lema
deixa isso preciso: **um evento que não casa com nenhum átomo de uma subfórmula
não pode mudar o valor dela.** Então incorporar um evento toca apenas as chaves
que esse evento nomeia.

```
$ python bench/scaling.py

interacoes      log   relendo   indice   ganho     ev/s  escala
       500     1096      1.44    0.040     36x    27272       -
      1000     2196      5.94    0.095     63x    23170   x2.36
                       (x4.1)
      2000     4396     24.87    0.212    117x    20755   x2.23
                       (x4.2)
      8000    17566         -    0.746      -    23548   x1.97
```

O tempo dobra quando o trabalho dobra, enquanto reler o log quadruplicava.
Medido em 140,546 eventos em 5.7 s com throughput constante.

Cada célula do índice é uma função pura do log, a mesma função que o avaliador
ingênuo computa relendo-o. Isso é uma otimização de uma afirmação de verdade,
então nunca se confia nela. `Machine(audit=True)` responde a toda consulta das
**duas** formas e levanta erro se elas divergirem, sobre passados aleatórios e
históricos com mais de mil eventos.

## Use a partir do Python

A linguagem é o artefato de pesquisa. O que a maioria dos sistemas precisa é
menor, e isso vem como biblioteca:

```python
from eleph import Policy

policy = Policy.from_file("booking.eleph")
assert policy.verify().proved          # the same file, proved statically

g = policy.guard(log="booking.jsonl")  # durable, reopening replays

g.record("make_reservation", "alice", "ba117")
g.holds("has_reservation", "alice", "ba117")                  # True
g.assert_answer("has_reservation", False, "alice", "ba117")   # raises

g.promise("alice", "has_seat", "alice", "ba117",
          before=("board", ("alice", "ba117")))
g.outstanding()        # what is still owed, to whom
```

Três formatos, do mais barato ao mais caro. `python examples/agente.py` executa
os três.

| formato | o que você muda | o que você ganha |
|---|---|---|
| **observador** | nada, você só alimenta os eventos | o que é verdade sobre o cadastro, e uma auditoria |
| **guard** | asserções e chamadas de ferramenta passam por ele | afirmações sem fundamento levantam erro em vez de ir para produção |
| **linguagem** | handlers escritos em `.eleph` | a prova estática |

A razão para manter as regras em um arquivo de política em vez de escrever as
verificações em Python é a primeira linha acima: **as regras que seu guard
aplica às três da manhã são o mesmo artefato que um solver provou.** Um guard
cujas regras foram provadas é coisa diferente de um guard cujas regras alguém
acreditou.

Nada além de eventos é escrito em disco. O índice e o ledger são reconstruídos
revivendo o passado, então um processo que morreu e voltou é indistinguível de
um que nunca morreu. Uma última linha truncada é descartada: um evento que
nunca terminou de ser escrito é um evento que não aconteceu.

## Medido contra um benchmark publicado

O [τ-bench](https://arxiv.org/abs/2406.12045) (ICLR 2025) dá a um agente de
atendimento de companhia aérea uma política escrita. Sua primeira regra:

> Antes de executar qualquer ação que atualize o banco de dados de reservas,
> você deve listar os detalhes da ação e obter confirmação explícita do usuário
> (yes) para prosseguir.

A política então diz, duas vezes, **"A API não verifica isso pelo agente."** E
a recompensa aplica hash ao banco de dados final, de modo que uma escrita não
confirmada que chega ao estado certo pontua exatamente como uma confirmada. A
obrigação está declarada, não é imposta e não é medida.

Essa regra é um `fact`. Reproduzindo as 200 trajetórias de companhia aérea do
gpt-4o publicadas:

```
$ python bench/taubench/check.py

  200 execucoes publicadas, 250 escritas no banco
  84 pontuadas como SUCESSO (42%, o pass^1 publicado e 0.420)

  leitura                 escritas  execucoes  sucessos com
                         sem conf.   afetadas      violacao
  gasta na acao                 85   45 (22%)     8 (10%)
  expira no turno               52   24 (12%)     4 ( 5%)
```

A frase não diz se um "yes" cobre uma ação ou um lote, então as duas leituras
são escritas, um `fact` para cada. Elas **não são ordenadas**: em 25 execuções
só a primeira acusa, em 4 só a segunda, em 20 as duas. Um time não pode
resolver isso escolhendo a regra mais permissiva, porque não existe uma.

### A regra que a API se recusa a verificar

A elegibilidade para cancelamento é evidência mais forte, porque
`cancel_reservation` não valida *absolutamente nada*. A wiki sabe disso: **"A
API não verifica isso pelo agente, então o agente precisa garantir que as
regras se aplicam antes de chamar a API!"**, o ponto de exclamação é deles.

```
$ python bench/taubench/cancel_check.py

  leitura de 'the condition is met'       proibidos  no gabarito
  seguro E motivo coberto (como o tau3 escreveu)         38           26
  ter seguro basta                                       16            7

  proibidos sob AMBAS as leituras: 16  (9 reservas distintas)
```

Duas coisas surgiram de escrever essa regra.

A frase *"somente se o seguro viagem foi comprado **e a condição é
atendida**"* nunca diz qual condição. Lida de forma estrita, ela proíbe 38
cancelamentos, 26 dos quais o **gabarito anotado executa**. A subespecificação
alcança os rótulos de referência, não apenas o agente. O τ³-bench depois
reescreveu exatamente essa frase, explicitando "o motivo do cancelamento é
coberto pelo seguro". A formalização caiu justamente sobre a frase que os
próprios autores foram corrigir, sem que ninguém mandasse olhar ali.

E uma reserva, `XEHM4B` (econômica, sem seguro, feita quatorze dias antes,
nenhum voo cancelado pela companhia), é cancelada pelo próprio gabarito em uma
execução pontuada com 1.0. Proibida sob qualquer leitura da frase.

Chegar até aí exigiu três correções, cada uma encontrada lendo casos à mão em
vez de confiar no número: a primeira contagem cobrava um lote de escritas sob
um único "yes"; a segunda chamava de violação um upgrade seguido de
cancelamento, que a política permite expressamente; a terceira modelava a
cabine com "aconteceu uma vez" quando uma cabine é um atributo que **muda**,
que é justamente para o que serve o `since_not`.

Isto não é uma afirmação de que o τ-bench está errado. Sua recompensa é
documentada e deliberada, e o artigo diz abertamente que `r = 1` "pode ser uma
condição necessária, mas não suficiente". A afirmação é mais estreita e
verificável: um compromisso que mandaram o agente cumprir não é medido pela
coisa que mede o agente, e basta uma linha para medi-lo.

`tests/test_taubench.py` fixa todos os números acima.

## Linguagem

```
sort   Passenger
event  make_reservation(p: Passenger, f: Flight)
fact   has_reservation(P: Passenger, F: Flight) := <temporal expression>
on question(C, has_reservation(P, F)):  ...
on request(C, make_reservation(P, F)):  ...
```

| forma | significado |
|---|---|
| `e(a, b)` | o evento `e` ocorreu **pelo menos uma vez** no passado |
| `a since_not b` | `a` ocorreu e nenhum `b` ocorreu desde então |
| `count e(a) >= n` | quantas vezes `e` ocorreu |
| `exists P: Sort where φ` | algum objeto satisfaz φ agora |
| `count P: Sort where φ >= n` | quantos satisfazem, que é o que um limite de assentos precisa |
| `spoke accept to C about e(...)` | o programa executou aquele ato naquele diálogo |
| `not`, `and`, `or` | como de costume |

O `e(a, b)` puro, significando *alguma vez aconteceu*, é a armadilha, de
propósito: ele se lê como "tem" e significa "fez". O verificador é o que
distingue os dois.

Comandos: `answer C yes` / `answer C no` / `answer C with φ`, `record e(...)`,
`accept C`, `decline C`, `release C from φ`, e três intensidades de
compromisso: `promise C that φ` (verdadeiro quando dito),
`promise C eventually φ` e `promise C that φ before e(...)`.

## Obrigações derivadas

| obrigação | verificada por |
|---|---|
| a resposta é verdadeira | Z3, no limiar de completude |
| a resposta responde à pergunta feita | Z3 |
| a promessa imediata vale no momento em que é feita | Z3, sobre o log mais o que o handler acabou de registrar |
| a promessa futura é alcançável por algum caminho | Z3, exigindo que o caminho a leve de falsa a verdadeira |
| os sorts dos argumentos batem com as declarações | compilador |
| todo caminho responde exatamente uma vez | estrutural |
| toda requisição é aceita ou recusada exatamente uma vez | estrutural |
| compromissos pendentes e quebrados | ledger em runtime |

## Limites honestos

* **Não há relógio de parede.** `since_not` conhece ordem, não tempo.
  "Cancelar em até 24 horas da reserva" não é expressável diretamente. O padrão
  que funciona hoje, e o que `bench/taubench/cancel.eleph` usa, é o host emitir
  o prazo como um evento. O relógio vive fora da lógica, que é como sistemas
  event sourced tratam o tempo de qualquer maneira.
* **Eventos carregam identidades, não dados.** Nada de `price > 100`. Coloque a
  classificação na identidade do evento, o que é grosseiro mas funciona para
  regras em nível de política.
* **O limiar linear de completude cobre um fragmento.** Ele vale quando todo
  `since_not` recebe átomos. Fora dele, a completude vem do espaço de estados
  do monitor, e além disso o checker admite que a execução não foi exaustiva. O
  limiar também cresce com as constantes: provar algo sobre uma capacidade de
  180 exige históricos capazes de conter 180 eventos.
* **Uma promessa futura é verificada quanto à possibilidade de cumprimento, não
  quanto a liveness.** O compilador prova que algum caminho a estabelece. Ele
  não pode provar que o interlocutor vai percorrer esse caminho, porque nenhum
  programa pode.
* **O índice precisa de localidade.** Uma subfórmula que nomeia menos variáveis
  do que a fórmula que a contém faz um único evento perturbar um número
  ilimitado de chaves. Esses programas ainda rodam, relendo o log, e
  `Machine.index.usable` avisa quando é o caso.
* **`spoke` nomeia o diálogo, não o conteúdo.** "Eu já prometi exatamente
  isto?" não é expressável. "Eu já prometi alguma coisa aqui?" é.
* **Fatos não podem ser recursivos**, então propriedades transitivas estão fora
  de alcance.
* **A auditoria do τ-bench lê linguagem natural com uma regex.** O assentimento
  é reconhecido a partir de uma lista generosa de palavras, então as contagens
  subestimam em vez de superestimar. Amostras de violações foram lidas à mão
  antes de os números serem publicados.
* **Os teoremas são provados no papel e testados, não mecanizados.** Um
  artefato em Lean para o fragmento ground é a próxima coisa que vale a pena
  construir.

## Instalação

```bash
pip install eleph          # or:  uv pip install eleph
```

A partir do código-fonte:

```bash
git clone https://github.com/isaacmello/eleph && cd eleph
uv venv && uv pip install -e ".[dev]"
```

## Executar

```bash
eleph obligations examples/airline_buggy.eleph   # what the text demands
eleph check       examples/companhia.eleph       # try to break it
eleph run         examples/companhia.eleph examples/voo.session --log /tmp/voo.jsonl
eleph ledger      examples/companhia.eleph /tmp/voo.jsonl   # what it still owes
eleph talk        examples/companhia.eleph examples/conversa.txt --roster alice,bruno,ba117

python examples/agente.py            # the three integration shapes
python bench/scaling.py              # constant time per event
python bench/taubench/check.py       # the benchmark audit
pytest -q                            # 121 tests
```

## Fonte

McCarthy, John. *Elephant 2000: A Programming Language Based on Speech Acts.*
Stanford, 6 de novembro de 1998.

## Licença

MIT. Veja [LICENSE](../LICENSE).
