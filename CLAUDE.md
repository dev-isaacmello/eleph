# eleph

Linguagem cujos programas não podem mentir: atos de fala, um histórico que é o
único estado, e obrigações de correção derivadas do texto do programa e
provadas com Z3. Publicada no PyPI como `eleph`. O site de documentação fica
em `site/` (Vite + React + MDX) e é publicado na Vercel.

## Comandos exatos

```bash
uv venv && uv pip install -e ".[dev,mcp]"     # setup, uma vez
uv run pytest -q                               # suíte inteira, ~15 s
uv run pytest -q tests/test_verifier.py -k nome   # um teste
uv run eleph check examples/airline.eleph --no-color   # verifica uma política
uv run eleph obligations examples/airline.eleph        # lista as obrigações derivadas
uv run python examples/agente.py > /dev/null           # as três formas de integração rodam
uv run python site/scripts/check-eleph-blocks.py       # todo bloco eleph do site é um programa
uv build                                               # sdist + wheel
cd site && npm run typecheck && npm run build          # site
```

O CI (`.github/workflows/ci.yml`) roda pytest em 3.11, 3.12 e 3.13, o
`eleph check` em cada exemplo, o `agente.py`, o checador de blocos do site e o
build da wheel. Antes de dizer que algo está pronto, rode o mesmo localmente.
O projeto não usa ruff nem formatador no CI: não reformate arquivo que você
não precisou mudar.

## Mapa

- `eleph/lexer.py`, `parser.py`, `ast.py`: front end da linguagem.
- `eleph/obligations.py`: deriva as obrigações a partir do texto.
- `eleph/verify.py`, `threshold.py`: encoding Z3 e limiar de completude.
- `eleph/runtime.py`, `store.py`, `incremental.py`: execução sobre o log.
- `eleph/guard.py`: a API `Policy`/`Guard` para pôr sob as tools de um agente.
- `eleph/mcp_server.py`: servidor MCP (`eleph-mcp`).
- `skills/eleph/SKILL.md` e `plugins/eleph/`: skill distribuída aos usuários.
  É produto, não configuração deste repositório. As duas cópias andam juntas.

## Convenções

- Strings de CLI voltadas ao usuário em português e sem acento, como todo o
  `cli.py` e os `.eleph` de exemplo. Identificadores, docstrings e
  comentários em inglês.
- Nunca use o caractere travessão (U+2014). O hook bloqueia a edição que o
  introduz.
- Python mínimo é 3.11. O único bug que chegou a uma versão publicada foi um
  erro de sintaxe que só o 3.11 via. O hook compila todo `.py` editado com o
  3.11 de verdade.
- Comentário explica o porquê, não o quê. O código é lido por quem decide se
  pode confiar nele.
- Mudança de comportamento vem com um teste que falharia sem ela.
  `tests/test_soundness.py` é o formato a copiar: o teste tenta quebrar uma
  afirmação feita em outro lugar.
- Exemplo novo em `examples/` entra também na lista do passo "every example
  verifies as expected" do `ci.yml`, do lado certo (PROVADO ou REPROVADO), e
  em `tests/test_incremental.py::test_the_examples_still_take_the_fast_path`
  se for uma política correta.
- A versão vive só em `pyproject.toml`. `__version__` é lido dos metadados.

## Nunca faça

- Publicar um número que não foi auditado à mão. Toda afirmação quantitativa
  em README, CHANGELOG, site ou docstring precisa da auditoria caso a caso que
  a sustenta. Use o subagente `auditor-de-numeros` antes de entregar texto com
  número.
- Criar tag `v*` ou dar push de tag: o `release.yml` publica no PyPI, e uma
  versão publicada nunca pode ser substituída nem reutilizada.
- `uv publish`, `twine upload`, `git push`, commit ou PR sem pedido explícito.
- Ler ou imprimir `.env*`, `~/.pypirc`, tokens ou chaves. O único segredo do
  projeto é `PYPI_API_TOKEN` e ele mora no GitHub.
- Enfraquecer a seção "Honest limits" do README ou trocar PROVADO por algo que
  o verificador não disse. `SEM CONTRAEXEMPLO` não é prova.
- Entregar um `.eleph` que não passou por `eleph check`. O MCP `eleph-local`
  (em `.mcp.json`) roda o checador desta árvore de trabalho.
- Editar `site/node_modules`, `site/dist` ou `dist/`.
