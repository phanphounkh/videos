import React from 'react';

type Props = {
  frame: number;
  fps: number;
  speaking: boolean;
  mood?: 'hook' | 'setup' | 'rising' | 'twist' | 'climax' | 'payoff';
};

/** A lightweight vector presenter so every lesson has a consistent host. */
export const EducationalAvatar: React.FC<Props> = ({ frame, fps, speaking, mood = 'setup' }) => {
  const bob = speaking ? Math.sin((frame / fps) * Math.PI * 1.8) * 3 : 0;
  const mouthHeight = speaking ? 10 + Math.abs(Math.sin(frame * 0.32)) * 17 : 7;
  const wave = speaking ? 0.38 + Math.abs(Math.sin(frame * 0.18)) * 0.55 : 0;
  const shirtColors = {
    hook: ['#ea580c', '#7c2d12'],
    setup: ['#2563eb', '#172554'],
    rising: ['#0d9488', '#134e4a'],
    twist: ['#9333ea', '#4c1d95'],
    climax: ['#dc2626', '#7f1d1d'],
    payoff: ['#f59e0b', '#92400e']
  }[mood];
  const raisedArm = mood === 'hook' || mood === 'twist' || mood === 'climax';
  const browTilt = mood === 'twist' ? -8 : mood === 'climax' ? 7 : 0;

  return (
    <svg viewBox="0 0 620 720" width="100%" height="100%" aria-label="Educational presenter">
      <defs>
        <linearGradient id={`shirt-${mood}`} x1="0" y1="0" x2="1" y2="1">
          <stop offset="0" stopColor={shirtColors[0]} />
          <stop offset="1" stopColor={shirtColors[1]} />
        </linearGradient>
        <linearGradient id="skin" x1="0" y1="0" x2="0.8" y2="1">
          <stop offset="0" stopColor="#fff4d8" />
          <stop offset="1" stopColor="#f6c98f" />
        </linearGradient>
        <filter id="softShadow" x="-40%" y="-40%" width="180%" height="180%">
          <feDropShadow dx="0" dy="18" stdDeviation="18" floodColor="#020617" floodOpacity="0.48" />
        </filter>
      </defs>

      <g transform={`translate(0 ${bob})`}>
        <ellipse cx="310" cy="675" rx="205" ry="34" fill="#020617" opacity="0.4" />
        <path
          d="M145 690c12-145 58-230 165-230s153 85 165 230z"
          fill={`url(#shirt-${mood})`}
          stroke="#60a5fa"
          strokeWidth="7"
          filter="url(#softShadow)"
        />
        <path d="M242 475c20 35 116 35 136 0l20 32c-39 47-137 47-176 0z" fill="#0f172a" opacity="0.5" />
        <rect x="270" y="415" width="80" height="78" rx="35" fill="url(#skin)" />
        <circle cx="310" cy="278" r="166" fill="url(#skin)" stroke="#f59e0b" strokeWidth="8" filter="url(#softShadow)" />
        <circle cx="151" cy="300" r="34" fill="#f5cb94" />
        <circle cx="469" cy="300" r="34" fill="#f5cb94" />

        <path d="M216 234q35-25 68 0" fill="none" stroke="#3f2d22" strokeWidth="11" strokeLinecap="round" transform={`rotate(${browTilt} 250 234)`} />
        <path d="M336 234q35-25 68 0" fill="none" stroke="#3f2d22" strokeWidth="11" strokeLinecap="round" transform={`rotate(${-browTilt} 370 234)`} />
        <ellipse cx="252" cy="276" rx="15" ry="27" fill="#171717" />
        <ellipse cx="368" cy="276" rx="15" ry="27" fill="#171717" />
        <circle cx="257" cy="268" r="5" fill="#ffffff" />
        <circle cx="373" cy="268" r="5" fill="#ffffff" />
        <path d="M300 298q10 13 22 0" fill="none" stroke="#d28c61" strokeWidth="7" strokeLinecap="round" />

        <ellipse cx="310" cy="357" rx="62" ry={mouthHeight} fill="#641c2c" />
        <path d="M260 350h100q-8 14-50 14t-50-14z" fill="#ffffff" opacity={mouthHeight > 12 ? 1 : 0} />
        <ellipse cx="310" cy="371" rx="31" ry="8" fill="#fb7185" opacity={mouthHeight > 15 ? 0.8 : 0} />

        <path d={raisedArm ? 'M190 565q-70-62-90-132' : 'M190 565q-54 42-74 125'} fill="none" stroke={shirtColors[0]} strokeWidth="46" strokeLinecap="round" />
        <path d="M430 565q54 42 74 125" fill="none" stroke={shirtColors[0]} strokeWidth="46" strokeLinecap="round" />
      </g>

      {/* Boom arm and studio microphone. */}
      <g filter="url(#softShadow)">
        <path d="M18 516L164 428L283 452" fill="none" stroke="#111827" strokeWidth="20" strokeLinecap="round" strokeLinejoin="round" />
        <circle cx="164" cy="428" r="18" fill="#334155" stroke="#94a3b8" strokeWidth="5" />
        <circle cx="34" cy="505" r="18" fill="#334155" stroke="#94a3b8" strokeWidth="5" />
        <g transform="translate(275 382) rotate(-5)">
          <rect width="76" height="150" rx="35" fill="#111827" stroke="#64748b" strokeWidth="6" />
          <path d="M18 22h40M18 39h40M18 56h40" stroke="#475569" strokeWidth="6" strokeLinecap="round" />
          <rect x="30" y="145" width="16" height="60" rx="8" fill="#0f172a" />
        </g>
      </g>

      <g opacity={wave} fill="none" stroke="#fbbf24" strokeWidth="8" strokeLinecap="round">
        <path d="M372 412q28 24 0 48" />
        <path d="M392 394q49 43 0 84" />
      </g>
    </svg>
  );
};
