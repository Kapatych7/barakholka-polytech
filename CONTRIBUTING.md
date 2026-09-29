# Правила работы с Git

Основано на материалах задачи WEEEK #25 (стратегии ветвления Gitflow и Feature Branching), упрощено под команду из 4 человек и семестровый срок.

## Ветки

| Ветка | Назначение | Кто пишет |
|---|---|---|
| `main` | Стабильная версия — то, что показываем на защите/сдаче этапа | Только через PR из `develop` |
| `develop` | Текущая рабочая версия, сюда сливаются все задачи | Только через PR из рабочих веток |
| `feature/<id>-<кратко>` | Новая функциональность | Автор задачи |
| `fix/<id>-<кратко>` | Исправление ошибки | Автор задачи |
| `docs/<id>-<кратко>` | Документация, отчёты | Автор задачи |

`<id>` — номер задачи в WEEEK. Примеры:

```
feature/31-ads-list-endpoint
feature/40-android-login-screen
fix/52-chat-duplicate
docs/25-git-rules
```

Прямые коммиты в `main` и `develop` запрещены (включена защита веток на GitHub).

## Порядок работы над задачей

```bash
git checkout develop
git pull
git checkout -b feature/31-ads-list-endpoint

# ... работа, коммиты ...

git push -u origin feature/31-ads-list-endpoint
```

Дальше на GitHub — **Pull Request в `develop`**:

1. Заполнить шаблон PR (что сделано, номер задачи, как проверить).
2. Дождаться зелёного CI.
3. Получить **1 одобрение** (backend ↔ frontend смотрят PR друг друга, Роман проверяет по тест-кейсам).
4. Слить через **Squash and merge**, удалить ветку.

Когда этап готов (например, MVP) — PR `develop → main` и тег версии: `v0.1.0`, `v0.2.0`, `v1.0.0`.

## Коммиты — Conventional Commits

Формат: `<тип>(<область>): <что сделано>`

| Тип | Когда |
|---|---|
| `feat` | новая функциональность |
| `fix` | исправление ошибки |
| `docs` | документация |
| `test` | тесты |
| `refactor` | переделка кода без изменения поведения |
| `chore` | настройки, зависимости, CI |

Область: `api`, `db`, `mobile`, `ci`, `docs`.

```
feat(api): add advertisements list with category filter
fix(mobile): crash when ad has no photos
docs: update README quick start
chore(ci): cache pip dependencies
```

Один коммит — одно логическое изменение. Сообщение можно писать на английском или русском, но единообразно внутри PR.

## Что нельзя коммитить

- `.env`, пароли, токены, ключи подписи (`*.jks`, `*.keystore`) — только `.env.example`
- Папки сборки (`build/`, `.gradle/`, `__pycache__/`, `.venv/`)
- Настройки IDE (`.idea/`, `.vscode/`)

Всё это уже в `.gitignore`.

## Изменения в БД

Схема БД меняется **только через миграции Alembic**:

```bash
cd backend
alembic revision --autogenerate -m "add is_read to messages"
# проверить сгенерированный файл в alembic/versions/
alembic upgrade head
```

Изменения в структуре БД сначала согласуются с командой (документ «Структура БД» утверждён).
