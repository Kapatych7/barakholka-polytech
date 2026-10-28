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

## Что уже есть в API (v0.2)

Все пути — с префиксом `/api/v1`, всё кроме регистрации и входа требует заголовок `Authorization: Bearer <токен>`.
Форматы ответов и коды ошибок — строго по контракту API (issue #3, `Rest_api_mvp.docx`).

| Метод | Путь | Описание |
|---|---|---|
| POST | `/auth/register` | Регистрация, сразу возвращает токен |
| POST | `/auth/login` | Вход, возвращает токен |
| GET | `/users/me` | Мой профиль |
| GET | `/users/me/ads` | Мои объявления (все статусы, фильтр `status`) |
| GET | `/categories` | Категории |
| GET | `/locations` | Места встречи (общежития и корпуса) |
| GET | `/ads` | Лента: фильтры `category_id`, `location_id`, `min_price`, `max_price`, `q`, сортировка `sort`, пагинация `limit`/`offset` |
| POST | `/ads` | Создание объявления |
| GET | `/ads/{id}` | Карточка объявления |
| PATCH | `/ads/{id}` | Редактирование (только переданные поля) |
| POST | `/ads/{id}/close` | Закрыть (active → closed) |
| POST | `/ads/{id}/reopen` | Открыть снова (closed → active) |
| POST | `/ads/{id}/archive` | В архив (active/closed → archived) |
| GET | `/health` | Проверка работы сервера и БД |

Ошибки всегда приходят в одном формате:

```json
{"error": {"code": "AD_NOT_FOUND", "message": "Объявление не найдено", "details": {}}}
```

Схема БД соответствует обновлённому документу «Структура БД» (issue #2): миграции `0001` и `0002`.

## Как мы работаем с Git

Коротко: `main` — стабильная версия, `develop` — текущая разработка, задачи делаются в ветках `feature/<id-задачи>-описание` и вливаются через Pull Request.
Полные правила — в [CONTRIBUTING.md](CONTRIBUTING.md).
