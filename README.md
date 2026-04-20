# MedSync

> **Medication Adherence Platform for Indian Adults**
> Phase 1 · Team 70

[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688?logo=fastapi)](https://fastapi.tiangolo.com)
[![Next.js](https://img.shields.io/badge/Next.js-14-000000?logo=next.js)](https://nextjs.org)
[![Python](https://img.shields.io/badge/Python-3.12-3776AB?logo=python)](https://python.org)
[![TypeScript](https://img.shields.io/badge/TypeScript-5.x-3178C6?logo=typescript)](https://typescriptlang.org)
[![License](https://img.shields.io/badge/License-MIT-green)](LICENSE)

---

## 🎯 Overview

Aujasya is a Progressive Web Application (PWA) for medication adherence, designed for Indian adults who manage daily medications. It provides:

- **📱 PWA** — installable, works offline, instant loading
- **🔔 4-level escalation** — Push → WhatsApp → SMS → Caregiver alert
- **🌐 6 languages** — Hindi, English, Tamil, Telugu, Bengali, Marathi
- **👥 Caregiver linking** — family members can monitor adherence
- **📊 Calendar & streaks** — monthly adherence visualization
- **🔒 DPDPA-compliant** — AES-256-GCM encryption for PHI, consent management

## 🏗️ Architecture

```
┌──────────────────────────────────────────────────────────────┐
│                     NGINX (Reverse Proxy)                     │
├──────────────────────────┬───────────────────────────────────┤
│   Next.js 14 (BFF)       │       FastAPI (Python 3.12)       │
│   ─────────────           │       ──────────────────          │
│   • Locale routing        │       • REST API (17 endpoints)   │
│   • Auth guards           │       • ORM + Migrations          │
│   • BFF Route Handlers    │       • AES-256-GCM encryption    │
│   • httpOnly cookies      │       • JWT + jti blacklist       │
│   • Server components     │       • 4 middleware layers       │
├──────────────────────────┼───────────────────────────────────┤
│   Zustand (3 stores)      │       Celery + Redis Beat         │
│   IndexedDB (offline)     │       • Daily dose generation     │
│   Serwist (PWA + FCM)     │       • Escalation engine         │
│                           │       • Cleanup tasks             │
├──────────────────────────┴───────────────────────────────────┤
│              PostgreSQL 16        │        Redis 7             │
│              ─────────────        │        ───────             │
│              13 tables            │        Rate limits          │
│              UUID PKs             │        jti blacklist        │
│              DPDPA audit          │        Escalation state     │
└───────────────────────────────────┴──────────────────────────┘
```

## 📁 Monorepo Structure

```
MMS/
├── apps/
│   ├── api/                    # FastAPI backend
│   │   ├── app/
│   │   │   ├── config.py       # pydantic-settings
│   │   │   ├── database.py     # Dual engine (async + sync)
│   │   │   ├── main.py         # LIFO middleware registration
│   │   │   ├── dependencies.py # DI with load_only()
│   │   │   ├── models/         # 10 SQLAlchemy ORM models
│   │   │   ├── schemas/        # 5 Pydantic v2 schemas
│   │   │   ├── services/       # 6 service modules
│   │   │   ├── routers/        # 6 API routers
│   │   │   ├── middleware/     # 4 middleware layers
│   │   │   ├── tasks/          # 3 Celery task files
│   │   │   └── utils/          # OTP, timezone, validators
│   │   ├── migrations/         # Alembic (13 tables)
│   │   └── tests/              # pytest-asyncio tests
│   │
│   └── web/                    # Next.js 14 frontend
│       ├── src/
│       │   ├── app/            # App Router pages
│       │   │   ├── [locale]/   # 6 locale-aware pages
│       │   │   └── api/bff/    # BFF Route Handlers
│       │   ├── components/     # React components
│       │   ├── stores/         # 3 Zustand stores
│       │   ├── hooks/          # 5 custom hooks
│       │   ├── lib/            # API client, utils, offline-db
│       │   ├── i18n/           # i18n config
│       │   └── messages/       # 6 language JSON files
│       ├── e2e/                # Playwright E2E tests
│       └── public/             # PWA assets
│
├── packages/
│   └── shared-types/           # Zod schemas (isomorphic)
│
├── docker-compose.yml          # 7 services
├── .github/workflows/          # CI/CD pipelines
└── pnpm-workspace.yaml
```

## 🚀 Quick Start

### Prerequisites

- Node.js ≥ 18 + pnpm ≥ 8
- Python ≥ 3.12
- Docker & Docker Compose
- Redis 7+, PostgreSQL 16+

### 1. Clone & Install

```bash
git clone https://github.com/team70/aujasya.git
cd aujasya

# Install frontend dependencies
pnpm install

# Install backend dependencies
cd apps/api
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 2. Environment Setup

```bash
# Copy environment templates
cp .env.example .env
cp apps/web/.env.local.example apps/web/.env.local

# Edit .env with your credentials:
# - DATABASE_URL
# - REDIS_URL
# - SECRET_KEY (generate: openssl rand -hex 32)
# - FIELD_ENCRYPTION_KEY (generate: openssl rand -hex 32)
# - MSG91_API_KEY (for OTP)
```

### 3. Start with Docker

```bash
docker compose up -d
```

### 4. Run Migrations

```bash
cd apps/api
alembic upgrade head
```

### 5. Access

| Service | URL |
|---------|-----|
| Frontend | http://localhost:3000 |
| API Docs | http://localhost:8000/api/v1/docs |
| API Health | http://localhost:8000/api/v1/health |

## 🔐 Security Architecture

| Layer | Implementation |
|-------|----------------|
| **PHI Encryption** | AES-256-GCM (field-level) for names, DOB, phone, prescriptions |
| **Auth** | PyJWT with HS256, 15-min access tokens |
| **Refresh Tokens** | httpOnly cookies via BFF, 30-day rotation |
| **Token Revocation** | Redis jti blacklist (15-min TTL) |
| **Rate Limiting** | Redis sliding window (5 OTP/hr, 300 req/min default) |
| **RBAC** | Middleware-level permission matrix (patient vs caregiver) |
| **Audit** | Append-only audit_logs table |
| **DPDPA** | Consent records with full audit trail |

## 🧪 Testing

### Backend Tests
```bash
cd apps/api
pytest tests/ -v --asyncio-mode=auto
```

### Frontend Tests
```bash
cd apps/web
pnpm test          # Vitest unit tests
pnpm test:e2e      # Playwright E2E
```

## 🔧 Key Design Decisions

1. **BFF Pattern** — Browser never calls FastAPI directly. Next.js Route Handlers proxy all requests, keeping refresh tokens in httpOnly cookies.

2. **Dual SQLAlchemy Engine** — Async engine (asyncpg) for FastAPI, sync engine (psycopg2) for Celery. Celery tasks cannot use `await`.

3. **Middleware LIFO** — FastAPI processes middleware in reverse registration order. We register: Audit → RBAC → Auth → RateLimit, so execution runs: RateLimit → Auth → RBAC → Audit.

4. **Unified Service Worker** — Single SW scope handles both Serwist precaching and FCM push. No separate firebase-messaging-sw.js.

5. **IST Timezone** — Celery Beat uses `Asia/Kolkata`. All crontab schedules fire in IST.

6. **days_of_week Convention** — 0 = Sunday (JavaScript `Date.getDay()` convention), validated by Pydantic.

## 📄 License

MIT © 2025 Team 70
