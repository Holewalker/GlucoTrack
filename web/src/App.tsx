import { useState } from "react";
import { CurrentGlucose } from "./components/CurrentGlucose";
import { GlucoseChart } from "./components/GlucoseChart";
import { TimeInRange } from "./components/TimeInRange";
import { HourlyPatterns } from "./components/HourlyPatterns";
import { EventsTable } from "./components/EventsTable";
import { RecordsPage } from "./components/RecordsPage";
import { AlertBanner } from "./components/AlertBanner";
import { AlertsPage } from "./components/AlertsPage";
import { SettingsPage } from "./components/SettingsPage";
import { useCurrentGlucose, useSettings, useRefreshDashboard } from "./hooks/useGlucoseData";
import type { Period } from "./api/client";

const PERIODS: { label: string; value: Period }[] = [
  { label: "Hoy", value: "1d" },
  { label: "7 días", value: "7d" },
  { label: "30 días", value: "30d" },
  { label: "90 días", value: "90d" },
];

type CatMood = "relaxed" | "alert" | "curled";

function getCatMood(value: number | undefined, low: number, high: number): CatMood {
  if (value === undefined) return "relaxed";
  if (value < low) return "curled";
  if (value > high) return "alert";
  return "relaxed";
}

function getCatColor(mood: CatMood): string {
  switch (mood) {
    case "relaxed": return "#6ea858";
    case "alert": return "#c18937";
    case "curled": return "#c05050";
  }
}

function CatIcon({ mood }: { mood: CatMood }) {
  const color = getCatColor(mood);

  if (mood === "alert") {
    // Standing cat, tail up and bristled
    return (
      <svg className="cat-icon" width="52" height="52" viewBox="0 0 38 38" aria-hidden="true" fill={color}>
        {/* ears — pointed up */}
        <polygon points="7,18 11,5 15,18" />
        <polygon points="23,18 27,5 31,18" />
        <polygon points="8.5,17 11,6.5 13.5,17" fill="var(--bg)" opacity="0.45" />
        <polygon points="24.5,17 27,6.5 29.5,17" fill="var(--bg)" opacity="0.45" />
        {/* head */}
        <ellipse cx="19" cy="21" rx="12" ry="9" />
        {/* body — taller, standing */}
        <ellipse cx="19" cy="31" rx="9" ry="6" />
        {/* legs */}
        <rect x="12" y="35" width="3" height="3" rx="1" />
        <rect x="23" y="35" width="3" height="3" rx="1" />
        {/* tail — bristled, up */}
        <path d="M28,31 Q38,18 34,10" stroke={color} strokeWidth="3.5" fill="none" strokeLinecap="round" />
        {/* eyes — wide open */}
        <ellipse cx="15" cy="20.5" rx="2.2" ry="2.2" fill="var(--bg)" />
        <ellipse cx="23" cy="20.5" rx="2.2" ry="2.2" fill="var(--bg)" />
        <circle cx="15" cy="20.5" r="1" fill={color} />
        <circle cx="23" cy="20.5" r="1" fill={color} />
        {/* nose */}
        <ellipse cx="19" cy="23.5" rx="1" ry="0.7" fill="var(--bg)" opacity="0.5" />
      </svg>
    );
  }

  if (mood === "curled") {
    // Curled up cat, compact shape
    return (
      <svg className="cat-icon" width="52" height="52" viewBox="0 0 38 38" aria-hidden="true" fill={color}>
        {/* ears — flattened */}
        <polygon points="8,20 12,12 16,20" />
        <polygon points="22,20 26,12 30,20" />
        <polygon points="9.5,19 12,13.5 14.5,19" fill="var(--bg)" opacity="0.45" />
        <polygon points="23.5,19 26,13.5 28.5,19" fill="var(--bg)" opacity="0.45" />
        {/* head — tucked lower */}
        <ellipse cx="19" cy="23" rx="11" ry="8" />
        {/* body — round, curled */}
        <ellipse cx="19" cy="31" rx="12" ry="6" />
        {/* tail — wrapped around body */}
        <path d="M8,33 Q3,28 7,24" stroke={color} strokeWidth="3" fill="none" strokeLinecap="round" />
        {/* eyes — squinting */}
        <line x1="13" y1="22" x2="17" y2="22" stroke="var(--bg)" strokeWidth="1.5" strokeLinecap="round" />
        <line x1="21" y1="22" x2="25" y2="22" stroke="var(--bg)" strokeWidth="1.5" strokeLinecap="round" />
        {/* nose */}
        <ellipse cx="19" cy="24.5" rx="1" ry="0.7" fill="var(--bg)" opacity="0.5" />
      </svg>
    );
  }

  // Relaxed — sitting calmly (default)
  return (
    <svg className="cat-icon" width="52" height="52" viewBox="0 0 38 38" aria-hidden="true" fill={color}>
      {/* ears */}
      <polygon points="7,18 11,7 15,18" />
      <polygon points="23,18 27,7 31,18" />
      <polygon points="8.5,17 11,8.5 13.5,17" fill="var(--bg)" opacity="0.45" />
      <polygon points="24.5,17 27,8.5 29.5,17" fill="var(--bg)" opacity="0.45" />
      {/* head */}
      <ellipse cx="19" cy="21" rx="12" ry="9" />
      {/* body */}
      <ellipse cx="19" cy="32.5" rx="10" ry="5.5" />
      {/* tail — relaxed curve */}
      <path d="M29,36 Q37,28 34,22" stroke={color} strokeWidth="3" fill="none" strokeLinecap="round" />
      {/* eyes — happy, half-closed */}
      <path d="M13,20 Q15,18.5 17,20" stroke="var(--bg)" strokeWidth="1.5" fill="none" strokeLinecap="round" />
      <path d="M21,20 Q23,18.5 25,20" stroke="var(--bg)" strokeWidth="1.5" fill="none" strokeLinecap="round" />
      {/* nose */}
      <ellipse cx="19" cy="23.5" rx="1" ry="0.7" fill="var(--bg)" opacity="0.5" />
    </svg>
  );
}

const SIM_MOODS: { mood: CatMood; label: string; desc: string }[] = [
  { mood: "curled", label: "Baja", desc: "< target_low" },
  { mood: "relaxed", label: "En rango", desc: "normal" },
  { mood: "alert", label: "Alta", desc: "> target_high" },
];

type Page = "dashboard" | "records" | "alerts" | "settings";

const NAV_TABS: { label: string; value: Page }[] = [
  { label: "Dashboard", value: "dashboard" },
  { label: "Registros", value: "records" },
  { label: "Alertas", value: "alerts" },
  { label: "Configuración", value: "settings" },
];

export default function App() {
  const [period, setPeriod] = useState<Period>("1d");
  const [page, setPage] = useState<Page>("dashboard");
  const [simMood, setSimMood] = useState<CatMood | null>(null);
  const { data: glucose } = useCurrentGlucose();
  const { data: settings } = useSettings();
  const refreshDashboard = useRefreshDashboard();
  const realMood = getCatMood(glucose?.value_mgdl, settings?.target_low ?? 60, settings?.target_high ?? 140);
  const mood = simMood ?? realMood;

  return (
    <div className="app">
      <header className="app-header">
        <div className="header-brand">
          <button
            className="cat-toggle"
            onClick={() => setSimMood(simMood ? null : "relaxed")}
            title={simMood ? "Salir de simulación" : "Modo simulación"}
          >
            <CatIcon mood={mood} />
          </button>
          <div className="header-text">
            <h1>Glucosa</h1>
            <p className="subtitle">diario de lecturas</p>
          </div>
        </div>
        {simMood && (
          <div className="sim-bar">
            {SIM_MOODS.map((s) => (
              <button
                key={s.mood}
                className={`sim-btn ${simMood === s.mood ? "active" : ""}`}
                style={{ "--sim-color": getCatColor(s.mood) } as React.CSSProperties}
                onClick={() => setSimMood(s.mood)}
              >
                {s.label}
              </button>
            ))}
          </div>
        )}
        <div className="header-nav-group">
          <nav className="page-nav">
            {NAV_TABS.map((t) => (
              <button
                key={t.value}
                onClick={() => setPage(t.value)}
                className={page === t.value ? "active" : ""}
              >
                {t.label}
              </button>
            ))}
          </nav>

          {(page === "dashboard" || page === "records") && (
            <div className="period-row">
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
              <button className="refresh-btn" onClick={refreshDashboard} title="Actualizar datos">
                ↺
              </button>
            </div>
          )}
        </div>
      </header>

      {page === "records" && (
        <RecordsPage period={period} onBack={() => setPage("dashboard")} />
      )}
      {page === "alerts" && <AlertsPage />}
      {page === "settings" && <SettingsPage />}
      {page === "dashboard" && (
        <main className="dashboard">
          <AlertBanner onViewHistory={() => setPage("alerts")} />

          <CurrentGlucose />

          <div className="row-two">
            <GlucoseChart period={period} />
            <TimeInRange period={period} />
          </div>

          <HourlyPatterns period={period} />

          <EventsTable period={period} />
        </main>
      )}
    </div>
  );
}
