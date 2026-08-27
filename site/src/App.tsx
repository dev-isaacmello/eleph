import { Route, Routes } from 'react-router-dom'

import { Layout } from './components/Layout'
import { DocPage } from './pages/DocPage'
import { Home } from './pages/Home'

export function App() {
  return (
    <Routes>
      <Route element={<Layout withSidebar={false} />}>
        <Route path="/" element={<Home />} />
      </Route>
      <Route element={<Layout withSidebar />}>
        <Route path="/docs/*" element={<DocPage />} />
        <Route path="*" element={<DocPage />} />
      </Route>
    </Routes>
  )
}
