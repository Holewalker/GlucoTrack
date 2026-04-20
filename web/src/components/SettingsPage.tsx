import { useState, useEffect } from "react";
import {
  useSettings,
  useUpdateSettings,
  useTelegramRecipients,
  useCreateRecipient,
  useUpdateRecipient,
  useDeleteRecipient,
  useDetectChatId,
  useSendTest,
} from "../hooks/useGlucoseData";
const SCALE_MIN = 40;
const SCALE_MAX = 320;

function RangeBar({ low, high }: { low: number; high: number }) {
  const span = SCALE_MAX - SCALE_MIN;
  const belowPct = ((Math.max(low, SCALE_MIN) - SCALE_MIN) / span) * 100;
  const inPct = (Math.max(0, Math.min(high, SCALE_MAX) - Math.max(low, SCALE_MIN)) / span) * 100;
  const abovePct = 100 - belowPct - inPct;
  return (
    <div className="sp-range-bar" aria-hidden="true">
      <div className="sp-bar-low" style={{ width: `${belowPct}%` }} />
      <div className="sp-bar-range" style={{ width: `${Math.max(inPct, 0)}%` }} />
      <div className="sp-bar-high" style={{ width: `${Math.max(abovePct, 0)}%` }} />
      <div className="sp-marker sp-marker-low" style={{ left: `${belowPct}%` }} />
      <div className="sp-marker sp-marker-high" style={{ left: `${belowPct + inPct}%` }} />
    </div>
  );
}

function ThresholdsSection() {
  const { data: settings } = useSettings();
  const { mutate, isPending, isSuccess, error } = useUpdateSettings();
  const [low, setLow] = useState(60);
  const [high, setHigh] = useState(140);
  const [validationError, setValidationError] = useState<string | null>(null);

  useEffect(() => {
    if (settings) { setLow(settings.target_low); setHigh(settings.target_high); }
  }, [settings]);

  const handleSave = () => {
    if (low <= 0 || high <= 0) { setValidationError("Los valores deben ser positivos"); return; }
    if (low >= high) { setValidationError("El mínimo debe ser menor al máximo"); return; }
    setValidationError(null);
    mutate({ target_low: low, target_high: high });
  };

  return (
    <section className="settings-section">
      <h3>Rangos objetivo</h3>
      <RangeBar low={low} high={high} />
      <div className="sp-scale"><span>{SCALE_MIN}</span><span>{SCALE_MAX} mg/dL</span></div>
      <div className="sp-inputs">
        <div className="sp-field">
          <span className="sp-field-dot sp-dot-low" />
          <label htmlFor="sp-low">Mínimo</label>
          <div className="sp-input-wrap">
            <input id="sp-low" type="number" value={low} min={1} max={high - 1}
              onChange={(e) => setLow(Number(e.target.value))} />
            <span className="sp-unit">mg/dL</span>
          </div>
        </div>
        <div className="sp-divider" />
        <div className="sp-field">
          <span className="sp-field-dot sp-dot-high" />
          <label htmlFor="sp-high">Máximo</label>
          <div className="sp-input-wrap">
            <input id="sp-high" type="number" value={high} min={low + 1} max={SCALE_MAX}
              onChange={(e) => setHigh(Number(e.target.value))} />
            <span className="sp-unit">mg/dL</span>
          </div>
        </div>
        <button className="sp-save" onClick={handleSave} disabled={isPending}>
          {isPending ? "…" : isSuccess && !validationError ? "✓" : "Guardar"}
        </button>
      </div>
      {validationError && <p className="sp-error">{validationError}</p>}
      {error && !validationError && <p className="sp-error">Error al guardar — intentá de nuevo</p>}
    </section>
  );
}

function TelegramSection() {
  const { data: settings } = useSettings();
  const { mutate: updateSettings } = useUpdateSettings();
  const { data: recipients = [] } = useTelegramRecipients();
  const { mutate: createRecipient } = useCreateRecipient();
  const { mutate: updateRecipient } = useUpdateRecipient();
  const { mutate: deleteRecipient } = useDeleteRecipient();
  const { mutate: detectChatId, data: detected, isPending: detecting } = useDetectChatId();
  const { mutate: sendTest, isPending: testing } = useSendTest();

  const [token, setToken] = useState("");
  const [newLabel, setNewLabel] = useState("");
  const [newChatId, setNewChatId] = useState("");

  const handleSaveToken = () => {
    if (token.trim()) updateSettings({ telegram_bot_token: token.trim() } as never);
  };

  const handleAdd = () => {
    if (newChatId.trim() && newLabel.trim()) {
      createRecipient({ chat_id: newChatId.trim(), label: newLabel.trim() });
      setNewChatId(""); setNewLabel("");
    }
  };

  return (
    <section className="settings-section">
      <h3>Telegram</h3>
      <div className="tg-token-row">
        <input
          type="password"
          placeholder={settings?.telegram_bot_token_set ? "Token guardado (reemplazar)" : "Bot token"}
          value={token}
          onChange={(e) => setToken(e.target.value)}
          className="tg-token-input"
        />
        <button className="sp-save" onClick={handleSaveToken} disabled={!token.trim()}>Guardar</button>
        <button className="sp-save" onClick={() => detectChatId()} disabled={detecting}>
          {detecting ? "…" : "Detectar chat ID"}
        </button>
        <button className="sp-save" onClick={() => sendTest()} disabled={testing}>
          {testing ? "…" : "Enviar prueba"}
        </button>
      </div>

      {detected && detected.length > 0 && (
        <div className="tg-detected">
          <p>Chats detectados — hacé clic para agregar:</p>
          {detected.map((d) => (
            <button key={d.chat_id} className="tg-detected-item"
              onClick={() => { setNewChatId(d.chat_id); setNewLabel(d.name); }}>
              {d.name} ({d.chat_id})
            </button>
          ))}
        </div>
      )}

      <table className="rp-table tg-table">
        <thead>
          <tr><th>Habilitado</th><th>Nombre</th><th>Chat ID</th><th></th></tr>
        </thead>
        <tbody>
          {recipients.map((r) => (
            <tr key={r.id}>
              <td>
                <input type="checkbox" checked={r.enabled === 1}
                  onChange={(e) => updateRecipient({ id: r.id, data: { enabled: e.target.checked ? 1 : 0 } })} />
              </td>
              <td>{r.label}</td>
              <td><code>{r.chat_id}</code></td>
              <td>
                <button className="fb-btn" onClick={() => deleteRecipient(r.id)}>🗑</button>
              </td>
            </tr>
          ))}
          <tr>
            <td></td>
            <td><input placeholder="Nombre" value={newLabel} onChange={(e) => setNewLabel(e.target.value)} /></td>
            <td><input placeholder="Chat ID" value={newChatId} onChange={(e) => setNewChatId(e.target.value)} /></td>
            <td><button className="sp-save" onClick={handleAdd}>+ Agregar</button></td>
          </tr>
        </tbody>
      </table>
    </section>
  );
}

function PredictorSection() {
  const { data: settings } = useSettings();
  const { mutate: updateSettings } = useUpdateSettings();
  const [window, setWindow] = useState(20);
  const [lookback, setLookback] = useState(20);
  const [cooldown, setCooldown] = useState(10);

  useEffect(() => {
    if (settings) {
      setWindow(settings.prediction_window_minutes);
      setLookback(settings.lookback_minutes);
      setCooldown(settings.alert_cooldown_minutes);
    }
  }, [settings]);

  const handleSave = () => {
    updateSettings({
      prediction_window_minutes: window,
      lookback_minutes: lookback,
      alert_cooldown_minutes: cooldown,
    } as never);
  };

  return (
    <section className="settings-section">
      <h3>Predictor</h3>
      <div className="pred-toggle-row">
        <label>
          <input
            type="checkbox"
            checked={settings?.predictor_enabled === 1}
            onChange={(e) =>
              updateSettings({ predictor_enabled: e.target.checked ? 1 : 0 } as never)
            }
          />
          {" "}Habilitado
        </label>
      </div>
      <div className="sp-inputs">
        <div className="sp-field">
          <label>Ventana de predicción</label>
          <div className="sp-input-wrap">
            <input type="number" value={window} min={5} max={60}
              onChange={(e) => setWindow(Number(e.target.value))} />
            <span className="sp-unit">min</span>
          </div>
        </div>
        <div className="sp-field">
          <label>Lecturas anteriores</label>
          <div className="sp-input-wrap">
            <input type="number" value={lookback} min={5} max={60}
              onChange={(e) => setLookback(Number(e.target.value))} />
            <span className="sp-unit">min</span>
          </div>
        </div>
        <div className="sp-field">
          <label>Cooldown entre alertas</label>
          <div className="sp-input-wrap">
            <input type="number" value={cooldown} min={5} max={120}
              onChange={(e) => setCooldown(Number(e.target.value))} />
            <span className="sp-unit">min</span>
          </div>
        </div>
        <button className="sp-save" onClick={handleSave}>Guardar</button>
      </div>
    </section>
  );
}

export function SettingsPage() {
  return (
    <main className="settings-page">
      <h2>Configuración</h2>
      <ThresholdsSection />
      <TelegramSection />
      <PredictorSection />
    </main>
  );
}
