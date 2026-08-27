/**
 * Where this build will be served from.
 *
 * Nothing here is written down as a domain, because the domain is Vercel's to
 * choose. `VERCEL_PROJECT_PRODUCTION_URL` is a system environment variable set
 * on every deployment -- including previews, where it still names the
 * production domain, which is what a canonical link and a sitemap want.
 *
 * Order: an explicit override, then the project's production domain, then the
 * per-deployment URL, then nothing. "Nothing" is a supported answer: the site
 * falls back to root-relative URLs, which are correct on whatever host serves
 * them, and the sitemap is simply not written.
 *
 * @returns {string} an origin with no trailing slash, or '' if unknown
 */
export function resolveOrigin(env = process.env) {
  const raw =
    env.SITE_ORIGIN ||
    env.VERCEL_PROJECT_PRODUCTION_URL ||
    env.VERCEL_URL ||
    ''
  if (!raw) return ''
  const withScheme = /^https?:\/\//.test(raw) ? raw : `https://${raw}`
  return withScheme.replace(/\/+$/, '')
}
