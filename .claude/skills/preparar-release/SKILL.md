---
name: preparar-release
description: Use quando for preparar uma versão nova do eleph para o PyPI ("prepara a 0.5.0", "bump de versão", "ensaia o release", "o que falta para lançar"). Faz o bump no pyproject.toml, escreve a entrada do CHANGELOG a partir do git log e ensaia localmente cada verificação do release.yml. Para antes da tag; nunca cria tag nem publica.
---

# Preparar release do eleph

Uma tag `v*` dispara `.github/workflows/release.yml`, que publica no PyPI. Uma
versão publicada nunca pode ser substituída nem reutilizada. Esta skill
deixa tudo pronto e verificado na árvore de trabalho e para. A tag é do dono
do repositório.

## Passos

1. **Versão.** Leia a atual em `pyproject.toml` (única fonte; `__version__`
   vem dos metadados). Confirme que a nova ainda não existe no PyPI:

   ```bash
   curl -s -o /dev/null -w '%{http_code}\n' https://pypi.org/pypi/eleph/<versao>/json
   ```

   `404` segue; `200` para tudo e avisa.

2. **CHANGELOG.** Liste os commits desde a última tag:

   ```bash
   git log --oneline "$(git describe --tags --abbrev=0)"..HEAD
   ```

   Escreva a entrada no formato das anteriores em `CHANGELOG.md`. Toda frase
   com número passa pelo subagente `auditor-de-numeros` antes de ficar.

3. **Ensaio do release.yml**, na ordem do workflow:

   ```bash
   for PY in 3.11 3.13; do
     uv run --isolated --python $PY --with-editable ".[dev]" pytest -q || break
   done
   rm -rf dist && uv build
   uvx twine check dist/*
   rm -rf /tmp/eleph-smoke && uv venv -q /tmp/eleph-smoke
   VIRTUAL_ENV=/tmp/eleph-smoke uv pip install -q dist/*.whl
   /tmp/eleph-smoke/bin/eleph check examples/companhia.eleph --no-color | tail -2   # PROVADO
   /tmp/eleph-smoke/bin/eleph check examples/fundo.eleph --no-color | tail -2      # REPROVADO
   ```

   O 3.11 não é opcional: foi a única versão que viu o bug que chegou ao PyPI.

4. **Site.** O cabeçalho do site lê a versão do `pyproject.toml`. Rode
   `cd site && npm run build` para confirmar que a versão nova aparece.

## Entrega

Um relatório curto: versão, link para a entrada do CHANGELOG, resultado real
de cada passo do ensaio (com a saída que falhou, se falhou) e os comandos que
o dono roda para publicar:

```bash
git commit -am "chore: release <versao>"
git tag -a v<versao> -m "eleph <versao>"
git push origin main --tags
```

Não execute esses três comandos. O `settings.json` do projeto nega `git tag`,
`git push` e `uv publish` de qualquer forma.
