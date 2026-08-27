<h1 align="center">eleph</h1>

<p align="center">
  <strong>Un lenguaje cuyos programas no pueden mentir.</strong><br>
  Actos de habla, un historial que es el único estado y condiciones de
  corrección derivadas del texto del programa en lugar de escritas junto a él.
</p>

<p align="center">
  <a href="#instalación">Instalación</a> ·
  <a href="#úsalo-desde-python">API de Python</a> ·
  <a href="#medido-contra-un-benchmark-publicado">Benchmark</a> ·
  <a href="#límites-honestos">Límites</a> ·
  <a href="../README.md">English</a> ·
  <a href="README.pt-BR.md">Português</a> ·
  Español ·
  <a href="README.zh-CN.md">中文</a>
</p>

---

*Isaac Mello, 2026. Implementa y extiende **Elephant 2000**, un lenguaje de
programación basado en actos de habla especificado por John McCarthy (Stanford,
6 de noviembre de 1998) y que él nunca llegó a implementar. El diseño es suyo.
Los umbrales de completitud, las obligaciones de compromiso, el runtime
incremental y la API embebible son de este proyecto.*

## Por qué

Un agente afirma cosas sobre el registro de un cliente, y promete hacer cosas.
Hoy nada conecta ninguna de las dos con la realidad. Los filtros de salida
revisan el texto. Nada comprueba si una afirmación se sigue de lo que realmente
ocurrió, y nada hace seguimiento de si una promesa llegó a cumplirse.

La respuesta de McCarthy, escrita antes de que el problema existiera: haz que
el programa diga solo lo que su propio historial sustenta, y que sus promesas
sean deudas que tiene que saldar. Dos obligaciones, ambas suyas:

* **Una respuesta debe ser verdadera.** Todo `yes` o `no` debe estar implicado
  por el log.
* **Una promesa debe cumplirse.** El programa no puede prometer lo que su
  historial no establece, ni prometer lo que ningún camino a través de él
  podría llegar a producir.

Tú no escribes esas condiciones. El compilador las lee del programa.

```
$ eleph obligations examples/airline_buggy.eleph

  linha 17  question(Caller, has_reservation)
    resposta yes e verdadeira
      supondo   alguma vez make_reservation(P, F)
      entao     (make_reservation(P, F) e desde entao nenhum cancel_reservation(P, F))
```

Después intenta romperlas.

```
$ eleph check examples/airline_buggy.eleph

  X   question(Caller, has_reservation)  linha 17  -  resposta yes e verdadeira

      historico que quebra a obrigacao:
        1. make_reservation(P, F)
        2. cancel_reservation(P, F)

      o programa responde yes, a verdade do log e no
```

El bug es una sola palabra. El guard pregunta *si hicieron una reserva* cuando
debería preguntar *si tienen una reserva*. Son preguntas distintas y la
diferencia es la cancelación. Este es el propio ejemplo de McCarthy, y todo el
lenguaje existe para volver imposible pasar por alto esa diferencia.

## El pasado es el único estado

No hay asignación en la gramática. No se trata de una omisión. No hay nada a lo
que asignar, porque un hecho no se almacena: es una consulta sobre lo que
ocurrió:

```
fact has_reservation(P: Passenger, F: Flight) :=
    make_reservation(P, F) since_not cancel_reservation(P, F)
```

Un elefante nunca olvida. Nada se sobrescribe, así que nada puede desviarse de
la verdad. Las propias declaraciones del programa van al mismo log, de modo que
se le puede preguntar qué ha dicho ya:

```
if spoke accept to C about make_reservation(P, F):
    decline C
```

## Prueba, no muestreo

El model checking acotado responde una pregunta más débil de la que queremos:
ningún historial *de longitud hasta N* rompe la obligación. Para el fragmento de
este lenguaje esa brecha se cierra, porque la verdad de una fórmula al final de
un historial depende solo del **orden de la última ocurrencia de cada átomo**.
`a since_not b` es exactamente "hay un `a` después del último `b`". Cualquier
configuración de ese tipo se realiza con un historial de una posición por
átomo, así que un umbral computable

```
N = sum over distinct atoms of k(a),   k(a) = 1, or n+1 under a count
```

hace que "no se encontró contraejemplo" signifique "no existe ninguno". Cada
obligación se comprueba en su propio umbral:

```
PROVADO  -  6 obrigacoes valem para TODO historico, de qualquer tamanho
```

Esto no es decoración. `examples/fundo.eleph` miente solo después de siete
eventos, y una cota fija de seis **lo aprueba**:

```
$ eleph check examples/fundo.eleph --bound 6
SEM CONTRAEXEMPLO  -  dentro dos limites checados, que nao sao exaustivos aqui

$ eleph check examples/fundo.eleph
X   question(C, elite)  -  resposta yes e verdadeira
    1..7. make_reservation(P, F)
```

Una fórmula que pone una expresión compuesta bajo `since_not` sale del fragmento
lineal. La completitud viene entonces del espacio de estados del monitor, `2^k`
para `k` subfórmulas temporales, que es exponencial en principio y pequeño en la
práctica. Cuando ni siquiera eso resulta asequible, el verificador dice que la
ejecución no fue exhaustiva en lugar de fingir.

## Tres afirmaciones, y los experimentos que las romperían

**Umbral.** Ningún veredicto puede cambiar por encima del umbral calculado. Se
comprueba volviendo a verificar cada obligación de cada ejemplo con cotas y
dominios superiores.

**Solidez de la derivación.** Si toda obligación queda probada, el runtime nunca
rechaza. El runtime rechaza exactamente cuando falla la condición de verdad de
un acto de habla, y el derivador emite `path condition implies truth condition`
para cada acto de ese tipo sobre el mismo log. Se comprueba martillando los
programas probados con pasados y conversaciones aleatorios, y confirmando que
los no probados sí rechazan.

**El índice calcula lo que calcula el log.** Ver más abajo.

Viven en `tests/test_soundness.py` y `tests/test_incremental.py`.

## Un historial que nunca deja de crecer

La objeción obvia a un lenguaje cuyo único estado es su pasado es que responder
una pregunta implica leer el pasado. Eso es cuadrático, y se notaba: con cuatro
mil interacciones esto corría a 46 eventos por segundo.

Cada operador de aquí tiene una recurrencia de un paso,
`(a since_not b)@t = a@t or ((a since_not b)@(t-1) and not b@t)`, que es la
lectura en programación dinámica de la lógica temporal de tiempo pasado. Un lema
la vuelve precisa: **un evento que no coincide con ningún átomo de una
subfórmula no puede cambiar su valor.** Así que incorporar un evento toca solo
las claves que ese evento nombra.

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

El tiempo se duplica cuando el trabajo se duplica, mientras que releer el log lo
cuadruplicaba. Medido en 140,546 eventos en 5.7 s con throughput plano.

Cada celda del índice es una función pura del log, la misma función que el
evaluador ingenuo calcula releyéndolo. Eso es una optimización de una afirmación
de verdad, así que nunca se confía en ella. `Machine(audit=True)` responde cada
consulta de **ambas** maneras y lanza un error si difieren, sobre pasados
aleatorios e historiales de más de mil eventos.

## Úsalo desde Python

Un ejemplo trabajado está en [`examples/langchain-agent`](../examples/langchain-agent):
el mismo agente LangChain ejecutado dos veces sobre nueve casos, una con un
guard debajo y otra sin él, con modelo, prompt y herramientas idénticos.

El lenguaje es el artefacto de investigación. Lo que la mayoría de los sistemas
necesita es más pequeño, y se distribuye como biblioteca:

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

Tres formas, de la más barata en adelante. `python examples/agente.py` ejecuta
las tres.

| forma | qué cambias | qué obtienes |
|---|---|---|
| **observador** | nada, tú le pasas los eventos | qué es verdad del registro, y una auditoría |
| **guard** | las afirmaciones y las llamadas a herramientas pasan por él | las afirmaciones sin fundamento lanzan un error en vez de salir |
| **lenguaje** | handlers escritos en `.eleph` | la prueba estática |

La razón para mantener las reglas en un archivo de política, en lugar de
escribir las comprobaciones en Python, es la primera línea de arriba: **las
reglas que tu guard aplica a las tres de la mañana son el mismo artefacto que un
solver probó.** Un guard cuyas reglas fueron probadas es algo distinto de un
guard cuyas reglas alguien creyó.

En disco no se escribe nada más que eventos. El índice y el libro mayor se
reconstruyen volviendo a vivir el pasado, así que un proceso que murió y volvió
es indistinguible de uno que nunca murió. Una última línea truncada se descarta:
un evento que nunca terminó de escribirse es un evento que no ocurrió.

## Medido contra un benchmark publicado

[τ-bench](https://arxiv.org/abs/2406.12045) (ICLR 2025) le da a un agente de
atención al cliente de una aerolínea una política escrita. Su primera regla:

> Antes de realizar cualquier acción que actualice la base de datos de reservas,
> debes enumerar los detalles de la acción y obtener la confirmación explícita
> del usuario (yes) para continuar.

La política dice luego, dos veces, **"La API no comprueba esto por el agente."**
Y la recompensa hashea la base de datos final, de modo que una escritura sin
confirmar que aterriza en el estado correcto puntúa exactamente igual que una
confirmada. La obligación está enunciada, sin aplicarse y sin medirse.

Esa regla es un `fact`. Al reproducir las 200 trayectorias publicadas de gpt-4o
para la aerolínea:

```
$ python bench/taubench/check.py

  200 execucoes publicadas, 250 escritas no banco
  84 pontuadas como SUCESSO (42%, o pass^1 publicado e 0.420)

  leitura                 escritas  execucoes  sucessos com
                         sem conf.   afetadas      violacao
  gasta na acao                 85   45 (22%)     8 (10%)
  expira no turno               52   24 (12%)     4 ( 5%)
```

La frase no dice si un "yes" cubre una acción o un lote, así que se escriben las
dos lecturas, un `fact` para cada una. **No están ordenadas**: en 25 ejecuciones
salta solo la primera, en 4 solo la segunda, en 20 ambas. Un equipo no puede
zanjar esto quedándose con la regla más laxa, porque no la hay.

### La regla que la API se niega a comprobar

La elegibilidad de cancelación es evidencia más fuerte, porque
`cancel_reservation` no valida *absolutamente nada*. El wiki lo sabe: **"La API
no comprueba esto por el agente, ¡así que el agente debe asegurarse de que las
reglas se cumplen antes de llamar a la API!"**, con el signo de exclamación
puesto por ellos.

```
$ python bench/taubench/cancel_check.py

  leitura de 'the condition is met'       proibidos  no gabarito
  seguro E motivo coberto (como o tau3 escreveu)         38           26
  ter seguro basta                                       16            7

  proibidos sob AMBAS as leituras: 16  (9 reservas distintas)
```

De escribir esa regla salieron dos cosas.

La frase *"solo si se compró un seguro de viaje **y se cumple la condición**"*
nunca dice qué condición. Leída de forma estricta, prohíbe 38 cancelaciones, 26
de las cuales **las realiza el ground truth anotado**. La subespecificación
alcanza a las etiquetas de oro, no solo al agente. τ³-bench reescribió más tarde
exactamente esa frase, explicitando "el motivo de la cancelación está cubierto
por el seguro". La formalización aterrizó justo en la frase que sus autores
terminaron corrigiendo, sin que nadie le dijera dónde mirar.

Y una reserva, `XEHM4B` (clase turista, sin seguro, reservada catorce días
antes, sin ningún vuelo cancelado por la aerolínea) es cancelada por el propio
ground truth en una ejecución puntuada con 1.0. Prohibida se lea como se lea la
frase.

Llegar hasta ahí costó tres correcciones, cada una encontrada leyendo casos a
mano en lugar de confiar en el número: el primer conteo cargaba un lote de
escrituras bajo un único "yes"; el segundo llamaba violación a un upgrade
seguido de una cancelación, algo que la política permite expresamente; el
tercero modelaba la cabina con "ocurrió una vez" cuando una cabina es un
atributo que **cambia**, que es justo para lo que sirve `since_not`.

Esto no es una afirmación de que τ-bench esté equivocado. Su recompensa está
documentada y es deliberada, y el paper dice sin rodeos que `r = 1` "podría ser
una condición necesaria pero no suficiente". La afirmación es más estrecha y
comprobable: un compromiso que se le pidió cumplir a un agente no lo mide
aquello que mide al agente, y basta una línea para medirlo.

`tests/test_taubench.py` fija todos los números de arriba.

## Lenguaje

```
sort   Passenger
event  make_reservation(p: Passenger, f: Flight)
fact   has_reservation(P: Passenger, F: Flight) := <temporal expression>
on question(C, has_reservation(P, F)):  ...
on request(C, make_reservation(P, F)):  ...
```

| forma | significado |
|---|---|
| `e(a, b)` | el evento `e` ocurrió **al menos una vez** en el pasado |
| `a since_not b` | `a` ocurrió y ningún `b` ha ocurrido desde entonces |
| `count e(a) >= n` | cuántas veces ocurrió `e` |
| `exists P: Sort where φ` | algún objeto satisface φ ahora |
| `count P: Sort where φ >= n` | cuántos lo hacen, que es lo que necesita un límite de asientos |
| `spoke accept to C about e(...)` | el programa realizó ese acto en ese intercambio |
| `e(a, amount > 100)` | un campo numérico del evento, evaluado en el momento en que ocurre |
| `not`, `and`, `or` | como es habitual |

Un handler puede condicionarse a la autoridad, que es el octavo acto de habla de
McCarthy y aquel por el que una revisión ordinaria nunca pregunta:

```
on question(Quem, saldo(C)) permitted pode_perguntar(Quem, C):
    answer Quem with saldo(C)
```

Un agente de soporte que informa con toda veracidad el saldo de cualquier
cliente a quien se lo pida no ha dicho mentira alguna, y todas las demás
obligaciones de aquí lo aprobarían. El permiso se suma a la condición de camino,
de modo que las respuestas se prueban *bajo* él en lugar de comprobarse aparte,
y el runtime falla cerrado: una respuesta retenida es recuperable, una respuesta
filtrada no.

El `e(a, b)` desnudo, con el sentido de *ocurrió alguna vez*, es la trampa, y lo
es a propósito: se lee como "tiene" y significa "hizo". El verificador es lo que
distingue una cosa de la otra.

Sentencias: `answer C yes` / `answer C no` / `answer C with φ`, `record e(...)`,
`accept C`, `decline C`, `release C from φ`, y cuatro intensidades de
compromiso: `offer C that φ` (dispuesto, aún sin deber nada),
`promise C that φ` (verdadera al decirse), `promise C eventually φ` y
`promise C that φ before e(...)`.

## Obligaciones derivadas

| obligación | comprobada por |
|---|---|
| la respuesta es verdadera | Z3, en el umbral de completitud |
| la respuesta responde a la pregunta formulada | Z3 |
| la promesa inmediata se sostiene al hacerse | Z3, sobre el log más lo que el handler acaba de registrar |
| la promesa futura es una que algún camino puede producir | Z3, exigiendo que el camino la haga pasar de falsa a verdadera |
| los sorts de los argumentos concuerdan con las declaraciones | compilador, en cada fact, se use o no |
| la oferta es una que algún camino podría honrar | Z3 |
| ninguna puerta hacia un asunto protegido queda sin llave | estructural |
| todo camino responde exactamente una vez | estructural |
| toda solicitud se acepta o se rechaza exactamente una vez | estructural |
| compromisos pendientes e incumplidos | libro mayor en runtime |

## Límites honestos

* **No hay reloj de pared.** `since_not` conoce el orden, no el tiempo.
  "Cancelar dentro de las 24 horas posteriores a la reserva" no es expresable
  directamente. El patrón que funciona hoy, y el que usa
  `bench/taubench/cancel.eleph`, es que el host emita el plazo como un evento.
  El reloj vive fuera de la lógica, que es como los sistemas event sourced
  manejan el tiempo de todos modos.
* **Los campos numéricos se comparan en el instante en que ocurre el evento.**
  Eso es lo que mantiene intacto el argumento de completitud, y es también el
  límite: puedes preguntar si *este cargo* superó 100, no si la suma de los tres
  últimos lo hizo. La aritmética agregada sobre el historial no es expresable.
* **El umbral lineal de completitud cubre un fragmento.** Vale cuando cada
  `since_not` toma átomos. Fuera de ahí, la completitud viene del espacio de
  estados del monitor, y más allá el verificador admite que la ejecución no fue
  exhaustiva. El umbral también crece con las constantes: probar algo sobre una
  capacidad de 180 requiere historiales capaces de contener 180 eventos.
* **Una promesa futura se comprueba por cumplibilidad, no por liveness.** El
  compilador prueba que algún camino la establece. No puede probar que quien
  llama recorrerá ese camino, porque ningún programa puede.
* **El índice necesita localidad.** Una subfórmula que nombra menos variables
  que su padre hace que un solo evento perturbe una cantidad no acotada de
  claves. Esos programas siguen ejecutándose, releyendo el log, y
  `Machine.index.usable` lo indica.
* **`spoke` nombra el intercambio, no el contenido.** "¿Ya prometí exactamente
  esto?" no es expresable. "¿Ya prometí algo aquí?" sí lo es.
* **El permiso es un hecho, no un sistema de roles.** `permitted` condiciona un
  handler a algo que el log sostiene, lo que cubre "este interlocutor se
  autentico en esta cuenta". No hay roles, jerarquia ni delegacion.
* **Los hechos no pueden ser recursivos**, así que las propiedades transitivas
  quedan fuera de alcance.
* **La auditoría de τ-bench lee lenguaje natural con una regex.** El
  asentimiento se detecta con una lista generosa de palabras, así que los
  conteos subestiman en lugar de sobreestimar. Las violaciones de muestra se
  leyeron a mano antes de publicar los números.
* **Los teoremas están probados en papel y testeados, no mecanizados.** Un
  artefacto en Lean para el fragmento ground es lo siguiente que vale la pena
  construir.

## Instalación

```bash
pip install eleph          # or:  uv pip install eleph
```

Desde el código fuente:

```bash
git clone https://github.com/dev-isaacmello/eleph && cd eleph
uv venv && uv pip install -e ".[dev]"
```

## Ejecutar

```bash
eleph obligations examples/airline_buggy.eleph   # what the text demands
eleph check       examples/companhia.eleph       # try to break it
eleph run         examples/companhia.eleph examples/voo.session --log /tmp/voo.jsonl
eleph ledger      examples/companhia.eleph /tmp/voo.jsonl   # what it still owes
eleph talk        examples/companhia.eleph examples/conversa.txt --roster alice,bruno,ba117

python examples/agente.py            # the three integration shapes
python bench/scaling.py              # constant time per event
python bench/taubench/check.py       # the benchmark audit
pytest -q                            # 146 tests
```

## Fuente

McCarthy, John. *Elephant 2000: A Programming Language Based on Speech Acts.*
Stanford, 6 de noviembre de 1998.

## Licencia

MIT. Ver [LICENSE](../LICENSE).
