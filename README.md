# CinemaRec — гибридная рекомендательная система фильмов

Дипломный full-stack проект для персональных рекомендаций фильмов.

## Что реализовано

- Гибридный ранжировщик: Collaborative (SVD) + Content (TF-IDF) + Popularity + поведенческий click-сигнал.
- Персональные рекомендации для авторизованного пользователя и fallback-сценарий cold start.
- Учет силы пользовательской оценки (высокие оценки усиливают, низкие штрафуют кандидатов).
- Учет времени взаимодействий: недавние оценки и клики имеют больший вес (time decay).
- Улучшенная генерация кандидатов: популярные фильмы + content-расширение по похожим фильмам.
- Обновленный пайплайн ML: обучение TF-IDF и SVD, автоподбор нескольких конфигураций SVD, offline-оценка метрик.
- Поддержка SentenceTransformers эмбеддингов (опционально).

## Архитектура и стек

- Backend: FastAPI 0.111.0, SQLAlchemy 2.0.30, Alembic 1.13.1, Pydantic 2.7.1.
- Auth: JWT (`python-jose` 3.3.0), `passlib`/bcrypt 4.0.1.
- БД: PostgreSQL (с поддержкой SQLite для разработки).
- ML: `scikit-surprise`, `scikit-learn` 1.5.0, `numpy` 1.26.4, `pandas` 2.2.2, `scipy` 1.13.0.
- Frontend: Next.js 14, TypeScript, TailwindCSS, Zustand, TanStack Query.

## Актуальная логика рекомендаций

### 1) Candidate generation

- Базовый пул: top-100 фильмов по популярности (`CANDIDATE_POOL = 100`).
- Расширение пула: похожие фильмы из content-модели по top-позитивным оценкам и недавним кликам пользователя (до 500 кандидатов на seed).

### 2) Взвешивание сигналов

Базовые веса в онлайновом гибриде (`backend/app/recommendation/hybrid.py`):

```text
W_CF = 0.45   (collaborative filtering)
W_CB = 0.35   (content-based)
W_POP = 0.12  (popularity)
W_CLICK = 0.08 (behavioral click signal)
```

### 3) Интент оценки и негативный сигнал

- Высокие оценки (>=4.5) -> weight = 2.2
- Оценки 4.0-4.5 -> weight = 1.4
- Оценки 3.5-4.0 -> weight = 0.8
- Оценки <=2.5 -> negative weight = -1.4
- Оценки <=2.0 -> negative weight = -2.2
- Средние оценки (около 3.0) считаются нейтральными (weight = 0).

Негативный профиль:
- penalty factor = 0.60
- block threshold = 0.62 (при cosine similarity >= 0.62 с негативным профилем кандидат исключается)

### 4) Time decay

- Для оценок: half-life = 45 дней
- Для кликов: half-life = 20 дней
- Формула: `0.35 + 0.65 * (0.5 ^ (age_days / half_life))`

### 5) Cold start

При <5 оценках используется content+popularity ранжирование (60% CB + 40% POP), дополнительно учитываются дизлайки, чтобы убрать нежелательные кандидаты.

## Постеры и медиа

- Источник постеров: OMDb (`OMDB_API_KEY`).
- Если в БД старый TMDB/относительный путь, backend резолвит его через OMDb по `imdb_id`.
- Результат кэшируется в памяти и может сохраняться в `movies.poster_url` для ускорения последующих запросов.
- На frontend используется lazy-loading (`loading="lazy"`, `decoding="async"`) и безопасный placeholder.

## Надежность сохранения оценок

- `POST /api/ratings/` работает как upsert.
- Добавлена защита от конкурентных конфликтов (обработка `IntegrityError` + повторное обновление записи).
- При обновлении оценки обновляется `timestamp`, чтобы корректно работал recency decay.

## Структура проекта

```text
backend/   API, бизнес-логика, модели БД, онлайн-рекомендатель
frontend/  пользовательский интерфейс
ml/        обучение моделей, подбор параметров, offline-оценка
data/      исходные данные
```

## Быстрый старт

### 1) Подготовка env-файлов

```bash
copy backend\.env.example backend\.env
copy frontend\.env.local.example frontend\.env.local
```

### 2) Backend

```bash
cd backend
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
alembic upgrade head
python -m app.utils.seed
uvicorn app.main:app --reload --port 8000
```

Минимальные переменные для `backend/.env`:

```env
DATABASE_URL=sqlite:///./data/cinemadb.db
SECRET_KEY=change-me
OMDB_API_KEY=your_omdb_api_key
```

### 3) Frontend

```bash
cd frontend
npm install
npm run dev
```

Приложение: `http://localhost:3000`  
Swagger: `http://localhost:8000/docs`

## Обучение и оценка ML

Запуск полного пайплайна:

```bash
python -m ml.main
```

Скрипт выполняет:

- подготовку текстовых признаков и обучение TF-IDF;
- обучение SVD (с выбором лучшей конфигурации из набора trial);
- сохранение артефактов в `ml/models/`;
- offline-оценку (`precision@10`, `recall@10`, `ndcg@10`, `rmse`) и сохранение в `ml/models/metrics.json`.

## Ключевые API-эндпоинты

- `POST /api/auth/register`
- `POST /api/auth/login`
- `GET /api/auth/me`
- `GET /api/movies/`
- `GET /api/movies/{id}`
- `GET /api/recommendations/`
- `GET /api/recommendations/popular`
- `GET /api/recommendations/similar/{movie_id}`
- `POST /api/recommendations/click`
- `POST /api/ratings/`
- `GET /api/ratings/my`
- `DELETE /api/ratings/{movie_id}`
- `GET /api/posters/movie/{movie_id}`

## Демо-аккаунты

- Админ: `admin@cinerarec.com` / `admin123`
- Пользователь: `demo@cinerarec.com` / `demo123`
