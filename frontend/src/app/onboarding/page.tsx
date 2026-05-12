"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Sparkles, CheckCircle2, ArrowRight } from "lucide-react";
import { postersApi, recommendationsApi, ratingsApi } from "@/lib/api";
import { useAuthStore } from "@/store/authStore";
import StarRating from "@/components/StarRating";
import toast from "react-hot-toast";

export default function OnboardingPage() {
  const { isAuthenticated } = useAuthStore();
  const router = useRouter();
  const queryClient = useQueryClient();
  const [ratings, setRatings] = useState<Record<number, number>>({});
  const [posters, setPosters] = useState<Record<number, string | null>>({});

  const { data: popular = [], isLoading } = useQuery({
    queryKey: ["popular-onboarding"],
    queryFn: () => recommendationsApi.popular(15),
    enabled: isAuthenticated,
  });

  const rateMutation = useMutation({
    mutationFn: ({ movie_id, rating }: { movie_id: number; rating: number }) =>
      ratingsApi.rate(movie_id, rating),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["personal"] });
      queryClient.invalidateQueries({ queryKey: ["personal-dashboard"] });
      queryClient.invalidateQueries({ queryKey: ["my-ratings"] });
    },
    onError: () => {
      toast.error("Не удалось сохранить оценку");
    },
  });

  const handleRate = (movieId: number, rating: number) => {
    const previousRating = ratings[movieId];
    setRatings((r) => ({ ...r, [movieId]: rating }));
    rateMutation.mutate(
      { movie_id: movieId, rating },
      {
        onError: () => {
          setRatings((r) => {
            const next = { ...r };
            if (previousRating === undefined) {
              delete next[movieId];
            } else {
              next[movieId] = previousRating;
            }
            return next;
          });
        },
      }
    );
  };

  const handleFinish = () => {
    if (Object.keys(ratings).length < 3) {
      toast.error("Оцените минимум 3 фильма для персональных рекомендаций");
      return;
    }
    toast.success("Предпочтения сохранены, рекомендации готовы");
    router.push("/");
  };

  const ratedCount = Object.keys(ratings).length;

  useEffect(() => {
    if (!popular.length) return;

    const toResolve = popular.filter(
      (movie) => !movie.poster_url || movie.poster_url.startsWith("/") || movie.poster_url.includes("image.tmdb.org")
    );
    if (!toResolve.length) return;

    let isActive = true;
    Promise.all(
      toResolve.map((movie) =>
        postersApi
          .byMovieId(movie.id)
          .then((res) => ({ movieId: movie.id, posterUrl: res.poster_url ?? null }))
          .catch(() => ({ movieId: movie.id, posterUrl: movie.poster_url ?? null }))
      )
    ).then((resolved) => {
      if (!isActive) return;
      setPosters((prev) => {
        const next = { ...prev };
        for (const item of resolved) {
          next[item.movieId] = item.posterUrl;
        }
        return next;
      });
    });

    return () => {
      isActive = false;
    };
  }, [popular]);

  if (!isAuthenticated) {
    router.push("/login");
    return null;
  }

  return (
    <div className="max-w-4xl mx-auto px-4 py-10 space-y-8">
      {/* Header */}
      <div className="text-center space-y-3">
        <div className="inline-flex items-center gap-2 bg-accent-soft border border-accent/30 text-accent text-sm px-4 py-2 rounded-full">
          <Sparkles className="w-4 h-4" />
          Быстрая настройка
        </div>
        <h1 className="text-3xl font-bold">Оцените фильмы для старта</h1>
        <p className="text-text-secondary">
          Оцените минимум 3 просмотренных фильма. Чем больше оценок, тем точнее рекомендации.
        </p>
        <div className="flex items-center justify-center gap-2 text-sm">
          <span className={`font-medium ${ratedCount >= 3 ? "text-green-400" : "text-accent"}`}>
            Оценено: {ratedCount}
          </span>
          <span className="text-muted">/ минимум 3</span>
        </div>
      </div>

      {/* Movie list */}
      {isLoading ? (
        <div className="space-y-3">
          {Array.from({ length: 6 }).map((_, i) => (
            <div key={i} className="h-20 bg-card rounded-xl animate-pulse" />
          ))}
        </div>
      ) : (
        <div className="space-y-3">
          {popular.map((movie) => {
            const posterUrl = posters[movie.id] ?? movie.poster_url;
            return (
              <div
                key={movie.id}
                className="bg-card border border-border rounded-xl p-4 flex items-center gap-4"
              >
                {/* Poster */}
                <div className="w-12 h-16 rounded-lg overflow-hidden bg-gradient-to-br from-violet-800 to-gray-900 flex-shrink-0 flex items-center justify-center text-white/40 text-xs font-bold">
                  {posterUrl ? (
                    <img
                      src={posterUrl}
                      alt={movie.title}
                      className="w-full h-full object-cover"
                      loading="lazy"
                      decoding="async"
                    />
                  ) : (
                    movie.title.slice(0, 2).toUpperCase()
                  )}
                </div>

                {/* Info */}
                <div className="flex-1 min-w-0">
                  <h3 className="font-medium text-text-primary truncate">{movie.title}</h3>
                  <p className="text-xs text-text-secondary">
                    {movie.year} · {movie.genres?.split(",")[0]?.trim()}
                  </p>
                </div>

                {/* Rating */}
                <div className="flex items-center gap-3 flex-shrink-0">
                  {ratings[movie.id] ? (
                    <CheckCircle2 className="w-4 h-4 text-green-400" />
                  ) : (
                    <span className="text-xs text-muted">Еще не смотрел(а)</span>
                  )}
                  <StarRating
                    value={ratings[movie.id] ?? 0}
                    onChange={(r) => handleRate(movie.id, r)}
                    readonly={rateMutation.isPending}
                    size="sm"
                  />
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* CTA */}
      <div className="flex justify-center">
        <button
          onClick={handleFinish}
          className="flex items-center gap-2 bg-accent hover:bg-accent-hover text-white font-medium px-8 py-3 rounded-xl transition-colors disabled:opacity-50"
          disabled={ratedCount === 0}
        >
          {ratedCount >= 3 ? "Показать рекомендации" : "Пропустить пока"}
          <ArrowRight className="w-4 h-4" />
        </button>
      </div>
    </div>
  );
}
