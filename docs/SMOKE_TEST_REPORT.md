# Smoke Test Report - 2025-11-03

## Summary
- **Status:** ✅ Django app boots, migrations apply, Celery worker starts, test suite passing.
- **Blocking issues:** No blockers after fixing checkout crash; Kafka broker absent locally (producer init fails).
- **Notable fixes:**
  - Prevented blank bootstrap cart items that broke checkout (`CartItem` signal now only creates when a default goods id is provided).
  - Ensured checkout queues confirmation tasks even inside transactional test harnesses (fall back to direct call when still inside an atomic block).
  - Added initial migration for `eventstream` app so outbox tables exist.

## Environment Setup
| Component | Notes |
| --- | --- |
| Python deps | `python -m ensurepip`, `python -m pip install -r requirements.txt`, `python -m pip install ruff` |
| MySQL | `sudo apt-get install -y mariadb-server mariadb-client`<br>`sudo service mariadb start`<br>`ALTER USER 'root'@'localhost' IDENTIFIED BY '2642';`<br>`CREATE DATABASE crossborder_trade CHARACTER SET utf8mb4;` |
| Redis | `sudo apt-get install -y redis-server`<br>`sudo service redis-server start` |
| Celery | Broker/backend via Redis (see above) |
| .env | Copied from `.env.example`; matches MySQL/Redis defaults |

## Migrations
- `python manage.py makemigrations` generated `eventstream/migrations/0001_initial.py`.
- `python manage.py migrate` applied all migrations successfully.

## Django Checks & Tests
| Command | Result |
| --- | --- |
| `python manage.py check` | ✅ No issues |
| `CELERY_TASK_ALWAYS_EAGER=True python manage.py test` | ✅ 10 tests, all passed (after fixes). Eventstream dispatcher logs expected retry warnings during tests. |

## Runtime Smoke Test
| Step | Result |
| --- | --- |
| `python manage.py runserver 0.0.0.0:8000` | ✅ Server started |
| `GET /` | 404 (expected, no root view) |
| `GET /api/user/auth/` | 405 (login endpoint requires POST) |
| `GET /api/order/orders/` (unauthenticated) | 401 Unauthorized as expected |

## Services
- **Redis cache:** Verified with `cache.set`/`cache.get` (value returned `ok`).
- **Celery worker:** `celery -A crossborder_trade worker -l info --pool=solo` connected to Redis, advertised queues `default, orders, payments, notifications`, and shut down cleanly.
- **Kafka producer:** `get_producer()` raises `NoBrokersAvailable` with the default `localhost:9092`. No local broker defined—needs docker-compose or similar for full functionality.

## Static Analysis (ruff)
- Command: `ruff check`
- Result: **25 warnings/errors**, predominantly unused imports/variables (e.g., unused admin imports in apps, unused serializer imports, unused locals in logout/realname views).
- Recommendation: Clean up unused symbols and enforce a linter in CI.

## Notable Bugs & Gaps
1. 🚫 **Checkout crashed** when a user had an auto-created cart item without an associated `Goods` record (due to `CartItem` post-save signal). Fixed by guarding signal.
2. 🔄 **Order confirmation task never queued** under Django `TestCase` transactions because `transaction.on_commit` defers until the outer transaction finishes. Added fallback to call queue logic immediately when still inside an atomic block.
3. 🗄️ **Outbox tables missing:** `eventstream` app shipped without migrations; added initial migration.
4. 📡 **Kafka integration incomplete for local dev:** Without a broker, producer initialization fails. Consider supplying docker-compose snippet or making connection lazy/optional.
5. 🛡️ **Settings hard-code credentials:** SECRET_KEY, DATABASES, and ALLOWED_HOSTS ignore `.env`. Moving to environment-driven settings would align with `.env` expectations.
6. 📉 **No `/api/health` endpoint:** Health-check route would simplify probe automation.
7. 🧾 **Logged warnings during tests:** Eventstream dispatcher emits stack traces every run because tests intentionally raise `send-error`. Consider silencing or asserting logs.
8. 🔁 **Celery eager mode toggle:** Tests rely on env var / Celery app mixin. Documented, but exposing a Django setting switch would help.
9. 💳 **Refund/payment flows:** Payment app includes placeholder views; no refund API or webhooks to deliver promised "refund API" feature.

## Recommended Next Steps (Priority Order)
1. **Add Kafka/dev services:** Provide docker-compose for Kafka (and document usage) or gate producer initialization so the API can start when Kafka is offline.
2. **Configuration hygiene:** Load SECRET_KEY/DB credentials/ALLOWED_HOSTS from environment variables; ensure `.env` matches actual usage.
3. **Lint cleanup & enforcement:** Address ruff-reported unused imports/variables, then add lint job to CI.
4. **Health endpoint:** Implement `GET /api/health` returning Django/DB/Redis status for readiness probes.
5. **Celery robustness:** Add worker/beat startup instructions, and consider monitoring (e.g., Flower) defaults; optionally add Celery ping management command.
6. **Payment/refund roadmap:** Flesh out payment callbacks and refund endpoints to match stated feature goals.
7. **Logging polish:** Down-grade expected test failures/warnings in eventstream dispatcher to avoid noisy logs.

## Artifacts & Logs
- `/tmp/runserver.log` – dev server output (404s as expected).
- `/tmp/celery.log` – Celery worker startup and clean shutdown.
- MySQL/Redis services running locally via systemd for the session.

