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

export default function App() {
  const [period, setPeriod] = useState<Period>("7d");

  return (
    <div className="app">
      <header className="app-header">
        <h1>Glucosa</h1>
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
