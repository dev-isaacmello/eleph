# eleph documentation site

The official documentation for [eleph](https://github.com/dev-isaacmello/eleph),
built with Vite, React and MDX, and deployed on Vercel.

```bash
npm install
npm run dev        # http://localhost:5173
npm run build      # -> dist/
npm run preview
```

## How it is put together

| Piece | Where | Note |
|---|---|---|
| Content | `src/content/<locale>/**.mdx` | one file per page; the path is the route |
| Sidebar | `src/lib/nav.ts` | the single registry: routes, titles per language, pager, breadcrumbs |
| Chrome strings | `src/lib/ui.ts` | everything the shell says, per language |
| Landing copy | `src/pages/home-copy.tsx` | the home page is layout, not prose, so its copy lives apart |
| Routing | `src/lib/content.ts` | `import.meta.glob`, lazily, so every page is its own chunk |
| Search | `scripts/build-search-index.mjs` | one record per heading, generated before `dev` and `build` |
| Sitemap, robots | same script | generated from the same walk, so they cannot drift from the content |
| Markdown for agents | `scripts/mdx-to-markdown.mjs` | every page also written as `.md`, plus `llms.txt` and `llms-full.txt` |
| Program check | `scripts/check-eleph-blocks.py` | runs the real checker over every `eleph` block on the site; wired into CI |
| Origin | `scripts/origin.mjs` | no domain is written down anywhere; the build reads Vercel's |
| Highlighting | `src/lib/eleph-grammar.ts` | TextMate grammars for `.eleph` and for what the CLI prints |
| CJK line breaks | `scripts/remark-cjk-linebreaks.mjs` | drops the space a wrapped source line would otherwise insert mid-word in Chinese |
| Design tokens | `src/styles/tokens.css` | the only place a colour is written; both themes |

Adding a page is three steps: write `src/content/en/<path>.mdx`, add the route
and its title per language to `src/lib/nav.ts`, then write the translation in
each `src/content/<locale>/<path>.mdx`.

## Languages

English is the default and lives at the root. Every other locale carries a path
prefix: `/pt-BR/docs/...`, `/zh-CN/docs/...`.

Routes are stored canonically (`/docs/...`) everywhere — in `nav.ts`, in the
search index, and in links written inside MDX. The prefix is applied at render.
That is what lets the language menu keep you on the page you were reading, and
it means a translated page never has to remember to prefix its own links.

A page with no translation falls back to English rather than 404ing
(`resolvePage` in `src/lib/content.ts`), so a partially translated locale is
always usable. The language menu drops you at that locale's `/docs` index when
the page you are on has no translation, rather than pretending.

Adding a locale: add it to `LOCALES` in `nav.ts` with its `htmlLang`, add its
titles to `TITLES`, add its strings to `src/lib/ui.ts` and its landing copy to
`src/pages/home-copy.tsx`, then create `src/content/<locale>/`. Routing,
search, the sitemap and `hreflang` follow from the content directory.

`README_TRANSLATIONS` holds languages the project has as translated READMEs but
not as pages here. They belong in the footer, never in the language menu.

### Writing Chinese

A soft line break inside a paragraph is a space, which is right for Latin
script and wrong for Han: it opens a gap in the middle of a word purely because
the source was wrapped. `scripts/remark-cjk-linebreaks.mjs` drops the break
when the characters on both sides of it are CJK, so `.mdx` files can be wrapped
normally.

**It does not reach JSX.** A Chinese string in a `.tsx` file (the landing copy,
the footer citation) must not be wrapped between two CJK characters, including
across `，` and `。`, because JSX collapses that break into a space and no
plugin runs on it. Keep those on one long line.

## Fence languages

````text
```eleph     a program
```out       what the CLI printed, coloured like the terminal
```python    the embedding API
```bash      a shell command
```text      a grammar, a session script, anything unhighlighted
````

## Markdown for agents

Every page is written twice at build time: as MDX for the browser, and as
Markdown at the same path with `.md` appended. `/llms.txt` indexes them in
reading order, taken from `nav.ts` so it cannot disagree with the sidebar;
`/llms-full.txt` is the English corpus in one file. All of it comes from the
same walk as the search index and the sitemap, so none of it can drift.

The conversion keeps what the components mean rather than dropping the tags: a
Callout becomes a labelled blockquote, a Snippet keeps the file it quotes, a
Source becomes the path. **Code fences are never touched.**

None of it is committed; `npm run index` writes it.

## The rule this site inherits

Every terminal block here is **a real run, pasted**. If the CLI's output
changes, the pages quoting it need re-pasting rather than editing. The project
rule is in [CONTRIBUTING.md](../CONTRIBUTING.md): do not publish a number you
have not read by hand.

The same applies to programs. `scripts/check-eleph-blocks.py` hands every
complete program printed on the site to `eleph check` and fails on a parser or
resolver rejection, and CI runs it. It is honest about what it cannot do:
excerpts have no program around them, and inventing one would test the
invention rather than the page, so those are counted and skipped rather than
faked.

## Deploying

Vercel, with **Root Directory** set to `site/`. Framework detection picks up
Vite; `vercel.json` pins the build command, the output directory and the SPA
rewrite that makes deep links work.

**No domain is hardcoded.** The build resolves its own origin, in order:

1. `SITE_ORIGIN`, if you set it — the escape hatch for a custom domain the
   build cannot see;
2. `VERCEL_PROJECT_PRODUCTION_URL`, a Vercel system variable set on every
   deployment, previews included, naming the production domain;
3. `VERCEL_URL`, the per-deployment host;
4. nothing.

"Nothing" is a supported answer, and it is what a local build gets: the head
falls back to root-relative URLs, which are correct on whatever host serves
them, and the sitemap is skipped rather than written against a guessed domain.
The canonical link is then rewritten per route in the browser from
`location.origin`, so it is right even on a host the build was never told
about.
