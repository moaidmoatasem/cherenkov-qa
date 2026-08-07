/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

import { useEffect, type RefObject } from 'react';

const FOCUSABLE_SELECTOR =
  'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])';

/**
 * Real focus trap for modals and drawers (FE_RECOMMENDATIONS §6: rigorous
 * focus management). While `active` is true:
 *   - focus is moved to the first focusable element inside the container,
 *   - Tab / Shift+Tab are constrained to the container,
 *   - focus is returned to the element that had it before the trap opened.
 */
export function useFocusTrap(
  ref: RefObject<HTMLElement | null>,
  active: boolean
): void {
  useEffect(() => {
    if (!active) return;
    const container = ref.current;
    if (!container) return;

    const previouslyFocused =
      document.activeElement instanceof HTMLElement
        ? document.activeElement
        : null;

    const getFocusable = () =>
      Array.from(container.querySelectorAll<HTMLElement>(FOCUSABLE_SELECTOR)).filter(
        (el) =>
          !el.hasAttribute('disabled') &&
          el.getAttribute('aria-hidden') !== 'true' &&
          el.offsetParent !== null
      );

    const focusables = getFocusable();
    if (focusables.length > 0) focusables[0].focus();

    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key !== 'Tab') return;
      const current = getFocusable();
      if (current.length === 0) {
        e.preventDefault();
        return;
      }
      const first = current[0];
      const last = current[current.length - 1];
      const activeEl = document.activeElement as HTMLElement | null;
      if (e.shiftKey && (activeEl === first || !container.contains(activeEl))) {
        e.preventDefault();
        last.focus();
      } else if (!e.shiftKey && (activeEl === last || !container.contains(activeEl))) {
        e.preventDefault();
        first.focus();
      }
    };

    document.addEventListener('keydown', handleKeyDown, true);
    return () => {
      document.removeEventListener('keydown', handleKeyDown, true);
      previouslyFocused?.focus?.();
    };
  }, [ref, active]);
}
