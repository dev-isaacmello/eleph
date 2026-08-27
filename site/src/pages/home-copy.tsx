import type { ReactNode } from 'react'

import type { Locale } from '@/lib/nav'

export interface HomeCopy {
  eyebrow: ReactNode
  title: string
  sub: ReactNode
  ctaPrimary: string
  ctaSecondary: string
  bugLabel: string
  bugTitle: ReactNode
  bugLede: ReactNode
  bugPanelNote: ReactNode
  checkerPanel: string
  checkerNote: ReactNode
  stateLabel: string
  stateTitle: string
  stateLede: ReactNode
  factPanel: string
  factNote: ReactNode
  obligationsLabel: string
  obligationsTitle: string
  obligationsLede: ReactNode
  cards: { kicker: string; title: string; body: string; to: string }[]
  measuredLabel: string
  measuredTitle: string
  stats: { value: string; label: string; source: string }[]
  measuredCards: { kicker: string; title: string; body: string; to: string }[]
  pythonLabel: string
  pythonTitle: string
  pythonLede: ReactNode
  shapeHead: [string, string, string]
  shapes: [string, string, string][]
  shapesNote: ReactNode
  doorsLabel: string
  doorsTitle: string
  doors: { kicker: string; title: string; body: string; to: string }[]
  ctaTitle: string
  ctaBody: string
  ctaButton: string
  ctaGhost: string
}

export const HOME: Record<Locale, HomeCopy> = {
  en: {
    eyebrow: <>John McCarthy’s Elephant 2000, implemented</>,
    title: 'A language whose programs cannot lie.',
    sub: (
      <>
        Speech acts, a history that is the only state, and correctness conditions derived
        from the program text rather than written beside it. You do not write the
        conditions. The compiler reads them off the program, then tries to break them.
      </>
    ),
    ctaPrimary: 'Use it in your agent',
    ctaSecondary: 'See the language',
    bugLabel: 'The bug is one word',
    bugTitle: (
      <>
        The guard asks <em>did they make a reservation</em> where it should ask{' '}
        <em>do they have one</em>.
      </>
    ),
    bugLede: (
      <>
        Those are different questions, and the difference is the cancellation. This is
        McCarthy’s own example, and the whole language exists to make that difference
        impossible to overlook.
      </>
    ),
    bugPanelNote: (
      <>Nothing here is annotated with a contract. There is no assertion, no invariant, no test.</>
    ),
    checkerPanel: 'what the checker says',
    checkerNote: (
      <>Not a failing test: a history that breaks the obligation, printed back at you.</>
    ),
    stateLabel: 'The past is the only state',
    stateTitle: 'There is no assignment in the grammar.',
    stateLede: (
      <>
        This is not an omission. There is nothing to assign to, because a fact is not
        stored — it is a query over what happened. An elephant never forgets, so nothing is
        overwritten and nothing can drift out of agreement with the truth.
      </>
    ),
    factPanel: 'a fact, which is a formula about the log',
    factNote: (
      <>
        The program’s own utterances go into the same log, so it can be asked what it has
        already said.
      </>
    ),
    obligationsLabel: 'Two obligations, both McCarthy’s',
    obligationsTitle: 'An answer must be true. A promise must be kept.',
    obligationsLede: (
      <>
        Every <code>yes</code> or <code>no</code> must be entailed by the log. The program
        cannot promise what its history does not establish, nor promise what no path
        through it could ever bring about.
      </>
    ),
    cards: [
      {
        kicker: 'Derived',
        title: 'Ten obligations',
        body: 'Discharged by Z3 at the completeness threshold, or structurally by the compiler. Nobody writes them.',
        to: '/docs/concepts/obligations',
      },
      {
        kicker: 'Runtime',
        title: 'Four strengths of commitment',
        body: 'Offer, immediate promise, eventual promise, promise before an event — with a ledger that says what is still owed.',
        to: '/docs/concepts/commitments',
      },
      {
        kicker: 'Authority',
        title: 'Whether you were entitled to ask',
        body: 'An agent that truthfully reports any customer’s balance to whoever asks has told no lie at all. It is still an incident.',
        to: '/docs/concepts/permission',
      },
    ],
    measuredLabel: 'Measured, not asserted',
    measuredTitle: 'Every number here was read by hand first.',
    stats: [
      { value: '146', label: 'tests, run on 3.11, 3.12 and 3.13', source: 'pytest -q' },
      {
        value: '~24k',
        label: 'events per second, flat as the log grows',
        source: 'bench/scaling.py',
      },
      {
        value: '200',
        label: 'published τ-bench trajectories replayed',
        source: 'bench/taubench/',
      },
      {
        value: '45/45',
        label:
          'guarded agent runs passing, against 30/45 unguarded. Claude Haiku 4.5, nine cases, five runs each',
        source: 'examples/langchain-agent',
      },
    ],
    measuredCards: [
      {
        kicker: 'Performance',
        title: 'Constant time per event',
        body: 'One-step recurrences plus a locality lemma, audited against the naive evaluator on every query.',
        to: '/docs/performance',
      },
      {
        kicker: 'Audit',
        title: 'τ-bench does not measure its own policy',
        body: 'Two of its rules written as facts, replayed over 200 trajectories. Both turned out to be ambiguous in ways that reach the gold labels.',
        to: '/docs/taubench',
      },
      {
        kicker: 'Experiment',
        title: 'The same agent, with and without',
        body: 'Identical prompt and tools. Haiku 4.5 went 30/45 to 45/45; an earlier Opus 5 suite went 19/21 to 21/21. The only difference is the guard.',
        to: '/docs/integration/langchain',
      },
    ],
    pythonLabel: 'Use it from Python',
    pythonTitle: 'The language is the research artifact. This is what ships.',
    pythonLede: (
      <>
        The reason to keep the rules in a policy file rather than writing the checks in
        Python is the second line below: the rules your guard enforces at three in the
        morning are the same artifact a solver proved.
      </>
    ),
    shapeHead: ['Shape', 'You change', 'You get'],
    shapes: [
      ['observer', 'nothing, you feed it events', 'what is true of the record, and an audit'],
      [
        'guard',
        'assertions and tool calls route through it',
        'ungrounded claims raise instead of shipping',
      ],
      ['language', 'handlers written in .eleph', 'the static proof'],
    ],
    shapesNote: <>Cheapest first.</>,
    doorsLabel: 'Whichever one you are',
    doorsTitle: 'Three doors, and they are not the same door.',
    doors: [
      {
        kicker: 'You ship an agent',
        title: 'Start here',
        body: 'What it does, what it does not do, and which of the three shapes is yours. GPT-4, Claude, or a hand-written loop: nothing in the guard knows what an LLM is.',
        to: '/docs/use/start-here',
      },
      {
        kicker: 'You want to see it',
        title: 'Quickstart',
        body: 'Nine lines, one bug McCarthy wrote down in 1998, and a checker that prints the history that breaks it.',
        to: '/docs/quickstart',
      },
      {
        kicker: 'You want the argument',
        title: 'Proof, not spot check',
        body: 'The completeness thresholds, the locality lemma, and the experiments that would break each claim.',
        to: '/docs/concepts/completeness',
      },
    ],
    ctaTitle: 'Start with the bug that started it.',
    ctaBody:
      'Install, derive the obligations of a nine-line program, and watch the checker produce the history that breaks it.',
    ctaButton: 'Quickstart',
    ctaGhost: 'Honest limits',
  },

  'pt-BR': {
    eyebrow: <>O Elephant 2000 de John McCarthy, implementado</>,
    title: 'Uma linguagem cujos programas não conseguem mentir.',
    sub: (
      <>
        Atos de fala, um histórico que é o único estado, e condições de correção derivadas
        do texto do programa em vez de escritas ao lado dele. Você não escreve as
        condições. O compilador as lê do programa e então tenta quebrá-las.
      </>
    ),
    ctaPrimary: 'Use no seu agente',
    ctaSecondary: 'Ver a linguagem',
    bugLabel: 'O bug tem uma palavra',
    bugTitle: (
      <>
        O guarda pergunta <em>ele fez uma reserva</em> quando deveria perguntar{' '}
        <em>ele tem uma reserva</em>.
      </>
    ),
    bugLede: (
      <>
        São perguntas diferentes, e a diferença é o cancelamento. Este é o exemplo do
        próprio McCarthy, e a linguagem inteira existe para tornar essa diferença
        impossível de passar batido.
      </>
    ),
    bugPanelNote: (
      <>Nada aqui está anotado com um contrato. Não há asserção, nem invariante, nem teste.</>
    ),
    checkerPanel: 'o que o verificador diz',
    checkerNote: (
      <>Não é um teste que falhou: é um histórico que quebra a obrigação, impresso de volta.</>
    ),
    stateLabel: 'O passado é o único estado',
    stateTitle: 'Não existe atribuição na gramática.',
    stateLede: (
      <>
        Isso não é uma omissão. Não há a que atribuir, porque um fato não é armazenado — ele
        é uma consulta sobre o que aconteceu. Um elefante nunca esquece, então nada é
        sobrescrito e nada pode sair de acordo com a verdade.
      </>
    ),
    factPanel: 'um fato, que é uma fórmula sobre o log',
    factNote: (
      <>
        As próprias falas do programa vão para o mesmo log, então dá para perguntar a ele o
        que já disse.
      </>
    ),
    obligationsLabel: 'Duas obrigações, ambas de McCarthy',
    obligationsTitle: 'Uma resposta tem que ser verdadeira. Uma promessa tem que ser cumprida.',
    obligationsLede: (
      <>
        Todo <code>yes</code> ou <code>no</code> tem que ser implicado pelo log. O programa
        não pode prometer o que o histórico dele não estabelece, nem prometer o que nenhum
        caminho por ele jamais conseguiria realizar.
      </>
    ),
    cards: [
      {
        kicker: 'Derivadas',
        title: 'Dez obrigações',
        body: 'Descarregadas pelo Z3 no limiar de completude, ou estruturalmente pelo compilador. Ninguém as escreve.',
        to: '/docs/concepts/obligations',
      },
      {
        kicker: 'Runtime',
        title: 'Quatro forças de compromisso',
        body: 'Oferta, promessa imediata, promessa futura, promessa antes de um evento — com um livro que diz o que ainda se deve.',
        to: '/docs/concepts/commitments',
      },
      {
        kicker: 'Autoridade',
        title: 'Se você tinha direito de perguntar',
        body: 'Um agente que informa com toda honestidade o saldo de qualquer cliente a quem perguntar não mentiu. Ainda assim é um incidente.',
        to: '/docs/concepts/permission',
      },
    ],
    measuredLabel: 'Medido, não afirmado',
    measuredTitle: 'Todo número aqui foi lido à mão antes.',
    stats: [
      { value: '146', label: 'testes, rodando em 3.11, 3.12 e 3.13', source: 'pytest -q' },
      {
        value: '~24k',
        label: 'eventos por segundo, constante conforme o log cresce',
        source: 'bench/scaling.py',
      },
      {
        value: '200',
        label: 'trajetórias publicadas do τ-bench reexecutadas',
        source: 'bench/taubench/',
      },
      {
        value: '45/45',
        label:
          'execuções do agente com guarda que passam, contra 30/45 sem. Claude Haiku 4.5, nove casos, cinco execuções cada',
        source: 'examples/langchain-agent',
      },
    ],
    measuredCards: [
      {
        kicker: 'Desempenho',
        title: 'Tempo constante por evento',
        body: 'Recorrências de um passo mais um lema de localidade, auditados contra o avaliador ingênuo a cada consulta.',
        to: '/docs/performance',
      },
      {
        kicker: 'Auditoria',
        title: 'O τ-bench não mede a própria política',
        body: 'Duas das regras dele escritas como fatos e reexecutadas sobre 200 trajetórias. Ambas se revelaram ambíguas de um jeito que alcança o gabarito.',
        to: '/docs/taubench',
      },
      {
        kicker: 'Experimento',
        title: 'O mesmo agente, com e sem',
        body: 'Prompt e ferramentas idênticos. O Haiku 4.5 foi de 30/45 para 45/45; uma suíte anterior no Opus 5 foi de 19/21 para 21/21. A única diferença é a guarda.',
        to: '/docs/integration/langchain',
      },
    ],
    pythonLabel: 'Use a partir do Python',
    pythonTitle: 'A linguagem é o artefato de pesquisa. Isto é o que vai para produção.',
    pythonLede: (
      <>
        A razão para manter as regras num arquivo de política em vez de escrever as
        verificações em Python é a segunda linha abaixo: as regras que sua guarda aplica às
        três da manhã são o mesmo artefato que um solver provou.
      </>
    ),
    shapeHead: ['Forma', 'Você muda', 'Você ganha'],
    shapes: [
      ['observador', 'nada, você só alimenta eventos', 'o que é verdade do registro, e uma auditoria'],
      [
        'guarda',
        'asserções e chamadas de ferramenta passam por ela',
        'afirmações sem base levantam erro em vez de irem ao ar',
      ],
      ['linguagem', 'handlers escritos em .eleph', 'a prova estática'],
    ],
    shapesNote: <>Da mais barata para a mais cara.</>,
    doorsLabel: 'Seja qual for o seu caso',
    doorsTitle: 'Três portas, e não são a mesma porta.',
    doors: [
      {
        kicker: 'Você já tem um agente',
        title: 'Comece por aqui',
        body: 'O que ele faz, o que ele não faz, e qual das três formas é a sua. GPT-4, Claude ou um loop escrito à mão: nada na guarda sabe o que é um LLM.',
        to: '/docs/use/start-here',
      },
      {
        kicker: 'Você quer ver funcionando',
        title: 'Primeiros passos',
        body: 'Nove linhas, um bug que McCarthy escreveu em 1998, e um verificador que imprime o histórico que o quebra.',
        to: '/docs/quickstart',
      },
      {
        kicker: 'Você quer o argumento',
        title: 'Prova, não amostragem',
        body: 'Os limiares de completude, o lema de localidade, e os experimentos que quebrariam cada alegação.',
        to: '/docs/concepts/completeness',
      },
    ],
    ctaTitle: 'Comece pelo bug que começou tudo.',
    ctaBody:
      'Instale, derive as obrigações de um programa de nove linhas, e veja o verificador produzir o histórico que o quebra.',
    ctaButton: 'Primeiros passos',
    ctaGhost: 'Limites honestos',
  },
}
