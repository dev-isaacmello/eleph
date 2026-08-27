import {
  Children,
  createContext,
  isValidElement,
  useCallback,
  useContext,
  useRef,
  useState,
  type ComponentPropsWithoutRef,
  type ReactNode,
} from 'react'
import { Link } from 'react-router-dom'

import { useLocale } from '@/lib/locale'
import { source } from '@/lib/site'
import {
  IconAlert,
  IconCheck,
  IconCopy,
  IconExternal,
  IconInfo,
  IconLink,
  IconShield,
} from './Icons'

/* ------------------------------------------------------------ code blocks */

/**
 * True while we are already inside a code shell (a `<Snippet>`), so the `pre`
 * override renders a bare block instead of wrapping it in a second frame with
 * a second copy button.
 */
const InShell = createContext(false)

/** Pull the language back out of the class Shiki put on the `<code>`. */
function languageOf(children: ReactNode): string | null {
  const only = Children.toArray(children)[0]
  if (!isValidElement(only)) return null
  const cls = (only.props as { className?: string }).className ?? ''
  const found = /language-([\w-]+)/.exec(cls)
  if (!found) return null
  return found[1] === 'eleph-output' ? 'output' : found[1]
}

function CopyButton({ target }: { target: React.RefObject<HTMLDivElement | null> }) {
  const [copied, setCopied] = useState(false)
  const { t } = useLocale()

  const copy = useCallback(async () => {
    const text = target.current?.querySelector('code')?.textContent ?? ''
    try {
      await navigator.clipboard.writeText(text)
      setCopied(true)
      setTimeout(() => setCopied(false), 1600)
    } catch {
      /* clipboard denied; the block is selectable either way */
    }
  }, [target])

  return (
    <button
      type="button"
      className="copy-button"
      data-copied={copied}
      onClick={copy}
      aria-label={copied ? t.copied : t.copyCode}
    >
      {copied ? <IconCheck /> : <IconCopy />}
      {copied ? t.copied : t.copy}
    </button>
  )
}

export function CodeBlock({
  title,
  language,
  children,
}: {
  title?: string
  language?: string | null
  children: ReactNode
}) {
  const box = useRef<HTMLDivElement>(null)
  return (
    <div className="code-block" ref={box}>
      {title ? (
        <div className="code-block__head">
          <span>{title}</span>
          {language ? <span className="code-block__lang">{language}</span> : null}
        </div>
      ) : null}
      {children}
      <CopyButton target={box} />
    </div>
  )
}

function Pre(props: ComponentPropsWithoutRef<'pre'>) {
  const nested = useContext(InShell)
  if (nested) return <pre {...props} />
  return (
    <CodeBlock language={languageOf(props.children)}>
      <pre {...props} />
    </CodeBlock>
  )
}

/**
 * A code block that says which file in the repository it came from, and links
 * there. Quoting a file without saying which one is how docs drift.
 */
export function Snippet({
  file,
  title,
  children,
}: {
  file?: string
  title?: string
  children: ReactNode
}) {
  const box = useRef<HTMLDivElement>(null)
  const label = title ?? file
  return (
    <div className="code-block" ref={box}>
      <div className="code-block__head">
        {file ? (
          <a href={source.file(file)} target="_blank" rel="noreferrer">
            {label} <IconExternal />
          </a>
        ) : (
          <span>{label}</span>
        )}
      </div>
      <InShell.Provider value={true}>{children}</InShell.Provider>
      <CopyButton target={box} />
    </div>
  )
}

/* ---------------------------------------------------------------- tables */

function Table(props: ComponentPropsWithoutRef<'table'>) {
  return (
    <div className="table-wrap scroll-thin">
      <table {...props} />
    </div>
  )
}

/* -------------------------------------------------------------- headings */

function heading(Tag: 'h2' | 'h3' | 'h4') {
  return function Heading({ id, children, ...rest }: ComponentPropsWithoutRef<'h2'>) {
    return (
      <Tag id={id} className="heading-anchor" {...rest}>
        {id ? (
          <a className="heading-anchor__link" href={`#${id}`} aria-label="Link to this section">
            <IconLink />
          </a>
        ) : null}
        {children}
      </Tag>
    )
  }
}

/* --------------------------------------------------------------- callout */

const CALLOUTS = {
  note: { icon: IconInfo, key: 'calloutNote' },
  proved: { icon: IconShield, key: 'calloutProved' },
  limit: { icon: IconAlert, key: 'calloutLimit' },
  danger: { icon: IconAlert, key: 'calloutDanger' },
} as const

export function Callout({
  type = 'note',
  title,
  children,
}: {
  type?: keyof typeof CALLOUTS
  title?: string
  children: ReactNode
}) {
  const { icon: Icon, key } = CALLOUTS[type]
  const { t } = useLocale()
  return (
    <div className={`callout callout--${type}`}>
      <Icon width={17} height={17} />
      <div className="callout__body">
        <strong className="callout__label">{title ?? t[key]}</strong>
        {children}
      </div>
    </div>
  )
}

/* ----------------------------------------------------------------- links */

/**
 * Internal links route; external ones open away and say so.
 *
 * Pages write links canonically (`/docs/...`) and this applies the reader's
 * locale, so a translated page does not have to remember to prefix every link
 * and cannot drop you back into English halfway through.
 */
function Anchor({ href = '', children, ...rest }: ComponentPropsWithoutRef<'a'>) {
  const { href: localised } = useLocale()

  // A Markdown or text endpoint is a file the server hands over, not a route
  // the router knows. Sending it through the router lands on "page not found".
  const isFile = /\.(md|txt|json|xml)$/.test(href)

  if (href.startsWith('/') && !isFile) {
    return (
      <Link to={localised(href)} {...rest}>
        {children}
      </Link>
    )
  }
  if (href.startsWith('/')) {
    // A page's Markdown lives beside the page, so it takes the locale. The
    // index files live at the root and do not.
    const to = href.startsWith('/docs/') || href === '/docs.md' ? localised(href) : href
    return (
      <a href={to} {...rest}>
        {children}
      </a>
    )
  }
  if (href.startsWith('#')) {
    return (
      <a href={href} {...rest}>
        {children}
      </a>
    )
  }
  return (
    <a href={href} target="_blank" rel="noreferrer" {...rest}>
      {children}
    </a>
  )
}

/** A link to a file in the repository, formatted as the path it is. */
export function Source({ file: path, children }: { file: string; children?: ReactNode }) {
  const href = /\.[a-z]+$/.test(path) ? source.file(path) : source.tree(path)
  return (
    <a className="source-link" href={href} target="_blank" rel="noreferrer">
      {children ?? path} <IconExternal />
    </a>
  )
}

export function Steps({ children }: { children: ReactNode }) {
  return <ol className="steps">{children}</ol>
}

export const mdxComponents = {
  pre: Pre,
  table: Table,
  a: Anchor,
  h2: heading('h2'),
  h3: heading('h3'),
  h4: heading('h4'),
  Callout,
  Snippet,
  Source,
  Steps,
  CodeBlock,
}
