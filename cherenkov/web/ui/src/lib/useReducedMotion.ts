import { useEffect, useState } from 'react';

/**
  * Custom hook to detect prefers-reduced-motion media query and localStorage override.
  */
export function useReducedMotion(): boolean {
  const [reducedMotion, setReducedMotion] = useState<boolean>(() => {
    // Initial check
    if (typeof window === 'undefined') return false;

    // Check localStorage override
    const override = localStorage.getItem('prefers-reduced-motion');
    if (override === 'reduce') return true;
    if (override === 'no-preference') return false;

    // Fallback to system preference
    return window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  });

  useEffect(() => {
    if (typeof window === 'undefined') return;

    const mediaQuery = window.matchMedia('(prefers-reduced-motion: reduce)');
    const listener = (event: MediaQueryListEvent) => {
      // Only apply system change if there's no localStorage override
      const override = localStorage.getItem('prefers-reduced-motion');
      if (!override) {
        setReducedMotion(event.matches);
      }
    };

    mediaQuery.addEventListener('change', listener);
    return () => mediaQuery.removeEventListener('change', listener);
  }, []);

  // Listen to storage events to stay in sync if changed in another window/settings panel
  useEffect(() => {
    const handleStorageChange = () => {
      const override = localStorage.getItem('prefers-reduced-motion');
      if (override === 'reduce') {
        setReducedMotion(true);
      } else if (override === 'no-preference') {
        setReducedMotion(false);
      } else {
        setReducedMotion(window.matchMedia('(prefers-reduced-motion: reduce)').matches);
      }
    };

    window.addEventListener('storage', handleStorageChange);
    // Custom event dispatch setup for same-document changes
    window.addEventListener('reduced-motion-changed', handleStorageChange);

    return () => {
      window.removeEventListener('storage', handleStorageChange);
      window.removeEventListener('reduced-motion-changed', handleStorageChange);
    };
  }, []);

  return reducedMotion;
}
