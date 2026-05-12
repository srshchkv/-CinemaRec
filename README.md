# CinemaRec — гибридная рекомендательная система фильмов

Дипломный full-stack проект для персональных рекомендаций фильмов.

## Что реализовано

- Гибридный ранжировщик: Collaborative (SVD) + Content (TF-IDF) + Popularity + поведенческий click-сигнал.
- Персональные рекомендации для авторизованного пользователя и fallback-сценарий cold start.
- Учет силы пользовательской оценки (высокие оценки усиливают, низкие штрафуют кандидатов).
- Учет времени взаимодействий: недавние оценки и клики имеют больший вес (time decay).
- Улучшенная генерация кандидатов: популярные фильмы + content-расширение по похожим фильмам.
- Обновленный пайплайн ML: обучение TF-IDF и SVD, автоподбор нескольких конфигураций SVD, offline-оценка метрик.

## Архитектура и стек

- Backend: FastAPI, SQLAlchemy 2.0, Alembic, Pydantic.
- Auth: JWT (`python-jose`), `passlib`/bcrypt.
- БД: PostgreSQL.
- ML: `scikit-learn`, `scikit-surprise`, `numpy`, `scipy`, `pandas`.
- Frontend: Next.js 14, TypeScript, TailwindCSS, Zustand, TanStack Query.

## Актуальная логика рекомендаций

### 1) Candidate generation

- Базовый пул: top фильмов по популярности (`CANDIDATE_POOL`).
- Расширение пула: похожие фильмы из content-модели по top-позитивным оценкам и недавним кликам пользователя.

### 2) Взвешивание сигналов

Базовые веса в онлайновом гибриде (`backend/app/recommendation/hybrid.py`):

```text
W_CF = 0.45
W_CB = 0.35
W_POP = 0.12
W_CLICK = 0.08
```

### 3) Интент оценки и негативный сигнал

- Высокие оценки (4.0-5.0) формируют позитивный профиль с повышенным весом.
- Средние оценки (около 3.0) считаются нейтральными.
- Низкие оценки (<=2.5) формируют негативный профиль:
  - похожим фильмам применяется penalty;
  - при сильной похожести на недавно дизлайкнутые фильмы кандидаты исключаются.

### 4) Time decay

- Для оценок и кликов применяется экспоненциальное затухание веса (half-life в днях).
- Это повышает значимость последних взаимодействий и снижает влияние старых.

### 5) Cold start

При малом числе оценок используется content+popularity ранжирование, дополнительно учитываются дизлайки, чтобы убрать нежелательные кандидаты.

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
