# GlucoTrack

Dashboard personal de glucosa para usuarios de FreeStyle Libre. Lee datos automáticamente desde la API de LibreLinkUp y los muestra en un panel visual con gráficas, estadísticas y alertas.

## Features

- **Lectura actual** — valor en tiempo real con flecha de tendencia
- **Gráfica temporal** — glucosa a lo largo del tiempo con ejes alineados al calendario (hoy, semana, mes, trimestre)
- **Modo overlay** — superponer días/semanas/meses para comparar patrones
- **Time in Range** — porcentaje en rango, alto y bajo
- **Patrones por hora** — promedio de glucosa por hora del día
- **Eventos** — episodios de hipoglucemia e hiperglucemia con duración
- **Thresholds dinámicos** — los límites `TARGET_LOW` / `TARGET_HIGH` se configuran en `.env` y se reflejan en todas las gráficas

## Stack

| Componente | Tecnología |
|------------|------------|
| Backend | Python 3.12, FastAPI, aiosqlite |
| Frontend | React, TypeScript, Recharts, TanStack Query |
| Base de datos | SQLite (volumen persistente) |
| Reverse proxy | Nginx (dev) / Caddy (prod, HTTPS automático) |
| Contenedores | Docker Compose |

## Desarrollo local

1. Copiar `.env.example` a `.env` y rellenar credenciales:

```bash
cp .env.example .env
```

2. Editar `.env`:

```env
LIBRE_EMAIL=tu-email@libreview.com
LIBRE_PASSWORD=tu-password
TARGET_LOW=60
TARGET_HIGH=180
```

3. Levantar:

```bash
docker compose up -d --build
```

4. Abrir http://localhost:3000

## Producción

El stack de producción añade Caddy (HTTPS + basic auth) y DuckDNS (DNS dinámico gratuito).

### Requisitos

- VM con Docker (ej: Oracle Cloud Free Tier, Hetzner, cualquier VPS)
- Subdominio en [DuckDNS](https://www.duckdns.org) (gratuito)

### Variables adicionales en `.env`

```env
DOMAIN=tusubdominio.duckdns.org
DUCKDNS_SUBDOMAIN=tusubdominio
DUCKDNS_TOKEN=tu-token
DASH_USER=usuario
DASH_PASSWORD_HASH=$$2a$$14$$hash_generado_por_caddy
```

Para generar el hash de la contraseña:

```bash
docker run --rm caddy:2-alpine caddy hash-password --plaintext 'tu-password'
```

> **Nota:** En el `.env`, reemplazar cada `$` del hash por `$$` para evitar interpolación de Docker Compose.

### Deploy

```bash
docker compose -f docker-compose.prod.yml up -d --build
```

Caddy obtiene el certificado HTTPS automáticamente vía Let's Encrypt.

### Backup

Un cron diario copia el SQLite y mantiene los últimos 7 días:

```bash
crontab -e
# Añadir:
0 3 * * * /ruta/al/proyecto/scripts/backup.sh >> /var/log/glucose-backup.log 2>&1
```

## Estructura del proyecto

```
├── api/                  # Backend FastAPI
│   ├── main.py           # App entry point
│   ├── config.py         # Settings desde .env
│   ├── database.py       # Queries SQLite
│   ├── poller.py         # Background task que lee LibreLinkUp
│   ├── libre_client.py   # Cliente HTTP para la API de Libre
│   └── routers/          # Endpoints REST
├── web/                  # Frontend React + Vite
│   └── src/
│       ├── components/   # Componentes visuales
│       ├── hooks/        # React Query hooks
│       └── api/          # Cliente API tipado
├── scripts/              # Deploy y backup
├── docker-compose.yml    # Stack de desarrollo
└── docker-compose.prod.yml  # Stack de producción (Caddy + DuckDNS)
```

## Tests

```bash
cd api && pip install -r requirements.txt && pytest
```

## Licencia

MIT
