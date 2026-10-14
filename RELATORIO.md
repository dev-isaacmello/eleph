# Relatório: eleph configurado para o Claude Code

O repositório é o [eleph](https://github.com/dev-isaacmello/eleph), uma
linguagem de políticas verificadas com Z3, publicada no PyPI e mantida por
mim. É código real, com CI, release automatizado e usuários. Configurei o
Claude Code em cima das regras que o projeto já tinha e que até então só
existiam em texto no `CONTRIBUTING.md`: Python mínimo 3.11, nenhum travessão,
nenhum número publicado sem auditoria e nenhuma tag sem querer, já que a tag
publica no PyPI.

## O que foi configurado

| Critério | Arquivo | O que faz |
|---|---|---|
| CLAUDE.md | [`CLAUDE.md`](CLAUDE.md) | Comandos exatos (setup, teste, `eleph check`, build, site), mapa dos módulos, convenções e uma seção "Nunca faça". |
| Permissões | [`.claude/settings.json`](.claude/settings.json) | Libera os comandos do CI. Pede confirmação para `git commit` e `gh pr create`. Nega leitura de `.env*`, `~/.pypirc`, `*.pem`, `*.key`, `~/.ssh` e `~/.config/gh`, além de `printenv`, `uv publish`, `twine upload`, `git push`, `git tag`, `gh release` e `git reset --hard`. |
| Skill | [`.claude/skills/preparar-release/SKILL.md`](.claude/skills/preparar-release/SKILL.md) | Prepara uma versão: bump, CHANGELOG e ensaio local de cada passo do `release.yml`. A descrição diz quando usar e que ela para antes da tag. |
| Hook | [`.claude/hooks/verificar-edicao.sh`](.claude/hooks/verificar-edicao.sh) | `PostToolUse` em `Edit\|Write\|MultiEdit`. Bloqueia travessão no texto recém-escrito, compila todo `.py` editado com o Python 3.11 real e roda `eleph check` em todo `.eleph`. Sintaxe inválida volta como erro; o veredito PROVADO/REPROVADO volta como contexto. |
| Subagente | [`.claude/agents/auditor-de-numeros.md`](.claude/agents/auditor-de-numeros.md) | Audita afirmações quantitativas contra a fonte no repositório. Ferramentas restritas a `Read, Grep, Glob`: não edita nem executa. |
| MCP | [`.mcp.json`](.mcp.json) | `eleph-local`: o servidor MCP do próprio projeto, rodando a partir do `.venv` desta árvore. O modelo verifica a política com o código que está sendo alterado, não com a versão do PyPI. |

`.claude/settings.local.json` entrou no `.gitignore` para que ajustes pessoais
não vazem para o repositório.

### Por que essas regras

- **3.11 no hook.** Segundo o `CONTRIBUTING.md`, o único bug que chegou a uma
  versão publicada foi um erro de sintaxe que só o 3.11 via. Testei o hook com
  `print(f"{d["a"]}")`: o 3.12 aceita, e o hook rejeita com
  `SyntaxError: f-string: unmatched '['`.
- **Travessão só no texto novo.** Algumas páginas antigas do site ainda têm o
  caractere. Se o hook cobrasse o arquivo inteiro, ele reclamaria a cada edição
  e ninguém leria o aviso.
- **REPROVADO não bloqueia.** Os `*_buggy.eleph` existem para ser reprovados.
  O hook só bloqueia o que não é programa válido (`eleph check` sai com 2).
- **Binário do `.venv` em vez de `uv run`.** Na primeira versão, o hook e o MCP
  usavam `uv run`, que cria um `uv.lock` que o projeto não versiona. O
  experimento abaixo mostrou o arquivo aparecendo e eu troquei: um hook não deve
  deixar arquivo para trás.

## Verificação de cada peça

Tudo foi executado, não apenas lido:

| Peça | Como foi testada | Resultado |
|---|---|---|
| Hook, `.py` | Arquivo com f-string válida só a partir do 3.12 | exit 2, erro do 3.11 devolvido ao modelo |
| Hook, travessão | `new_string` com U+2014 | exit 2, linha apontada |
| Hook, `.eleph` | `booking.eleph`, `booking_buggy.eleph` e um arquivo quebrado | PROVADO e REPROVADO como contexto; o quebrado deu exit 2 |
| Negar `git tag` | `claude -p` pedindo `git tag v9.9.9` | Negado (`permission_denials`); nenhuma tag criada |
| Negar `.env` | `claude -p` mandando chamar `Read` no `.env` | `File is in a directory that is denied by your permission settings.` |
| MCP | `claude -p` chamando `mcp__eleph-local__eleph_check` com o `booking_buggy.eleph` | REPROVADO, com o contraexemplo |
| Subagente | Auditoria das linhas 150, 172 e 376 do README | Ver abaixo |

## A tarefa real

> Adicione um exemplo novo em examples/: uma política de biblioteca. Um livro
> só pode ser emprestado se não estiver emprestado, a devolução só é aceita
> para livro emprestado, e o sistema responde a quem pergunta se o livro está
> emprestado. Inclua também uma variante com defeito que o verificador
> reprove, como os outros *_buggy. Deixe o repositório pronto para revisão,
> sem commit.

### Método

Rodei a mesma tarefa duas vezes com `claude -p`, em duas worktrees do mesmo
commit (`d1230f3`):

- **sem configuração:** o repositório como está no `main`;
- **com configuração:** os arquivos deste relatório copiados para a worktree.

Nas duas execuções usei o mesmo modelo (Sonnet), o mesmo prompt, o modo
`acceptEdits` e a mesma lista de ferramentas liberadas pela linha de comando
(`Bash(uv run:*)`, `git status`, `git diff`, leitura e escrita). A lista vai
pela linha de comando porque, em modo headless numa worktree que nunca passou
pelo diálogo de confiança, o Claude Code ignora o `allow` do `settings.json` do
projeto. O `deny` e os hooks continuam valendo. Os dois ambientes têm a mesma
configuração global da minha máquina, incluindo o plugin `eleph` instalado
pelo PyPI.

### Resultado

| | Sem configuração | Com configuração |
|---|---|---|
| Política correta e variante com defeito | Sim (`library*.eleph`) | Sim (`biblioteca*.eleph`) |
| Verificou com `eleph check` | **Não.** Tentou `eleph check` sem `uv run` e o MCP do plugin; as 6 chamadas foram negadas. | **Sim.** `uv run eleph check`, o comando do CLAUDE.md, e o hook devolveu o veredito a cada `Write` |
| Entrou no loop de exemplos do `ci.yml` | **Não.** Percebeu a lista e devolveu a decisão para mim | **Sim**, cada arquivo do lado certo (PROVADO e REPROVADO) |
| Entrou em `test_the_examples_still_take_the_fast_path` | Não | Sim |
| Rodou a suíte | Não | Sim, 154 passaram (venv sem o extra `langchain`) |
| Turnos, tempo e custo | 17, 43 s, US$ 0,18 | 16, 59 s, US$ 0,18 |

Conferi os quatro arquivos de forma independente: os dois corretos dão
PROVADO e os dois com defeito, REPROVADO. Ou seja, o modelo sem configuração
também escreveu uma política correta. A diferença está em outro lugar: ele
entregou algo que **não verificou** e que **ficaria fora do CI**. Num projeto
cuja tese é "não acredite numa regra sem checar", esse é exatamente o defeito
que importa.

### O que mudou no resultado e por quê

1. **Comando exato venceu permissão.** O modelo sem configuração sabia que
   precisava rodar o verificador, mas chamou `eleph check` direto, e esse
   comando não estava liberado. O CLAUDE.md dava `uv run eleph check`, que
   estava. A lição prática: comando exato no CLAUDE.md e regra de permissão
   precisam falar a mesma coisa.
2. **Convenção escrita virou mudança feita.** "Exemplo novo entra no `ci.yml` e
   no teste do fast path" só existia na cabeça do mantenedor. Escrita no
   CLAUDE.md, ela foi cumprida sem que eu pedisse.
3. **O hook fechou o ciclo sem custo de turno.** O veredito de cada `.eleph`
   chegou como contexto logo depois da escrita, sem o modelo precisar lembrar
   de rodar nada.
4. **Custo igual, um pouco mais lento.** O tempo a mais é o da execução dos
   testes e do verificador, que é justamente o trabalho que faltava na outra
   execução.

O resultado da execução configurada está neste branch:
`examples/biblioteca.eleph`, `examples/biblioteca_buggy.eleph` e as duas
linhas novas no `ci.yml` e no `tests/test_incremental.py`. Rodei localmente
cada passo do CI: pytest em 3.13 com os extras do CI (164 passaram) e em 3.11
(144 passaram e 2 foram pulados, sem o extra `mcp`), o loop de exemplos, o
`agente.py`, o checador de blocos do site (16 programas, 0 rejeitados) e o
`uv build`.

### O subagente numa auditoria real

Pedi ao `auditor-de-numeros` que auditasse três números do README:

- **"46 events per second"** (linha 150): NÃO SUSTENTADO, sem fonte no
  repositório. Conferi com grep: o número só aparece em cópias do próprio
  README (traduções e site). Fica como pendência real do projeto.
- **"145,564 events in 6.1 s"** (linha 172): NÃO VERIFICADO. Só se confirma
  rodando `bench/scaling.py`, e o subagente não executa nada.
- **"164 tests"** (linha 376): NÃO VERIFICADO. Rodei a suíte com os extras do
  CI (`dev,mcp,langchain`) e deram exatamente 164. O número está certo, e o
  subagente acertou ao não chamá-lo de errado sem executar.

Ele não editou nada (as ferramentas não permitem) e respondeu no formato
pedido. Uma ressalva: no primeiro item, ele foi além da evidência e estimou
por extrapolação que o número "contradiz" a tabela. Considero só a parte
verificável: falta fonte.

## Limites desta avaliação

- Foi **uma** execução de cada lado. Mostra a direção do efeito, não mede a
  sua frequência. Outra amostra do modelo sem configuração poderia ter
  acertado o comando.
- A skill `preparar-release` não foi exercitada pela tarefa, porque a tarefa
  não era um release. Testei separadamente os comandos dela que não publicam
  (pytest com `--isolated --python 3.11`, `uv build`).
- A execução configurada não chamou o MCP `eleph-local`; preferiu a CLI, que
  dá o mesmo veredito. O MCP foi testado à parte.
- O experimento rodou com a versão anterior do hook (com `uv run`). A troca
  para o binário do `.venv` veio dele e foi testada depois, com os mesmos
  casos.
- Os ambientes compartilham a minha configuração global. A diferença medida é
  a da configuração do projeto, nesta máquina.
