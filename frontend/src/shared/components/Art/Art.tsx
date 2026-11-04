import { useId } from "react";
import { cn } from "@/lib/utils";

interface ArtProps {
  className?: string;
}

/**
 * MIS Master logo mark. Same artwork as /art/logo-mark.svg, drawn inline so it
 * needs no extra request and sizes with `className` (for example "h-9 w-9").
 */
export function BrandMark({ className }: ArtProps) {
  const id = useId();
  return (
    <svg viewBox="0 0 48 48" role="img" aria-label="MIS Master" className={cn("shrink-0", className)}>
      <defs>
        <linearGradient id={`${id}-bg`} x1="0" y1="0" x2="1" y2="1">
          <stop offset="0" stopColor="#5B8DEF" />
          <stop offset="1" stopColor="#2447B8" />
        </linearGradient>
      </defs>
      <rect width="48" height="48" rx="12" fill={`url(#${id}-bg)`} />
      <rect x="11" y="27" width="6" height="11" rx="2" fill="#fff" fillOpacity=".55" />
      <rect x="21" y="21" width="6" height="17" rx="2" fill="#fff" fillOpacity=".8" />
      <rect x="31" y="14" width="6" height="24" rx="2" fill="#fff" />
      <path
        d="M11 22 L21 15.5 L27 18.5 L37 9"
        fill="none"
        stroke="#7EF0C0"
        strokeWidth="2.4"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
      <circle cx="37" cy="9" r="2.6" fill="#7EF0C0" />
    </svg>
  );
}

/**
 * Dashboard illustration for the dark brand panel on the login page.
 * Decorative: the figures in it are not real data.
 */
export function HeroIllustration({ className }: ArtProps) {
  const id = useId();
  const font = "Inter, 'Segoe UI', Arial, sans-serif";
  return (
    <svg viewBox="0 0 520 340" fill="none" aria-hidden="true" className={className}>
      <defs>
        <radialGradient id={`${id}-glow`} cx="0.8" cy="0.1" r="0.7">
          <stop offset="0" stopColor="#3B6FE0" stopOpacity=".45" />
          <stop offset="1" stopColor="#3B6FE0" stopOpacity="0" />
        </radialGradient>
        <linearGradient id={`${id}-bar`} x1="0" y1="0" x2="0" y2="1">
          <stop offset="0" stopColor="#7BA6FF" />
          <stop offset="1" stopColor="#3B6FE0" stopOpacity=".55" />
        </linearGradient>
      </defs>

      <rect width="520" height="340" fill={`url(#${id}-glow)`} />

      {/* Dashboard window */}
      <rect x="20" y="24" width="400" height="280" rx="16" fill="#fff" fillOpacity=".06" stroke="#fff" strokeOpacity=".16" />
      <circle cx="42" cy="44" r="4" fill="#FF6B6B" />
      <circle cx="56" cy="44" r="4" fill="#F2A93B" />
      <circle cx="70" cy="44" r="4" fill="#2FBF8A" />
      <rect x="150" y="38" width="120" height="12" rx="6" fill="#fff" fillOpacity=".1" />

      {/* KPI tiles */}
      <rect x="40" y="68" width="112" height="56" rx="10" fill="#fff" fillOpacity=".07" stroke="#fff" strokeOpacity=".1" />
      <rect x="52" y="80" width="40" height="6" rx="3" fill="#fff" fillOpacity=".35" />
      <rect x="52" y="96" width="64" height="14" rx="4" fill="#fff" fillOpacity=".85" />
      <rect x="164" y="68" width="112" height="56" rx="10" fill="#fff" fillOpacity=".07" stroke="#fff" strokeOpacity=".1" />
      <rect x="176" y="80" width="46" height="6" rx="3" fill="#fff" fillOpacity=".35" />
      <rect x="176" y="96" width="56" height="14" rx="4" fill="#7EF0C0" />
      <rect x="288" y="68" width="112" height="56" rx="10" fill="#fff" fillOpacity=".07" stroke="#fff" strokeOpacity=".1" />
      <rect x="300" y="80" width="36" height="6" rx="3" fill="#fff" fillOpacity=".35" />
      <rect x="300" y="96" width="70" height="14" rx="4" fill="#fff" fillOpacity=".85" />

      {/* Bar chart */}
      <rect x="40" y="140" width="224" height="148" rx="10" fill="#fff" fillOpacity=".05" stroke="#fff" strokeOpacity=".1" />
      <g fill={`url(#${id}-bar)`}>
        <rect x="54" y="236" width="14" height="36" rx="3" />
        <rect x="79" y="220" width="14" height="52" rx="3" />
        <rect x="104" y="228" width="14" height="44" rx="3" />
        <rect x="129" y="204" width="14" height="68" rx="3" />
        <rect x="154" y="212" width="14" height="60" rx="3" />
        <rect x="179" y="188" width="14" height="84" rx="3" />
        <rect x="204" y="198" width="14" height="74" rx="3" />
        <rect x="229" y="174" width="14" height="98" rx="3" />
      </g>
      <path
        d="M61 224 L86 208 L111 216 L136 192 L161 200 L186 176 L211 186 L236 162"
        stroke="#7EF0C0"
        strokeWidth="2.5"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
      <circle cx="236" cy="162" r="4" fill="#7EF0C0" />
      <line x1="50" y1="272" x2="254" y2="272" stroke="#fff" strokeOpacity=".15" />

      {/* Donut chart */}
      <rect x="276" y="140" width="124" height="148" rx="10" fill="#fff" fillOpacity=".05" stroke="#fff" strokeOpacity=".1" />
      <g transform="rotate(-90 338 196)" strokeWidth="11" fill="none">
        <circle cx="338" cy="196" r="34" stroke="#fff" strokeOpacity=".1" />
        <circle cx="338" cy="196" r="34" stroke="#6C9BFF" strokeDasharray="128 213.6" strokeLinecap="round" />
        <circle cx="338" cy="196" r="34" stroke="#2FBF8A" strokeDasharray="52 213.6" strokeDashoffset="-134" strokeLinecap="round" />
        <circle cx="338" cy="196" r="34" stroke="#F2A93B" strokeDasharray="20 213.6" strokeDashoffset="-192" strokeLinecap="round" />
      </g>
      <text x="338" y="202" textAnchor="middle" fontFamily={font} fontSize="16" fontWeight="700" fill="#fff">
        92%
      </text>
      <circle cx="298" cy="252" r="3.5" fill="#6C9BFF" />
      <rect x="308" y="249" width="60" height="6" rx="3" fill="#fff" fillOpacity=".3" />
      <circle cx="298" cy="265" r="3.5" fill="#2FBF8A" />
      <rect x="308" y="262" width="44" height="6" rx="3" fill="#fff" fillOpacity=".3" />
      <circle cx="298" cy="278" r="3.5" fill="#F2A93B" />
      <rect x="308" y="275" width="52" height="6" rx="3" fill="#fff" fillOpacity=".3" />

      {/* Floating "Validated" badge */}
      <g className="animate-float">
        <rect x="388" y="8" width="120" height="36" rx="18" fill="#0F1A33" stroke="#fff" strokeOpacity=".18" />
        <circle cx="408" cy="26" r="7" fill="#2FBF8A" />
        <path d="M404.6 26.2 L407.2 28.8 L411.6 23.8" stroke="#fff" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" />
        <text x="422" y="30" fontFamily={font} fontSize="11.5" fontWeight="600" fill="#fff">
          Validated
        </text>
      </g>

      {/* Floating uploaded-report card */}
      <g className="animate-float" style={{ animationDelay: "-3s" }}>
        <rect x="330" y="258" width="180" height="64" rx="12" fill="#0F1A33" stroke="#fff" strokeOpacity=".18" />
        <rect x="344" y="272" width="28" height="36" rx="6" fill="#2FBF8A" fillOpacity=".2" stroke="#2FBF8A" strokeOpacity=".6" />
        <text x="358" y="294" textAnchor="middle" fontFamily={font} fontSize="9" fontWeight="700" fill="#7EF0C0">
          XLS
        </text>
        <rect x="382" y="276" width="72" height="7" rx="3.5" fill="#fff" fillOpacity=".85" />
        <rect x="382" y="290" width="52" height="6" rx="3" fill="#fff" fillOpacity=".35" />
        <rect x="382" y="302" width="86" height="4" rx="2" fill="#fff" fillOpacity=".12" />
        <rect x="382" y="302" width="64" height="4" rx="2" fill="#6C9BFF" />
        <circle cx="488" cy="290" r="9" fill="#2FBF8A" />
        <path d="M483.8 290.2 L486.8 293.2 L492 287.4" stroke="#fff" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
      </g>
    </svg>
  );
}

/** Documents with a magnifying glass. Used when a table or list has nothing to show. */
export function EmptyIllustration({ className }: ArtProps) {
  return (
    <svg viewBox="0 0 160 120" fill="none" aria-hidden="true" className={className}>
      <ellipse cx="80" cy="108" rx="50" ry="7" className="fill-primary/10" />
      <rect x="54" y="16" width="58" height="76" rx="8" transform="rotate(8 83 54)" className="fill-muted stroke-border" />
      <rect x="42" y="24" width="64" height="80" rx="8" className="fill-card stroke-border" />
      <rect x="54" y="38" width="40" height="6" rx="3" className="fill-muted" />
      <rect x="54" y="50" width="30" height="6" rx="3" className="fill-muted" />
      <rect x="54" y="62" width="42" height="6" rx="3" className="fill-muted" />
      <rect x="54" y="80" width="24" height="8" rx="4" className="fill-primary/30" />
      <circle cx="112" cy="84" r="14" strokeWidth="4" className="fill-primary/10 stroke-primary" />
      <path d="M122 94 L134 106" strokeWidth="5" strokeLinecap="round" className="stroke-primary" />
      <path d="M30 34 v8 M26 38 h8" strokeWidth="2" strokeLinecap="round" className="stroke-chart-1" />
      <path d="M132 30 v6 M129 33 h6" strokeWidth="2" strokeLinecap="round" className="stroke-success" />
      <circle cx="24" cy="78" r="2.5" className="fill-warning" />
    </svg>
  );
}

/** Browser window showing a broken chart and a 404. Used on the not-found page. */
export function NotFoundIllustration({ className }: ArtProps) {
  const font = "Inter, 'Segoe UI', Arial, sans-serif";
  return (
    <svg viewBox="0 0 280 180" fill="none" aria-hidden="true" className={className}>
      <ellipse cx="140" cy="168" rx="86" ry="8" className="fill-primary/10" />
      <rect x="30" y="20" width="220" height="136" rx="14" className="fill-card stroke-border" />
      <path d="M30 34 a14 14 0 0 1 14 -14 h192 a14 14 0 0 1 14 14 v10 H30 Z" className="fill-muted" />
      <circle cx="46" cy="32" r="3.5" fill="#FF6B6B" />
      <circle cx="58" cy="32" r="3.5" fill="#F2A93B" />
      <circle cx="70" cy="32" r="3.5" fill="#2FBF8A" />
      <text x="140" y="108" textAnchor="middle" fontFamily={font} fontSize="64" fontWeight="800" className="fill-primary">
        404
      </text>
      <path d="M56 132 L88 122 L110 130 L132 118" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round" className="stroke-chart-1" />
      <path
        d="M146 118 L168 126 L196 112 L224 120"
        strokeWidth="3"
        strokeLinecap="round"
        strokeLinejoin="round"
        strokeDasharray="2 8"
        className="stroke-chart-1"
      />
      <circle cx="236" cy="30" r="16" className="fill-warning" />
      <text x="236" y="37" textAnchor="middle" fontFamily={font} fontSize="20" fontWeight="800" className="fill-warning-foreground">
        ?
      </text>
    </svg>
  );
}
