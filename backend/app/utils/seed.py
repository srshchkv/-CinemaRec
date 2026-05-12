"""
Скрипт начального заполнения БД:
- импорт фильмов из CSV;
- создание демо-пользователей;
- генерация синтетических оценок для обучения коллаборативной модели.
"""
import os
import sys
import csv
import random
import numpy as np
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from app.database.database import SessionLocal, engine, Base
from app.models.user import User, UserRole
from app.models.movie import Movie
from app.models.rating import Rating
from app.auth.jwt_handler import hash_password

Base.metadata.create_all(bind=engine)

CSV_CANDIDATES = [
    Path(__file__).parent.parent.parent.parent / "data_movies_ВКР2.csv",
    Path(__file__).parent.parent.parent.parent / "data_movies_ВКР.csv",
]

# Synthetic generation config
NUM_SYNTHETIC_USERS = 100
RATINGS_PER_USER = 500
RANDOM_SEED = 42

POPULARITY_BIAS = 0.7        
RANDOM_NOISE = 0.3

GENRE_PROFILES = {
    "action_fan":     {"Action": 0.7, "Thriller": 0.9, "Crime": 0.45, "Drama": 0.6, "Romance": 0.3, "Science Fiction": 0.6},
    "drama_fan":      {"Drama": 0.9, "Romance": 0.7, "Family": 0.6, "History": 0.5, "Action": 0.2},
    "scifi_fan":      {"Science Fiction": 0.95, "Adventure": 0.7, "Action": 0.6, "Fantasy": 0.7},
    "comedy_fan":     {"Comedy": 0.9, "Romance": 0.6, "Family": 0.5, "Drama": 0.3},
    "horror_fan":     {"Horror": 0.95, "Thriller": 0.8, "Mystery": 0.6, "Crime": 0.5},
    "animation_fan":  {"Animation": 0.9, "Family": 0.8, "Comedy": 0.6, "Adventure": 0.7},
    "documentary_fan": {"Documentary": 0.9, "History": 0.7, "Drama": 0.6},
    "thriller_fan":   {"Thriller": 0.9, "Mystery": 0.8, "Crime": 0.7, "Action": 0.5},
}

PROFILE_NAMES = list(GENRE_PROFILES.keys())


def parse_genres(genres_str: str) -> list[str]:
    if not genres_str:
        return []
    return [g.strip() for g in genres_str.split(",") if g.strip()]


def resolve_csv_path() -> Path | None:
    env_csv = os.getenv("CSV_PATH")
    if env_csv:
        path = Path(env_csv)
        if path.exists():
            return path
    for path in CSV_CANDIDATES:
        if path.exists():
            return path
    return None


def import_movies(db) -> int:
    """Returns the number of movies in the DB after import (0 if CSV missing)."""
    csv_path = resolve_csv_path()
    if not csv_path:
        print("[WARN] CSV с фильмами не найден. Пропускаю импорт фильмов.")
        return 0

    existing = db.query(Movie.id).count()
    if existing > 0:
        print(f"[INFO] Фильмы уже импортированы ({existing}).")
        print("[INFO] Постеры загружаются динамически на сайте (без массового backfill в БД).")
        return existing

    print(f"[INFO] Импорт фильмов из {csv_path}...")
    batch, batch_size, total = [], 500, 0

    with open(csv_path, encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            try:
                movie = Movie(
                    id=int(row["id"]),
                    title=row["title"] or "Unknown",
                    vote_average=float(row["vote_average"] or 0),
                    vote_count=int(row["vote_count"] or 0),
                    runtime=int(row["runtime"]) if row.get("runtime") and row["runtime"] != "" else None,
                    original_language=row.get("original_language") or None,
                    overview=row.get("overview") or None,
                    popularity=float(row["popularity"] or 0),
                    genres=row.get("genres") or None,
                    keywords=row.get("keywords") or None,
                    year=int(row["year"]) if row.get("year") and row["year"] != "" else None,
                    poster_url=row.get("poster_url") or None,
                )
                batch.append(movie)
                if len(batch) >= batch_size:
                    db.bulk_save_objects(batch)
                    db.commit()
                    total += len(batch)
                    batch = []
                    print(f"  ...импортировано {total} фильмов", end="\r")
            except (ValueError, KeyError):
                continue

        if batch:
            db.bulk_save_objects(batch)
            db.commit()
            total += len(batch)

    print(f"\n[OK] Импортировано фильмов: {total}.")
    print("[OK] Постеры будут запрашиваться лениво только для фильмов на текущей странице.")
    return total


def create_demo_users(db) -> list[User]:
    demos = [
        {"username": "admin", "email": "admin@cinerarec.com", "password": "admin123", "role": UserRole.admin},
        {"username": "demo", "email": "demo@cinerarec.com", "password": "demo123", "role": UserRole.user},
    ]
    created = []
    for d in demos:
        if not db.query(User).filter(User.email == d["email"]).first():
            u = User(
                username=d["username"],
                email=d["email"],
                password_hash=hash_password(d["password"])[:72],
                role=d["role"],
            )
            db.add(u)
            db.commit()
            db.refresh(u)
            created.append(u)
            print(f"[OK] Создан пользователь: {d['email']} (роль={d['role'].value})")
    return created


def generate_synthetic_users(db, movie_count: int) -> None:
    """
    Генерирует синтетических пользователей с оценками фильмов.
    
    Гиперпараметры:
        POPULARITY_THRESHOLD = 6.07   - порог популярности (50% фильмов в CSV имеют popularity > 6.07)
        POPULARITY_RATIO = 0.5      - 1/2 фильмов с popularity > 6.07 для более реалистичного распределения
    """
    # === ГИПЕРПАРАМЕТРЫ ===
    POPULARITY_THRESHOLD = 6.07    # 1/2 фильмов должны иметь популярность выше этого
    POPULARITY_RATIO = 0.5   # больше половины
    
    existing_synthetic_users = db.query(User).filter(User.username.like("synth_%")).all()
    if existing_synthetic_users:
        synth_ids = [u.id for u in existing_synthetic_users]
        removed_ratings = (
            db.query(Rating)
            .filter(Rating.user_id.in_(synth_ids))
            .delete(synchronize_session=False)
        )
        removed_users = (
            db.query(User)
            .filter(User.id.in_(synth_ids))
            .delete(synchronize_session=False)
        )
        db.commit()
        print(
            f"[INFO] Удалены старые синтетические данные: "
            f"{removed_users} пользователей, {removed_ratings} оценок."
        )

    if not movie_count:
        print("[WARN] В БД нет фильмов, пропускаю генерацию синтетических пользователей.")
        return

    print(f"[INFO] Генерирую {NUM_SYNTHETIC_USERS} синтетических пользователей с оценками...")
    rng = random.Random(RANDOM_SEED)
    np.random.seed(RANDOM_SEED)

    # === ИМПОРТ ФИЛЬМОВ ===
    movies = db.query(Movie).filter(Movie.vote_count >= 100).all()
    
    if not movies:
        print("[WARN] Недостаточно данных по фильмам для синтетической генерации.")
        return
    
    # === ГРУППИРОВКА ПО ЖАНРАМ + ПО ПОПУЛЯРНОСТИ ===
    movies_by_genre_popular = {}   # Фильмы с popularity > 6.07
    movies_by_genre_all = {}       # Все фильмы
    
    for m in movies:
        genres = parse_genres(m.genres or "")
        for genre in genres:
            if genre not in movies_by_genre_popular:
                movies_by_genre_popular[genre] = []
                movies_by_genre_all[genre] = []
            
            movies_by_genre_all[genre].append(m)
            
            # Отделяем популярные
            if (m.popularity or 0) > POPULARITY_THRESHOLD:
                movies_by_genre_popular[genre].append(m)
    
    # Сортируем популярные фильмы по popularity (desc)
    for genre in movies_by_genre_popular:
        movies_by_genre_popular[genre] = sorted(
            movies_by_genre_popular[genre], 
            key=lambda m: m.popularity or 0, 
            reverse=True
        )
    
    # Сортируем все фильмы по popularity (desc)
    for genre in movies_by_genre_all:
        movies_by_genre_all[genre] = sorted(
            movies_by_genre_all[genre], 
            key=lambda m: m.popularity or 0, 
            reverse=True
        )
    
    movie_map = {m.id: m for m in movies}
    
    # === СОЗДАНИЕ ПОЛЬЗОВАТЕЛЕЙ ===
    users_batch = []
    for i in range(NUM_SYNTHETIC_USERS):
        u = User(
            username=f"synth_{i:04d}",
            email=f"synth_{i:04d}@synthetic.cinerarec.internal",
            password_hash=hash_password("not_a_real_password"),
            role=UserRole.user,
            created_at=datetime.utcnow() - timedelta(days=rng.randint(0, 365)),
        )
        users_batch.append(u)

    db.bulk_save_objects(users_batch)
    db.commit()

    synth_users = db.query(User).filter(User.username.like("synth_%")).all()
    print(f"[OK] Создано синтетических пользователей: {len(synth_users)}.")

    # === ГЕНЕРАЦИЯ ОЦЕНОК ===
    ratings_batch = []
    batch_size = 2000
    total_ratings = 0

    for user in synth_users:
        profile_name = rng.choice(PROFILE_NAMES)
        genre_prefs = GENRE_PROFILES[profile_name]
        
        n_ratings = min(RATINGS_PER_USER, len(movies))
        
        chosen_movies = []
        seen_ids = set()
        
        # === ВЫБОР ФИЛЬМОВ: 2/3 popular, 1/3 random ===
        while len(chosen_movies) < n_ratings:
            roll = rng.random()
            
            if roll < POPULARITY_RATIO:  # 66%: popularity > 6.07 внутри жанра
                # Выбрать жанр из профиля (с весами)
                genre_list = list(genre_prefs.keys())
                weights = [genre_prefs[g] for g in genre_list]
                chosen_genre = rng.choices(genre_list, weights=weights)[0]
                
                genre_movies = movies_by_genre_popular.get(chosen_genre, [])
                
                # Если нет популярных в жанре → берём любой фильм
                if not genre_movies:
                    genre_movies = movies_by_genre_all.get(chosen_genre, [])
                    if not genre_movies:
                        continue
                
                candidate = genre_movies[rng.randint(0, len(genre_movies) - 1)]
                
            else:  # 33%: рандомный из жанра
                genre_list = list(genre_prefs.keys())
                weights = [genre_prefs[g] for g in genre_list]
                chosen_genre = rng.choices(genre_list, weights=weights)[0]
                
                genre_movies = movies_by_genre_all.get(chosen_genre, [])
                if not genre_movies:
                    continue
                
                candidate = genre_movies[rng.randint(0, len(genre_movies) - 1)]
            
            if candidate.id in seen_ids:
                continue
            seen_ids.add(candidate.id)
            chosen_movies.append(candidate)
        
        # === СОЗДАНИЕ ОЦЕНОК ===
        for m in chosen_movies:
            movie_genres = parse_genres(m.genres or "")
            
            # Максимальный pref_score среди жанров фильма
            pref_score = max((genre_prefs.get(g, 0.0) for g in movie_genres), default=0.1)
            
            # Base rating: movie quality + preference bias + noise
            base = (m.vote_average / 10.0) * 5.0
            bias = (pref_score - 0.5) * 2.0  # [-1, 1]
            noise = rng.gauss(0, 0.5)
            
            raw_rating = base + bias + noise
            rating_val = round(max(0.5, min(5.0, raw_rating)) * 2) / 2  # snap to 0.5 steps
            
            ratings_batch.append(Rating(
                user_id=user.id,
                movie_id=m.id,
                rating=rating_val,
                timestamp=datetime.utcnow() - timedelta(days=rng.randint(0, 180)),
            ))
            
            if len(ratings_batch) >= batch_size:
                db.bulk_save_objects(ratings_batch)
                db.commit()
                total_ratings += len(ratings_batch)
                ratings_batch = []
                print(f"  ...сохранено {total_ratings} оценок", end="\r")

    if ratings_batch:
        db.bulk_save_objects(ratings_batch)
        db.commit()
        total_ratings += len(ratings_batch)

    print(f"\n[OK] Сгенерировано синтетических оценок: {total_ratings}.")
    
    # === ДИАГНОСТИКА: проверка популярности ===
    popular_ratings = sum(
        1 for r in ratings_batch 
        if (movie_map.get(r.movie_id) and movie_map[r.movie_id].popularity > POPULARITY_THRESHOLD)
    ) if ratings_batch else 0
    
    # Полная диагностика
    total_popular = 0
    for batch in range(total_ratings // batch_size + 1):
        ratings = db.query(Rating).filter(
            Rating.user_id.in_([u.id for u in synth_users])
        ).offset(batch * batch_size).limit(batch_size).all()
        
        for r in ratings:
            m = movie_map.get(r.movie_id)
            if m and m.popularity > POPULARITY_THRESHOLD:
                total_popular += 1
    
    if total_ratings > 0:
        actual_ratio = total_popular / total_ratings
        print(f"\n=== ДИАГНОСТИКА ПОПУЛЯРНОСТИ ===")
        print(f"Всего оценок: {total_ratings}")
        print(f"Оценок с popularity > {POPULARITY_THRESHOLD}: {total_popular}/{total_ratings} = {actual_ratio:.1%}")
        print(f"Ожидаемо: ~{POPULARITY_RATIO:.1%}")


def main():
    db = SessionLocal()
    try:
        movie_count = import_movies(db)
        create_demo_users(db)
        generate_synthetic_users(db, movie_count)
        print("\n[DONE] Заполнение базы завершено успешно.")
        print("  Admin:  admin@cinerarec.com / admin123")
        print("  Demo:   demo@cinerarec.com  / demo123")
    finally:
        db.close()


if __name__ == "__main__":
    main()
