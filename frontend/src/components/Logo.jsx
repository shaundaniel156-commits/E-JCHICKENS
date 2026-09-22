/**
 * The E&J's CHICKENS mark: an original egg silhouette holding a stylised hen.
 * Drawn inline so it inherits the surrounding colour and scales crisply.
 */
export default function Logo({ size = 34, showWordmark = false, tagline }) {
  return (
    <span style={{ display: 'inline-flex', alignItems: 'center', gap: 10 }}>
      <svg
        className="logo"
        width={size}
        height={size}
        viewBox="0 0 64 64"
        role="img"
        aria-label="E&J's Chickens"
      >
        <defs>
          <linearGradient id="ejc-shell" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="#f9f6ec" />
            <stop offset="100%" stopColor="#e7dfc6" />
          </linearGradient>
        </defs>
        <path
          d="M32 3c11.6 0 21 13.4 21 27.6C53 45.1 43.6 57 32 57S11 45.1 11 30.6C11 16.4 20.4 3 32 3Z"
          fill="url(#ejc-shell)"
          stroke="#14532d"
          strokeWidth="3"
        />
        <path
          d="M25.5 43.5c-2.6-2.1-4-5-4-8.4 0-5.6 4.3-10 9.9-10 1 0 2 .15 2.9.45.3-2.6 1.6-4.6 3.6-5.6-.5 1.9-.3 3.5.6 4.8 3.5 1.7 5.7 5.2 5.7 9.3 0 3.6-1.6 6.7-4.4 8.7v3.8H25.5Z"
          fill="#16a34a"
        />
        <path d="M35.6 20.2c1.1-2.2.8-4.3-.9-6.2 3 .5 4.9 2.3 5.4 5.2" fill="#d97706" />
        <circle cx="39.4" cy="31.4" r="1.7" fill="#14532d" />
        <path d="M43.8 33.9l4.4 1.9-4.4 2z" fill="#d97706" />
        <path d="M24 47.4h16.8" stroke="#14532d" strokeWidth="2.4" strokeLinecap="round" />
      </svg>
      {showWordmark && (
        <span style={{ display: 'flex', flexDirection: 'column', minWidth: 0 }}>
          <strong style={{ fontSize: '0.95rem', letterSpacing: '0.01em' }}>E&amp;J&apos;s CHICKENS</strong>
          {tagline && (
            <span style={{ fontSize: '0.7rem', opacity: 0.75, whiteSpace: 'nowrap' }}>{tagline}</span>
          )}
        </span>
      )}
    </span>
  )
}
