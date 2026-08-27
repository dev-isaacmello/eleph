import { Link, NavLink } from 'react-router-dom'

import { useLocale } from '@/lib/locale'
import { site } from '@/lib/site'
import { IconGitHub, IconMenu, IconClose } from './Icons'
import { LanguageMenu } from './LanguageMenu'
import { Mark } from './Mark'
import { Search } from './Search'
import { ThemeToggle } from './ThemeToggle'

export function Header({
  menuOpen,
  onToggleMenu,
}: {
  menuOpen: boolean
  onToggleMenu: () => void
}) {
  const { href, t } = useLocale()

  return (
    <header className="header">
      <button
        type="button"
        className="icon-button menu-button"
        onClick={onToggleMenu}
        aria-expanded={menuOpen}
        aria-controls="sidebar"
        aria-label={menuOpen ? t.closeNav : t.openNav}
      >
        {menuOpen ? <IconClose /> : <IconMenu />}
      </button>

      <Link to={href('/')} className="header__brand">
        <Mark className="header__mark" />
        <span>{site.name}</span>
      </Link>

      <a
        className="header__version"
        href={`${site.repo}/blob/main/CHANGELOG.md`}
        target="_blank"
        rel="noreferrer"
        title="Changelog"
      >
        v{site.version}
      </a>

      <nav className="header__nav" aria-label={t.primaryNav}>
        <NavLink to={href('/docs/use/start-here')}>{t.headerUse}</NavLink>
        <NavLink to={href('/docs')} end>
          {t.headerDocs}
        </NavLink>
        <NavLink to={href('/docs/reference/program-structure')}>{t.headerReference}</NavLink>
        <NavLink to={href('/docs/python-api')}>{t.headerApi}</NavLink>
      </nav>

      <span className="header__spacer" />

      <div className="header__actions">
        <Search />
        <LanguageMenu />
        <ThemeToggle />
        <a
          className="icon-button"
          href={site.repo}
          target="_blank"
          rel="noreferrer"
          aria-label="eleph on GitHub"
        >
          <IconGitHub />
        </a>
      </div>
    </header>
  )
}
