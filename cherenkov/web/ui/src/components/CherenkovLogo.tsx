import React from 'react';

interface CherenkovLogoProps {
  variant?: 'icon' | 'full' | 'wireframe';
  className?: string;
  size?: number | string;
  glow?: boolean;
}

export default function CherenkovLogo({
  variant = 'full',
  className = '',
  size = 36,
  glow = true,
}: CherenkovLogoProps) {
  // Common aspect ratio is 1:1 for icon and wireframe, but wider for full logo.
  const isFull = variant === 'full';

  return (
    <div className={`inline-flex items-center gap-3.5 select-none ${className}`} id={`cherenkov-logo-${variant}`}>
      <div className="relative flex items-center justify-center shrink-0">
        {/* Glow backdrop shadow element - match Image 1 and 2 glow atmosphere */}
        {glow && variant !== 'wireframe' && (
          <div className="absolute inset-0 bg-cyan-400/25 rounded-full blur-[14px] pointer-events-none scale-110 animate-pulse-slow" />
        )}

        {variant === 'wireframe' ? (
          // Isometric 3D Hexagon structure (Image 3)
          <svg
            width={size}
            height={size}
            viewBox="0 0 100 100"
            fill="none"
            xmlns="http://www.w3.org/2000/svg"
            className="text-white/30 hover:text-white/50 transition-colors"
          >
            {/* Outer Hexagon outline */}
            <path
              d="M 50,5 L 90,28 L 90,72 L 50,95 L 10,72 L 10,28 Z"
              stroke="currentColor"
              strokeWidth="4"
              strokeLinecap="round"
              strokeLinejoin="round"
            />
            {/* Inner Isometric Cube lines */}
            <line
              x1="50"
              y1="5"
              x2="50"
              y2="50"
              stroke="currentColor"
              strokeWidth="4"
              strokeLinecap="round"
            />
            <line
              x1="10"
              y1="72"
              x2="50"
              y2="50"
              stroke="currentColor"
              strokeWidth="4"
              strokeLinecap="round"
            />
            <line
              x1="90"
              y1="72"
              x2="50"
              y2="50"
              stroke="currentColor"
              strokeWidth="4"
              strokeLinecap="round"
            />
          </svg>
        ) : (
          // High-fidelity Neon Cyan-to-Purple Hexagon (Image 1 and logo)
          <svg
            width={size}
            height={size}
            viewBox="0 0 100 100"
            fill="none"
            xmlns="http://www.w3.org/2000/svg"
          >
            <defs>
              {/* Vibrant neon gradient from cyan to electric purple */}
              <linearGradient id="cherenkov-neon-grad" x1="100" y1="20" x2="0" y2="80" gradientUnits="userSpaceOnUse">
                <stop offset="0%" stopColor="#00f0ff" />
                <stop offset="40%" stopColor="#06b6d4" />
                <stop offset="100%" stopColor="#8b5cf6" />
              </linearGradient>
            </defs>

            {/* Glowing outer Pac-Hexagon outline with slight shadow */}
            <path
              d="M 50,7 L 90,30 L 59,50 L 90,70 L 50,93 L 10,70 L 10,30 Z"
              stroke="url(#cherenkov-neon-grad)"
              strokeWidth="8"
              strokeLinecap="round"
              strokeLinejoin="round"
              className="drop-shadow-[0_0_10px_rgba(0,240,255,0.4)]"
            />

            {/* Nested Solid triangle inside the right mouth cavity, pointing left */}
            <path
              d="M 85,38 L 61,50 L 85,62 Z"
              fill="#00f0ff"
              className="opacity-95"
            />

            {/* Forensic Reveal Dot indicator */}
            <circle
              cx="77"
              cy="50"
              r="4.5"
              fill="#ffffff"
              className="shadow-sm"
            />
          </svg>
        )}
      </div>

      {/* Text Label Logotype - Image 2 typography spacing */}
      {isFull && (
        <div className="flex flex-col select-none leading-none">
          <span className="font-sans font-black text-xl tracking-[0.16em] text-white">
            CHERENKOV
          </span>
          <span className="text-[8px] text-cyan-400/80 font-mono font-bold tracking-[0.15em] mt-1.5 relative left-[1px] glow-text">
            THE FORENSIC QA PROTOCOL
          </span>
        </div>
      )}
    </div>
  );
}
