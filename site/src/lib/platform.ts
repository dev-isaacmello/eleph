/**
 * Which modifier key to name in the UI.
 *
 * The shortcut handler already accepts either, because Cmd on a Mac and Ctrl
 * everywhere else are the same gesture. Only the label has to choose, and a
 * label that says Cmd on Windows is telling the reader to press a key their
 * keyboard does not have.
 */
function isApple(): boolean {
  if (typeof navigator === 'undefined') return false

  // userAgentData.platform is the one that is not deprecated; navigator
  // .platform is the one that exists in Firefox and Safari today.
  const data = (navigator as Navigator & { userAgentData?: { platform?: string } })
    .userAgentData
  const platform = data?.platform || navigator.platform || navigator.userAgent
  return /mac|iphone|ipad|ipod/i.test(platform)
}

/** `⌘K` on Apple hardware, `Ctrl K` everywhere else. */
export function shortcutLabel(key: string): string {
  return isApple() ? `⌘${key}` : `Ctrl ${key}`
}
