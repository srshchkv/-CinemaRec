"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { useEffect } from "react";
import { Sparkles, Star, Film, Trash2 } from "lucide-react";
import { recommendationsApi, ratingsApi } from "@/lib/api";
import { useAuthStore } from "@/store/authStore";
import MovieGrid from "@/components/MovieGrid";
import MovieCard from "@/components/MovieCard";
import type { Movie } from "@/types/movie";

export default function DashboardPage() {
  const { isAuthenticated, user } = useAuthStore();
  const router = useRouter();
  const queryClient = useQueryClient();

  useEffect(() => {
    if (!isAuthenticated) router.push("/login");
  }, [isAuthenticated, router]);

  const { data: recommendations = [], isLoading: loadingRec } = useQuery({
    queryKey: ["personal-dashboard"],
    queryFn: () => recommendationsApi.personal(24),
    enabled: isAuthenticated,
  });

  const { data: myRatings = [] } = useQuery({
    queryKey: ["my-ratings"],
    queryFn: () => ratingsApi.myRatings(),
    enabled: isAuthenticated,
  });

  const deleteMutation = useMutation({
    mutationFn: (movieId: number) => ratingsApi.delete(movieId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["my-ratings"] });
      queryClient.invalidateQueries({ queryKey: ["personal-dashboard"] });
      queryClient.invalidateQueries({ queryKey: ["personal"] });
    },
  });

  return (
    <div className="max-w-7xl mx-auto px-4 py-8 space-y-10">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-text-primary">Мой профиль</h1>
          <p className="text-text-secondary text-sm mt-1">
            С возвращением, <span className="text-accent">{user?.username}</span>
          </p>
        </div>
        <div className="flex items-center gap-2 text-sm text-text-secondary">
          <Film className="w-4 h-4" />
          <span>Оценено фильмов: {(myRatings as unknown[]).length}</span>
        </div>
      </div>

      {/* Stats cards */}
      <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
        <div className="bg-card border border-border rounded-xl p-4 space-y-1">
          <p className="text-xs text-muted uppercase tracking-wide">Оценено</p>
          <p className="text-2xl font-bold text-text-primary">{(myRatings as unknown[]).length}</p>
        </div>
        <div className="bg-card border border-border rounded-xl p-4 space-y-1">
          <p className="text-xs text-muted uppercase tracking-wide">Средняя оценка</p>
          <p className="text-2xl font-bold text-text-primary">
            {(myRatings as { rating: number }[]).length > 0
              ? (
                  (myRatings as { rating: number }[]).reduce((s, r) => s + r.rating, 0) /
                  (myRatings as { rating: number }[]).length
                ).toFixed(1)
              : "—"}
          </p>
        </div>
        <div className="bg-card border border-border rounded-xl p-4 space-y-1">
          <p className="text-xs text-muted uppercase tracking-wide">Рекомендации</p>
          <p className="text-2xl font-bold text-accent">{recommendations.length}</p>
        </div>
      </div>

      {/* Personal recommendations */}
      <section>
        <h2 className="text-xl font-bold flex items-center gap-2 mb-4">
          <Sparkles className="w-5 h-5 text-accent" />
          Рекомендуем вам
        </h2>
        <MovieGrid
          movies={recommendations}
          loading={loadingRec}
          clickSource="recommendation"
          emptyMessage="Оцените минимум 5 фильмов, чтобы открыть персональные рекомендации."
        />
      </section>

      {/* Recently rated */}
      {(myRatings as unknown[]).length > 0 && (
        <section>
          <h2 className="text-xl font-bold flex items-center gap-2 mb-4">
            <Star className="w-5 h-5 text-yellow-400" />
            Ваши последние оценки
          </h2>
          <div className="space-y-3">
            {(myRatings as { id: number; movie_id: number; movie_title?: string | null; rating: number; timestamp: string }[])
              .slice(0, 10)
              .map((r) => (
                <div key={r.id} className="flex items-center gap-3 bg-card border border-border rounded-xl p-3">
                  <div className="text-text-secondary text-sm flex-1">{r.movie_title || `Фильм #${r.movie_id}`}</div>
                  <div className="flex items-center gap-1 text-yellow-400 text-sm">
                    <Star className="w-3.5 h-3.5 fill-yellow-400" />
                    {r.rating}
                  </div>
                  <div className="text-xs text-muted">
                    {new Date(r.timestamp).toLocaleDateString()}
                  </div>
                  <button
                    type="button"
                    className="text-muted hover:text-red-400 transition-colors"
                    onClick={() => deleteMutation.mutate(r.movie_id)}
                    title="Удалить оценку"
                  >
                    <Trash2 className="w-4 h-4" />
                  </button>
                </div>
              ))}
          </div>
        </section>
      )}
    </div>
  );
}
