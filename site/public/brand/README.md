# eleph — brand assets

The mark: two quotation marks that are also two trunks. One stroke weight (5.4
on a 64 grid), one colour, no fill. Minimum size 16px. Clear space on all four
sides is a quarter of the mark's height.

| colour | on | hex |
|---|---|---|
| accent | paper | `#1668c5` |
| accent | dark | `#71a8ef` |
| ink | paper | `#1b1917` |
| paper | ink or accent | `#fffefb` |

Every value above is a token from `site/src/styles/tokens.css`. The wordmark is
Newsreader; the tile is the same `rx="7"` on 32 that `site/public/favicon.svg`
already uses.

`svg/favicon.svg` and `svg/og.svg` are drop-in replacements for the two files
in `site/public/`, and are already installed there.

This kit lives at `site/public/brand/`, not under `assets/`, because `assets/`
is where Vite writes content-hashed bundles and `vercel.json` marks that path
`immutable` for a year. These files carry no hash, so a logo change would have
been invisible to anyone who had already loaded the old one.

## Contents

```
svg/  eleph-mark.svg            accent, for paper
      eleph-mark-dark.svg       accent, for dark
      eleph-mark-ink.svg        one colour, ink
      eleph-mark-paper.svg      one colour, reversed
      eleph-lockup.svg          mark and wordmark
      eleph-lockup-dark.svg
      eleph-lockup-mono-ink.svg
      eleph-lockup-mono-paper.svg
      favicon.svg               ink tile, accent glyph   -> site/public/favicon.svg
      favicon-paper.svg         paper tile, accent glyph
      og.svg                    1200x630 card            -> site/public/og.svg

png/  eleph-mark-{512,256,128,64,32,16}.png       accent, transparent
      eleph-mark-{dark,ink,paper}-{512,128}.png   transparent
      favicon-{512,180,64,32,16}.png              180 is the iOS touch icon
      favicon-paper-512.png
      eleph-lockup.png                            1912x528, transparent
      og.png
```

The lockup SVGs set the wordmark as live Newsreader text, so a machine without
that font falls back to Georgia. `png/eleph-lockup.png` is the same lockup with
the real font baked in — ink on transparent, so it is for light backgrounds
only; on dark, use `svg/eleph-lockup-dark.svg`.
