# Барахолка Политех

Мобильное приложение для размещения, поиска и обмена объявлениями между студентами Московского Политеха.

**Команда:** Григорий Князев (тимлид, UI/UX) · Альберт Гридасов (frontend / Android) · Михаил Герасимов (backend) · Роман Павлов (аналитик, QA)

## Структура репозитория (monorepo)

```
.
├── backend/            # REST API — Python, FastAPI, PostgreSQL
│   ├── app/            #   код приложения (модели, роуты, схемы)
│   ├── alembic/        #   миграции БД
│   └── tests/          #   автотесты (pytest)
├── mobile/             # Android-клиент — Kotlin
├── docs/               # архитектура, решения (ADR), структура БД
├── infra/              # docker-compose для локального запуска
└── .github/            # CI (GitHub Actions), шаблон PR
```

Почему один репозиторий, а не два — см. [docs/adr/0001-monorepo.md](docs/adr/0001-monorepo.md).

## Стек

| Часть | Технологии |
|---|---|
| Мобильный клиент | Kotlin, Android SDK, MVVM, Retrofit, Coroutines, Coil |
| Backend | Python 3.12, FastAPI, SQLAlchemy 2, Alembic, Pydantic, JWT |
| База данных | PostgreSQL 16 |
| Инфраструктура | Docker Compose, GitHub Actions |
| Дизайн / задачи | Figma, WEEEK |

Подробнее — [docs/adr/0002-tech-stack.md](docs/adr/0002-tech-stack.md).

## Быстрый старт (backend)

### Вариант 1 — Docker (проще всего)

```bash
docker compose -f infra/docker-compose.yml up --build
```

Откроется:
- API: http://localhost:8000/api/v1/health
- Swagger (документация и ручное тестирование API): http://localhost:8000/docs

### Вариант 2 — без Docker для API (удобно для разработки)

```bash
docker compose -f infra/docker-compose.yml up -d db   # только база
cd backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt
cp .env.example .env
alembic upgrade head
uvicorn app.main:app --reload
```

Тесты и линтер:

```bash
cd backend
pytest
ruff check . && ruff format --check .
```

## Что уже есть в API (v0.1)

| Метод | Путь | Описание |
|---|---|---|
| GET | `/api/v1/health` | Проверка работы сервера и БД |
| POST | `/api/v1/auth/register` | Регистрация по email и паролю |
| POST | `/api/v1/auth/login` | Вход, возвращает JWT |
| GET | `/api/v1/auth/me` | Текущий пользователь (нужен токен) |
| GET | `/api/v1/categories` | Список категорий |

Все таблицы из утверждённой структуры БД уже созданы миграцией `0001`.

## Как мы работаем с Git

Коротко: `main` — стабильная версия, `develop` — текущая разработка, задачи делаются в ветках `feature/<id-задачи>-описание` и вливаются через Pull Request.
Полные правила — в [CONTRIBUTING.md](CONTRIBUTING.md).
