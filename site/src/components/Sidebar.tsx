import { NavLink } from 'react-router-dom'

import { nav, DEFAULT_LOCALE } from '@/lib/nav'

export function Sidebar({ open, onClose }: { open: boolean; onClose: () => void }) {
  return (
    <>
      {open ? (
        <button
          type="button"
          className="sidebar__scrim"
          aria-label="Close navigation"
          onClick={onClose}
        />
      ) : null}

      <nav
        id="sidebar"
        className="sidebar scroll-thin"
        data-open={open}
        aria-label="Documentation"
      >
        {nav[DEFAULT_LOCALE].map((group) => (
          <div className="sidebar__group" key={group.title}>
            <h2 className="sidebar__title">{group.title}</h2>
            <ul className="sidebar__list">
              {group.items.map((item) => (
                <li key={item.href}>
                  <NavLink to={item.href} end className="sidebar__link" onClick={onClose}>
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
