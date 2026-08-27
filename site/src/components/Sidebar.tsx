import { NavLink } from 'react-router-dom'

import { useLocale } from '@/lib/locale'
import { nav } from '@/lib/nav'

export function Sidebar({
  open,
  onClose,
  drawerOnly = false,
}: {
  open: boolean
  onClose: () => void
  drawerOnly?: boolean
}) {
  const { locale, href, t } = useLocale()

  return (
    <>
      {open ? (
        <button
          type="button"
          className="sidebar__scrim"
          aria-label={t.closeNav}
          onClick={onClose}
        />
      ) : null}

      <nav
        id="sidebar"
        className={`sidebar scroll-thin${drawerOnly ? ' sidebar--drawer' : ''}`}
        data-open={open}
        aria-label={t.docsNav}
      >
        {nav(locale).map((group) => (
          <div className="sidebar__group" key={group.title}>
            <h2 className="sidebar__title">{group.title}</h2>
            <ul className="sidebar__list">
              {group.items.map((item) => (
                <li key={item.href}>
                  <NavLink
                    to={href(item.href)}
                    end
                    className="sidebar__link"
                    onClick={onClose}
                  >
                    <span>{item.title}</span>
                    {item.badge ? <span className="sidebar__badge">{item.badge}</span> : null}
                  </NavLink>
                </li>
              ))}
            </ul>
          </div>
        ))}
      </nav>
    </>
  )
}
