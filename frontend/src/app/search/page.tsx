"use client";

import { useState, useEffect } from "react";
import { useSearchParams } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import { moviesApi } from "@/lib/api";
import { useAuthStore } from "@/store/authStore";
import type { MovieFilters } from "@/types/movie";
import SearchBar from "@/components/SearchBar";
import FilterPanel from "@/components/FilterPanel";
import MovieGrid from "@/components/MovieGrid";

export default function SearchPage() {
  const searchParams = useSearchParams();
  const { isAuthenticated } = useAuthStore();

  const [filters, setFilters] = useState<MovieFilters>({
    q: searchParams.get("q") || undefined,
    sort_by: (searchParams.get("sort_by") as MovieFilters["sort_by"]) || "popularity",
    page: 1,
    limit: 24,
  });

  const { data, isLoading } = useQuery({
    queryKey: ["movies", filters],
    queryFn: () => moviesApi.list(filters),
    placeholderData: (prev) => prev,
  });

  const handleSearch = (q: string) => setFilters((f) => ({ ...f, q: q || undefined, page: 1 }));

  return (
    <div className="max-w-7xl mx-auto px-4 py-8 space-y-6">
      <div className="flex flex-col sm:flex-row gap-3">
        <SearchBar initialQuery={filters.q || ""} onSearch={handleSearch} />
      </div>

      <FilterPanel filters={filters} onChange={setFilters} />

      {data && (
        <p className="text-sm text-text-secondary">
          Найдено фильмов: {data.total.toLocaleString()}
          {filters.q && <span className="ml-1">по запросу "<span className="text-text-primary">{filters.q}</span>"</span>}
        </p>
      )}

      <MovieGrid movies={data?.movies ?? []} loading={isLoading} />

      {/* Pagination */}
      {data && data.total_pages > 1 && (
        <div className="flex items-center justify-center gap-2 pt-4">
          <button
            onClick={() => setFilters((f) => ({ ...f, page: Math.max(1, (f.page || 1) - 1) }))}
            disabled={(filters.page || 1) <= 1}
            className="px-4 py-2 text-sm bg-card border border-border rounded-lg disabled:opacity-40 hover:border-accent transition-colors"
          >
            Назад
          </button>
          <span className="text-sm text-text-secondary px-4">
            {filters.page || 1} / {data.total_pages}
          </span>
          <button
            onClick={() => setFilters((f) => ({ ...f, page: Math.min(data.total_pages, (f.page || 1) + 1) }))}
            disabled={(filters.page || 1) >= data.total_pages}
            className="px-4 py-2 text-sm bg-card border border-border rounded-lg disabled:opacity-40 hover:border-accent transition-colors"
          >
            Вперед
          </button>
        </div>
      )}
    </div>
  );
}
