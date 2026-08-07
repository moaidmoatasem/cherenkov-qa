/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

import { useEffect, useState } from 'react';

export type Density = 'comfortable' | 'compact';

export const DENSITY_KEY = '[cherenkov] ui_density';
export const DENSITY_CHANGED_EVENT = 'density-changed';

function readDensity(): Density {
  try {
    const value = localStorage.getItem(DENSITY_KEY);
    return value === 'compact' ? 'compact' : 'comfortable';
  } catch {
    return 'comfortable';
  }
}

function applyDensity(density: Density): void {
  document.documentElement.dataset.density = density;
}

/**
 * Persist a density preference. Writes localStorage, applies the data-density
 * attribute, and notifies every mounted hook via a same-document event.
 */
export function setDensity(density: Density): void {
  try {
    localStorage.setItem(DENSITY_KEY, density);
  } catch {
    /* storage full or blocked -- the session still gets the density */
  }
  applyDensity(density);
  window.dispatchEvent(new CustomEvent(DENSITY_CHANGED_EVENT));
}

/**
 * Global Comfortable/Compact density preference (FE_RECOMMENDATIONS §6).
 * Persisted in localStorage and reflected as data-density on <html>, which the
 * global stylesheet turns into tightened spacing. A single instance is mounted
 * in App.tsx so the attribute is applied on load; consumers may call it too,
 * the effect is idempotent.
 */
export function useDensity(): Density {
  const [density, setDensityState] = useState<Density>(() => {
    if (typeof window === 'undefined') return 'comfortable';
    return readDensity();
  });

  useEffect(() => {
    applyDensity(density);
  }, [density]);

  useEffect(() => {
    const sync = () => setDensityState(readDensity());
    window.addEventListener(DENSITY_CHANGED_EVENT, sync);
    window.addEventListener('storage', sync);
    return () => {
      window.removeEventListener(DENSITY_CHANGED_EVENT, sync);
      window.removeEventListener('storage', sync);
    };
  }, []);

  return density;
}
