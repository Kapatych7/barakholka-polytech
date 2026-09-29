# mobile — Android-клиент

Здесь будет проект Android Studio (Kotlin).

## Как создать проект (делает frontend-разработчик)

1. Android Studio → **New Project** → *Empty Views Activity* (или *Empty Activity* для Compose).
2. **Save location**: эта папка `mobile/` (корень Gradle-проекта должен быть прямо здесь — рядом с `gradlew`).
3. Package name: `ru.mospolytech.barakholka`, язык Kotlin, Minimum SDK — 26.
4. Закоммитить в ветку `feature/<id>-android-init`, открыть PR в `develop`.

После появления `gradlew` CI (`.github/workflows/mobile.yml`) начнёт автоматически собирать приложение.

## Рекомендуемые библиотеки

- Retrofit + OkHttp + kotlinx.serialization / Moshi — запросы к API
- Kotlin Coroutines + ViewModel (MVVM)
- Coil — загрузка изображений
- Navigation Component

## Подключение к бэкенду

- Эмулятор Android: `http://10.0.2.2:8000/api/v1/`
- Реальный телефон в той же Wi-Fi-сети: `http://<IP-компьютера>:8000/api/v1/`
- Описание API: `http://localhost:8000/docs` (Swagger)
