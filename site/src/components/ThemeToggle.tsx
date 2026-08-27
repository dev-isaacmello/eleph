import { useTheme } from '@/lib/theme'
import { IconMoon, IconSun } from './Icons'

export function ThemeToggle() {
  const { theme, toggle } = useTheme()
  return (
    <button
      type="button"
      className="icon-button"
      onClick={toggle}
      aria-label={theme === 'dark' ? 'Switch to light theme' : 'Switch to dark theme'}
      title={theme === 'dark' ? 'Light theme' : 'Dark theme'}
    >
      {theme === 'dark' ? <IconSun /> : <IconMoon />}
    </button>
  )
}
