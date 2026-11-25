import React, { useState, useEffect } from 'react';
import emblemDark from '../../assets/branding/aerovital-emblem-dark.png';
import emblemLight from '../../assets/branding/aerovital-emblem-light.png';

const SIZE_MAP = {
  sm: 32,
  md: 44,
  lg: 64,
  xl: 108,
  hero: 140,
};

/**
 * Reusable AeroVital Official Emblem Component
 * Respects original 1:1 proportions and switches cleanly between dark and light variants.
 */
export function BrandLogo({
  variant = 'auto',
  size = 'md',
  showText = false,
  subtitle = null,
  className = '',
  alt = 'AeroVital Official Aircraft Emblem',
}) {
  const [isDarkTheme, setIsDarkTheme] = useState(false);

  useEffect(() => {
    // Check if body has dark-theme or dark mode
    const checkTheme = () => {
      const prefersDark = typeof window !== 'undefined' && typeof window.matchMedia === 'function'
        ? window.matchMedia('(prefers-color-scheme: dark)').matches
        : false;
      const isDark = (typeof document !== 'undefined' && document.body?.classList.contains('dark-theme')) || prefersDark;
      setIsDarkTheme(isDark);
    };

    checkTheme();

    const observer = new MutationObserver(() => checkTheme());
    observer.observe(document.body, { attributes: true, attributeFilter: ['class'] });

    return () => observer.disconnect();
  }, []);

  const pixelSize = typeof size === 'number' ? size : (SIZE_MAP[size] || SIZE_MAP.md);

  // Determine active logo variant
  const activeLogo = variant === 'dark'
    ? emblemDark
    : variant === 'light'
      ? emblemLight
      : (isDarkTheme ? emblemDark : emblemLight);

  return (
    <div className={`brand-logo-lockup ${className}`} style={{ display: 'inline-flex', alignItems: 'center', gap: '12px' }}>
      <img
        src={activeLogo}
        alt={alt}
        width={pixelSize}
        height={pixelSize}
        style={{
          width: `${pixelSize}px`,
          height: `${pixelSize}px`,
          objectFit: 'contain',
          aspectRatio: '1 / 1',
          borderRadius: pixelSize > 48 ? '16px' : '8px',
          display: 'block',
          flexShrink: 0,
        }}
      />
      {showText && (
        <div className="brand-logo-text-group" style={{ display: 'flex', flexDirection: 'column' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <span
              className="brand-title"
              style={{
                fontFamily: 'var(--font-main)',
                fontWeight: 800,
                letterSpacing: '0.08em',
                fontSize: pixelSize >= 64 ? '22px' : '17px',
                lineHeight: 1.1,
                color: 'var(--text-primary)',
                textTransform: 'uppercase',
              }}
            >
              AeroVital
            </span>
            <span
              className="brand-tricolour-pill"
              title="Official Indian Tricolour Brand Signature"
              style={{
                display: 'inline-block',
                width: '18px',
                height: '4px',
                borderRadius: '2px',
                background: 'linear-gradient(90deg, #FF9933 33.3%, #FFFFFF 33.3%, #FFFFFF 66.6%, #138808 66.6%)',
              }}
            />
          </div>
          {subtitle && (
            <span
              style={{
                fontSize: '11px',
                fontWeight: 600,
                color: 'var(--text-secondary)',
                letterSpacing: '0.04em',
                textTransform: 'uppercase',
                marginTop: '2px',
              }}
            >
              {subtitle}
            </span>
          )}
        </div>
      )}
    </div>
  );
}

export default BrandLogo;
