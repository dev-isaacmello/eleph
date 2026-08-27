/**
 * A TextMate grammar for `.eleph`.
 *
 * The keyword list is kept in the same order as `eleph/lexer.py` so a reader
 * can diff the two. Nothing here is decorative: the three groups below are the
 * three things the language actually distinguishes -- declarations, temporal
 * operators, and speech acts -- and colouring them apart is the point.
 */
export const elephGrammar = {
  name: 'eleph',
  scopeName: 'source.eleph',
  patterns: [
    { include: '#comment' },
    { include: '#declaration' },
    { include: '#handler' },
    { include: '#speech-act' },
    { include: '#temporal' },
    { include: '#control' },
    { include: '#number' },
    { include: '#assign' },
    { include: '#operator' },
    { include: '#sortname' },
    { include: '#variable' },
    { include: '#call' },
  ],
  repository: {
    comment: {
      match: '#.*$',
      name: 'comment.line.number-sign.eleph',
    },
    // `program airline`, `sort Passenger`, `event board(p: Passenger)`
    declaration: {
      begin: '\\b(program|sort|event|fact)\\b',
      beginCaptures: { 1: { name: 'keyword.other.declaration.eleph' } },
      end: '(?=$|:=|\\()',
      patterns: [{ include: '#entityname' }],
    },
    // `on question(C, has_reservation(P, F)) permitted autorizado(Q, U):`
    handler: {
      match: '\\b(on)\\s+(question|request)\\b|\\b(permitted)\\b',
      captures: {
        1: { name: 'keyword.control.handler.eleph' },
        2: { name: 'support.function.speech-act.eleph' },
        3: { name: 'keyword.control.permission.eleph' },
      },
    },
    // What the program is allowed to say. These are the whole language.
    'speech-act': {
      match:
        '\\b(answer|record|accept|decline|promise|offer|release|from|with|that|to|about|yes|no)\\b',
      name: 'keyword.other.speech-act.eleph',
    },
    // The past, read as a formula.
    temporal: {
      match: '\\b(since_not|count|exists|where|spoke|eventually|before)\\b',
      name: 'keyword.operator.temporal.eleph',
    },
    control: {
      match: '\\b(if|else|not|and|or)\\b',
      name: 'keyword.control.eleph',
    },
    number: {
      match: '\\b\\d+\\b',
      name: 'constant.numeric.eleph',
    },
    assign: {
      match: ':=',
      name: 'keyword.operator.assignment.eleph',
    },
    operator: {
      match: '>=|<=|==|!=|<|>',
      name: 'keyword.operator.comparison.eleph',
    },
    entityname: {
      match: '\\b([a-z_][A-Za-z_0-9]*)\\b',
      name: 'entity.name.function.eleph',
    },
    // Sorts and logical variables are capitalised; parameters are not.
    sortname: {
      match: '\\b([A-Z][A-Za-z_0-9]*)\\b',
      name: 'variable.other.logical.eleph',
    },
    variable: {
      match: '\\b([a-z_][A-Za-z_0-9]*)\\s*(?=:)',
      name: 'variable.parameter.eleph',
    },
    call: {
      match: '\\b([a-z_][A-Za-z_0-9]*)\\s*(?=\\()',
      name: 'entity.name.function.eleph',
    },
  },
} as const

/**
 * A grammar for what the CLI prints.
 *
 * `eleph check` says a great deal with three tokens -- `ok`, `ok?` and `X` --
 * and a verdict line. The terminal colours them; so does this, so the blocks
 * in these pages look like the run they are quoting rather than a paraphrase
 * of it.
 */
export const elephOutputGrammar = {
  name: 'eleph-output',
  scopeName: 'source.eleph-output',
  patterns: [
    { match: '^\\s*\\$.*$', name: 'string.other.prompt.eleph-output' },
    {
      match: '\\b(PROVADO|CUMPRIDA|ok)\\b(?!\\?)',
      name: 'markup.inserted.eleph-output',
    },
    {
      match: '\\b(REPROVADO|RECUSA|QUEBRADA|BREACHED)\\b|(?<=\\s)X(?=\\s)',
      name: 'markup.deleted.eleph-output',
    },
    {
      match: '\\b(SEM CONTRAEXEMPLO|ABERTA|LIBERADA|ok\\?)\\b',
      name: 'markup.changed.eleph-output',
    },
    { match: '\\b(linha|line)\\s+\\d+\\b', name: 'comment.line.eleph-output' },
    { match: '\\b\\d+(\\.\\d+)?\\b', name: 'constant.numeric.eleph-output' },
    {
      match: '\\b(since_not|count|exists|where|spoke|not|and|or)\\b',
      name: 'keyword.operator.temporal.eleph-output',
    },
    {
      match: '\\b(supondo|entao|resposta|verdadeira)\\b',
      name: 'keyword.control.eleph-output',
    },
  ],
} as const
