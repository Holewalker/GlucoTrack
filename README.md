# Glucose Dashboard

Dashboard de análisis de glucosa para FreeStyle Libre (LibreLinkUp API).

## Setup

1. Copy `.env.example` to `.env` and fill in your credentials:

```bash
cp .env.example .env
```

2. Edit `.env`:

```env
LIBRE_EMAIL=tu-email@libreview.com
LIBRE_PASSWORD=tu-password
TARGET_LOW=60
TARGET_HIGH=140
```

3. Start:

```bash
docker compose up -d
```

4. Open http://localhost:3000

## What it shows

- **Current glucose** — live reading with trend arrow
- **24h chart** — glucose over time, with overlay mode to compare days/weeks
- **Time in Range** — % in range / high / low
- **Hourly patterns** — average glucose by hour of day
- **Events** — hypoglycemia and hyperglycemia events with duration
