/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

import React from 'react';
import { Link } from 'react-router-dom';
import { Home, ChevronRight } from 'lucide-react';

export interface BreadcrumbCrumb {
  label: string;
  /** Omit to render the final crumb as plain text (the current location). */
  to?: string;
  title?: string;
}

export interface BreadcrumbsProps {
  trail: BreadcrumbCrumb[];
}

/**
 * Deep-linkable breadcrumb trail rendered below the top bar. The home crumb
 * always links back to the dashboard; the current location is plain text so it
 * is never a dead link to itself. Rendered as an <ol> so screen readers see a
 * real list -- deliberately not a <nav> so the sidebar remains the page's one
 * navigation landmark.
 */
export function Breadcrumbs({ trail }: BreadcrumbsProps) {
  return (
    <div className="px-6 py-2 border-b border-border-subtle bg-bg-surface/60 text-[11px] font-mono text-text-muted select-none shrink-0" data-testid="breadcrumbs">
      <ol className="flex items-center gap-1.5 overflow-x-auto whitespace-nowrap" aria-label="Breadcrumb">
        <li>
          <Link
            to="/dashboard"
            className="inline-flex items-center gap-1 hover:text-cyan-400 transition-colors"
            data-testid="breadcrumb-home"
            aria-label="Go to dashboard"
          >
            <Home className="w-3 h-3" />
            Home
          </Link>
        </li>
        {trail.map((crumb, idx) => {
          const isLast = idx === trail.length - 1;
          return (
            <li key={idx} className="flex items-center gap-1.5">
              <ChevronRight className="w-3 h-3 text-text-muted/50" />
              {isLast || !crumb.to ? (
                <span
                  className={isLast ? 'text-text-primary font-semibold' : undefined}
                  aria-current={isLast ? 'page' : undefined}
                  title={crumb.title}
                >
                  {crumb.label}
                </span>
              ) : (
                <Link
                  to={crumb.to}
                  title={crumb.title}
                  className="hover:text-cyan-400 transition-colors"
                >
                  {crumb.label}
                </Link>
              )}
            </li>
          );
        })}
      </ol>
    </div>
  );
}

export default Breadcrumbs;
