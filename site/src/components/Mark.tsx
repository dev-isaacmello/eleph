/**
 * The eleph mark: two quotation marks that are also two trunks.
 *
 * The stroke is `currentColor` rather than a fixed hex, so one component
 * serves both themes and the accent token stays the single place the colour
 * is decided. The geometry is `public/assets/svg/eleph-mark.svg`, unchanged.
 */
export function Mark({ size = 26, className }: { size?: number; className?: string }) {
  return (
    <svg
      className={className}
      viewBox="0 0 64 64"
      width={size}
      height={size}
      role="img"
      aria-label="eleph"
      focusable="false"
    >
      <g
        fill="none"
        stroke="currentColor"
        strokeWidth="5.4"
        strokeLinecap="round"
      >
        <path d="M9.4 16c12.1 0 19.7 7.7 19.7 17.3 0 8.5-6.2 14.2-13.6 12.8" />
        <path d="M35 16c12.1 0 19.7 7.7 19.7 17.3 0 8.5-6.2 14.2-13.6 12.8" />
      </g>
    </svg>
  )
}
