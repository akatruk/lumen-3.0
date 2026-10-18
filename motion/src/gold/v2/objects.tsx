import type { ReactNode } from "react";

const INK = "#1c1612";
const PAPER = "#f3eee6";
const ACCENT = "#9c3b2e";
const MUTE = "#a3988c";

function Shadow({ children }: { children: ReactNode }) {
  return (
    <div style={{ filter: "drop-shadow(0 18px 28px rgba(12, 8, 6, 0.28))", width: "100%", height: "100%" }}>
      {children}
    </div>
  );
}

export function HouseMark() {
  return (
    <Shadow>
      <svg viewBox="90 110 480 430" width="100%" height="100%">
        <path d="M48 520 H592" stroke={MUTE} strokeWidth="3" fill="none" />
        <path d="M120 520 V300 L320 140 L520 300 V520 Z" fill={PAPER} />
        <path d="M120 520 V300 L320 140 L520 300 V520" fill="none" stroke={INK} strokeWidth="6" />
        <rect x="280" y="360" width="80" height="160" fill={ACCENT} />
        <rect x="180" y="340" width="70" height="56" fill="none" stroke={INK} strokeWidth="5" />
        <rect x="390" y="340" width="70" height="56" fill="none" stroke={INK} strokeWidth="5" />
        <path d="M300 140 H340 V190 H300 Z" fill={PAPER} stroke={INK} strokeWidth="5" />
      </svg>
    </Shadow>
  );
}

export function WorkMark() {
  return (
    <Shadow>
      <svg viewBox="40 60 560 480" width="100%" height="100%">
        <rect x="70" y="80" width="500" height="300" rx="8" fill={PAPER} />
        <rect x="70" y="80" width="500" height="300" rx="8" fill="none" stroke={INK} strokeWidth="6" />
        <path d="M70 160 H570" stroke={INK} strokeWidth="4" />
        <circle cx="118" cy="120" r="10" fill={ACCENT} />
        <rect x="150" y="210" width="200" height="16" fill={MUTE} />
        <rect x="150" y="250" width="280" height="16" fill={MUTE} />
        <rect x="150" y="290" width="160" height="16" fill={ACCENT} />
        <path d="M120 500 H520" stroke={INK} strokeWidth="8" />
        <path d="M160 500 V420 H480 V500" fill={PAPER} stroke={INK} strokeWidth="6" />
        <rect x="250" y="440" width="140" height="60" fill={ACCENT} />
      </svg>
    </Shadow>
  );
}

export function SchoolMark() {
  return (
    <Shadow>
      <svg viewBox="40 120 560 470" width="100%" height="100%">
        <path d="M80 250 L320 140 L560 250 L320 340 Z" fill={PAPER} stroke={INK} strokeWidth="6" />
        <path d="M140 270 V460 H500 V270" fill={PAPER} stroke={INK} strokeWidth="6" />
        <path d="M280 460 V340 H360 V460" fill={ACCENT} />
        <rect x="190" y="320" width="60" height="48" fill="none" stroke={INK} strokeWidth="5" />
        <rect x="390" y="320" width="60" height="48" fill="none" stroke={INK} strokeWidth="5" />
        <path d="M48 560 H200" stroke={INK} strokeWidth="6" />
        <path d="M70 560 V480 H180 V560" fill={PAPER} stroke={INK} strokeWidth="5" />
        <path d="M440 560 H592" stroke={INK} strokeWidth="6" />
        <path d="M460 560 V470 H580 V560" fill={PAPER} stroke={INK} strokeWidth="5" />
      </svg>
    </Shadow>
  );
}

export function StayMark() {
  return (
    <Shadow>
      <svg viewBox="0 0 640 720" width="100%" height="100%">
        <rect x="70" y="220" width="500" height="36" rx="18" fill="#3a322c" />
        <rect x="70" y="220" width="92" height="36" rx="18" fill={ACCENT} />
        <path d="M70 460 H570" stroke={MUTE} strokeWidth="4" strokeDasharray="10 14" />
        <path d="M70 460 H500" stroke={INK} strokeWidth="10" />
        <circle cx="500" cy="460" r="18" fill={ACCENT} />
      </svg>
    </Shadow>
  );
}

function Person({ x, y, h, active }: { x: number; y: number; h: number; active: boolean }) {
  const head = h * 0.22;
  const fill = active ? PAPER : "#5c534c";
  return (
    <g>
      <ellipse cx={x} cy={y + head * 0.55} rx={head * 0.42} ry={head * 0.48} fill={fill} />
      <path
        d={`M${x - h * 0.22} ${y + h} C${x - h * 0.24} ${y + h * 0.42} ${x - h * 0.08} ${y + head} ${x} ${y + head} C${x + h * 0.08} ${y + head} ${x + h * 0.24} ${y + h * 0.42} ${x + h * 0.22} ${y + h} Z`}
        fill={fill}
      />
    </g>
  );
}

export function FamilyMark({
  extended,
  focus,
}: {
  extended: boolean;
  focus: "assemble" | "household" | "parents";
}) {
  const household = focus !== "parents";
  const parents = focus === "parents" || focus === "assemble";
  return (
    <Shadow>
      <svg viewBox="0 0 640 900" width="100%" height="100%">
        <path d="M80 760 H560" stroke={MUTE} strokeWidth="3" />
        <Person x={210} y={80} h={620} active={household} />
        <Person x={430} y={110} h={590} active={household} />
        <Person x={320} y={300} h={400} active={household} />
        {extended ? <Person x={70} y={160} h={500} active={parents} /> : null}
        {extended ? <Person x={570} y={140} h={520} active={parents} /> : null}
      </svg>
    </Shadow>
  );
}

export function CostMark({ fan, fee }: { fan: number; fee: ReactNode }) {
  const spread = 36 * fan;
  return (
    <div style={{ position: "relative", width: "100%", height: "100%" }}>
      {[2, 1, 0].map((layer) => (
        <div
          key={layer}
          style={{
            position: "absolute",
            left: 40 + layer * spread,
            top: 20 + layer * 18 * fan,
            width: "78%",
            height: "86%",
            borderRadius: 18,
            background: layer === 0 ? PAPER : "#e4ddd2",
            boxShadow: "0 18px 28px rgba(12,8,6,0.28)",
            transform: `rotate(${(layer - 1) * 4 * fan}deg)`,
            opacity: layer === 0 ? 1 : 0.35 + fan * 0.65,
          }}
        >
          {layer === 0 ? (
            <div style={{ padding: "48px 40px", color: INK }}>
              <div style={{ width: 72, height: 8, background: ACCENT, marginBottom: 28 }} />
              {fee}
              <div style={{ marginTop: 36, height: 10, width: "70%", background: "#d9d0c4" }} />
              <div style={{ marginTop: 16, height: 10, width: "54%", background: "#d9d0c4" }} />
              <div style={{ marginTop: 16, height: 10, width: "62%", background: "#d9d0c4" }} />
            </div>
          ) : null}
        </div>
      ))}
    </div>
  );
}
