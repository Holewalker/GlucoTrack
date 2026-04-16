import { useState } from "react";
import { CurrentGlucose } from "./components/CurrentGlucose";
import { GlucoseChart } from "./components/GlucoseChart";
import { TimeInRange } from "./components/TimeInRange";
import { HourlyPatterns } from "./components/HourlyPatterns";
import { EventsTable } from "./components/EventsTable";
import type { Period } from "./api/client";

const PERIODS: { label: string; value: Period }[] = [
  { label: "Hoy", value: "1d" },
  { label: "7 días", value: "7d" },
  { label: "30 días", value: "30d" },
  { label: "90 días", value: "90d" },
];

function CatIcon() {
  return (
    <svg
      className="cat-icon"
      width="38"
      height="38"
      viewBox="0 0 38 38"
      aria-hidden="true"
      fill="currentColor"
    >
      {/* ears */}
      <polygon points="7,18 11,7 15,18" />
      <polygon points="23,18 27,7 31,18" />
      {/* inner ear detail */}
      <polygon points="8.5,17 11,8.5 13.5,17" fill="var(--bg)" opacity="0.45" />
      <polygon points="24.5,17 27,8.5 29.5,17" fill="var(--bg)" opacity="0.45" />
      {/* head */}
      <ellipse cx="19" cy="21" rx="12" ry="9" />
      {/* body */}
      <ellipse cx="19" cy="32.5" rx="10" ry="5.5" />
      {/* tail */}
      <path
        d="M29,36 Q40,25 33,18"
        stroke="currentColor"
        strokeWidth="3"
        fill="none"
        strokeLinecap="round"
      />
      {/* eyes */}
      <ellipse cx="15" cy="20.5" rx="1.8" ry="2" fill="var(--bg)" />
      <ellipse cx="23" cy="20.5" rx="1.8" ry="2" fill="var(--bg)" />
      {/* nose */}
      <ellipse cx="19" cy="23.5" rx="1" ry="0.7" fill="var(--bg)" opacity="0.5" />
    </svg>
  );
}

export default function App() {
  const [period, setPeriod] = useState<Period>("7d");

  return (
    <div className="app">
      <header className="app-header">
        <div className="header-brand">
          <CatIcon />
          <div className="header-text">
            <h1>Glucosa</h1>
            <p className="subtitle">diario de lecturas</p>
          </div>
        </div>
        <nav className="period-selector">
          {PERIODS.map((p) => (
            <button
              key={p.value}
              onClick={() => setPeriod(p.value)}
              className={period === p.value ? "active" : ""}
            >
              {p.label}
            </button>
          ))}
        </nav>
      </header>

      <main className="dashboard">
        <CurrentGlucose />

        <div className="row-two">
          <GlucoseChart period={period} />
          <TimeInRange period={period} />
        </div>

        <HourlyPatterns period={period} />

        <EventsTable period={period} />
      </main>
    </div>
  );
}
