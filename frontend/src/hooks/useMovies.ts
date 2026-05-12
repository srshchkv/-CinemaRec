import { useQuery } from "@tanstack/react-query";
import { moviesApi, recommendationsApi } from "@/lib/api";
import type { MovieFilters } from "@/types/movie";

export function useMovies(filters: MovieFilters = {}) {
  return useQuery({
    queryKey: ["movies", filters],
    queryFn: () => moviesApi.list(filters),
    placeholderData: (prev) => prev,
  });
}

export function useMovie(id: number) {
  return useQuery({
    queryKey: ["movie", id],
    queryFn: () => moviesApi.detail(id),
    enabled: !!id,
  });
}

export function usePopular(n = 20) {
  return useQuery({
    queryKey: ["popular", n],
    queryFn: () => recommendationsApi.popular(n),
  });
}

export function usePersonalRecommendations(enabled = true, n = 20) {
  return useQuery({
    queryKey: ["personal", n],
    queryFn: () => recommendationsApi.personal(n),
    enabled,
  });
}

export function useSimilarMovies(movieId: number, n = 10) {
  return useQuery({
    queryKey: ["similar", movieId, n],
    queryFn: () => recommendationsApi.similar(movieId, n),
    enabled: !!movieId,
  });
}
