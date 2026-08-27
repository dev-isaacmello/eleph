import { Route, Routes } from 'react-router-dom'

import { Layout } from './components/Layout'
import { DEFAULT_LOCALE, LOCALES } from './lib/nav'
import { DocPage } from './pages/DocPage'
import { Home } from './pages/Home'

/** Every locale but the default carries a path prefix. */
const PREFIXED = LOCALES.filter((l) => l.code !== DEFAULT_LOCALE).map((l) => l.code)

export function App() {
  return (
    <Routes>
      <Route element={<Layout withSidebar={false} />}>
        <Route path="/" element={<Home />} />
        {PREFIXED.map((code) => (
          <Route key={code} path={`/${code}`} element={<Home />} />
        ))}
      </Route>

      <Route element={<Layout withSidebar />}>
        <Route path="/docs/*" element={<DocPage />} />
        {PREFIXED.map((code) => (
          <Route key={code} path={`/${code}/docs/*`} element={<DocPage />} />
        ))}
        <Route path="*" element={<DocPage />} />
      </Route>
    </Routes>
  )
}
