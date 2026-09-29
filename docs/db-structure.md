> Утверждённый документ (перенесён из «Структура_БД_Барахолка_Политех_конечный_вариант.docx» без изменений по содержанию).

# Описание структур таблиц (MVP «Барахолка Политех»)

Данный документ содержит описание структуры базы данных для мобильного приложения «Барахолка Политех». Структура спроектирована с учетом требований MVP (размещение объявлений, обмен сообщениями). Авторизация пользователей осуществляется через Личный кабинет Московского Политеха.

## 1\. Таблица Users (Пользователи)

Хранит данные студентов. В рамках MVP регистрация реализована по email и паролю (интеграция с Личным кабинетом Политеха перенесена в план-максимум).

| Поле | Тип данных | Ограничения (Констрейнты) | Описание |
|---|---|---|---|
| id | INT | PK, NOT NULL, AUTO_INCREMENT | Уникальный внутренний идентификатор пользователя. |
| email | VARCHAR(255) | NOT NULL, UNIQUE | Почта пользователя. |
| password_hash | VARCHAR(255) | NOT NULL | Хэш пароля. |
| first_name | VARCHAR(100) | NOT NULL | Имя. |
| last_name | VARCHAR(100) | NOT NULL | Фамилия. |
| created_at | TIMESTAMP | NOT NULL, DEFAULT CURRENT_TIMESTAMP | Дата и время первого входа в приложение. |
| is_active | BOOLEAN | NOT NULL, DEFAULT TRUE | Флаг активности аккаунта. FALSE — пользователь заблокирован/удалил аккаунт, но данные сохранены. |

## 2\. Таблица Categories (Категории)

Справочник категорий (Учебники, Техника, Одежда, Услуги и т.д.) для фильтрации объявлений.

| Поле | Тип данных | Ограничения (Констрейнты) | Описание |
|---|---|---|---|
| id | INT | PK, NOT NULL, AUTO_INCREMENT | Уникальный идентификатор категории. |
| name | VARCHAR(100) | NOT NULL, UNIQUE | Название категории. |

## 3\. Таблица Advertisements (Объявления)

Основная сущность для хранения информации о товарах.

| Поле | Тип данных | Ограничения (Констрейнты) | Описание |
|---|---|---|---|
| id | INT | PK, NOT NULL, AUTO_INCREMENT | Уникальный идентификатор объявления. |
| user_id | INT | FK (Users.id), ON DELETE RESTRICT, NOT NULL | Автор объявления. |
| category_id | INT | FK (Categories.id), ON DELETE RESTRICT, NOT NULL | Категория товара. |
| title | VARCHAR(255) | NOT NULL | Заголовок объявления. |
| description | TEXT | NOT NULL | Подробное описание. |
| price | DECIMAL(10, 2) | NOT NULL, CHECK (price >= 0) | Стоимость товара (если 0, отдают даром). |
| status | VARCHAR(50) | NOT NULL, CHECK (status IN ('active', 'closed', 'archived')) | Статус активности. |
| created_at | TIMESTAMP | NOT NULL, DEFAULT CURRENT_TIMESTAMP | Дата создания. |
| updated_at | TIMESTAMP | NOT NULL, DEFAULT CURRENT_TIMESTAMP | Дата последнего обновления. |

## Рекомендованная реализация updated_at в PostgresSql:

```sql
CREATE OR REPLACE FUNCTION set_updated_at()
RETURNS TRIGGER AS $$
BEGIN NEW.updated_at = NOW(); RETURN NEW; END;
$$ LANGUAGE plpgsql;
CREATE TRIGGER trg_ads_updated_at
BEFORE UPDATE ON Advertisements
FOR EACH ROW EXECUTE FUNCTION set_updated_at();
```

## 4\. Таблица Ad_Images (Фотографии объявлений)

Вынесена в отдельную таблицу, так как у одного объявления может быть несколько фото (связь 1:N).

| Поле | Тип данных | Ограничения (Констрейнты) | Описание |
|---|---|---|---|
| id | INT | PK, NOT NULL, AUTO_INCREMENT | Уникальный идентификатор фото. |
| ad_id | INT | FK (Advertisements.id) ON DELETE CASCADE, NOT NULL | К какому объявлению относится. |
| image_url | VARCHAR(500) | NOT NULL | Ссылка на файл изображения на сервере. |
| is_main | BOOLEAN | NOT NULL, DEFAULT FALSE | Флаг, является ли фото главным. |

## 5\. Таблица Chats (Чаты)

Создает «комнату» для общения между покупателем и продавцом по конкретному объявлению.

| Поле | Тип данных | Ограничения (Констрейнты) | Описание |
|---|---|---|---|
| id | INT | PK, NOT NULL, AUTO_INCREMENT | Уникальный идентификатор чата. |
| ad_id | INT | FK (Advertisements.id) ON DELETE CASCADE, NOT NULL | Объявление, по которому идет обсуждение. |
| buyer_id | INT | FK (Users.id), ON DELETE RESTRICT, NOT NULL | Пользователь, который откликнулся. |
| created_at | TIMESTAMP | NOT NULL, DEFAULT CURRENT_TIMESTAMP | Дата начала переписки. |

*Системное ограничение: UNIQUE(ad_id, buyer_id) — чтобы один и тот же покупатель не мог создать два разных чата по одному объявлению.*

*Системное ограничение: (buyer_id != user_id продавца) — пользователь не может создать чат с самим собой, описывается на уровне backend логики при создании чата.*

## 6\. Таблица Messages (Сообщения в чате)

Хранит сами сообщения внутри чатов.

| Поле | Тип данных | Ограничения (Констрейнты) | Описание |
|---|---|---|---|
| id | INT | PK, NOT NULL, AUTO_INCREMENT | Уникальный идентификатор сообщения. |
| chat_id | INT | FK (Chats.id) ON DELETE CASCADE, NOT NULL | Ссылка на чат. |
| sender_id | INT | FK (Users.id), ON DELETE RESTRICT, NOT NULL | Отправитель сообщения (покупатель/продавец). |
| text | TEXT | NOT NULL | Текст сообщения. |
| created_at | TIMESTAMP | NOT NULL, DEFAULT CURRENT_TIMESTAMP | Дата и время отправки. |

## 7\. Правила удаления (Soft Delete)

В рабочей версии приложения объявления не удаляются физически из БД (чтобы не сломать историю чатов при каскадном удалении). Вместо этого у них просто меняется статус на 'closed' или 'archived'. Физическое удаление (DELETE) используется только для модерации и на этапе разработки/тестирования.

## 8\. Индексы для поиска (План-максимум, при работе над Mvp не использовать)

Для ускорения фильтрации и поиска при увеличении количества объявлений необходимо прописать индексы для полей: Advertisements.category_id, Advertisements.status, Advertisements.created_at, Advertisements.price, Advertisements.Title + Advertisements.description
