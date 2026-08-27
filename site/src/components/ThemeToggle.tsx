import { useLocale } from '@/lib/locale'
import { useTheme } from '@/lib/theme'
import { IconMoon, IconSun } from './Icons'

export function ThemeToggle() {
  const { theme, toggle } = useTheme()
  const { t } = useLocale()
  return (
    <button
      type="button"
      className="icon-button"
      onClick={toggle}
      aria-label={theme === 'dark' ? t.themeToLight : t.themeToDark}
    >
      {theme === 'dark' ? <IconSun /> : <IconMoon />}
    </button>
  )
}
