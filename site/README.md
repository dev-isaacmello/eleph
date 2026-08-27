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
| Origin | `scripts/origin.mjs` | no domain is written down anywhere; the build reads Vercel's |
| Highlighting | `src/lib/eleph-grammar.ts` | TextMate grammars for `.eleph` and for what the CLI prints |
| Design tokens | `src/styles/tokens.css` | the only place a colour is written; both themes |

Adding a page is three steps: write `src/content/en/<path>.mdx`, add the route
and its title per language to `src/lib/nav.ts`, then write the translation at
`src/content/pt-BR/<path>.mdx`.

## Languages

English is the default and lives at the root. Every other locale carries a path
prefix: `/pt-BR/docs/...`.

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

## Fence languages

````text
```eleph     a program
```out       what the CLI printed, coloured like the terminal
```python    the embedding API
```bash      a shell command
```text      a grammar, a session script, anything unhighlighted
````

## The rule this site inherits

Every terminal block here is **a real run, pasted**. If the CLI's output
changes, the pages quoting it need re-pasting rather than editing. The project
rule is in [CONTRIBUTING.md](../CONTRIBUTING.md): do not publish a number you
have not read by hand.

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
