import type { Movie } from "@/types/movie";
import MovieCard from "./MovieCard";

interface Props {
  movies: Movie[];
  title?: string;
  loading?: boolean;
  emptyMessage?: string;
  clickSource?: string;
}

function SkeletonCard() {
  return (
    <div className="bg-card rounded-xl overflow-hidden border border-border animate-pulse">
      <div className="aspect-[2/3] bg-border" />
      <div className="p-3 space-y-2">
        <div className="h-4 bg-border rounded w-3/4" />
        <div className="h-3 bg-border rounded w-1/2" />
        <div className="flex gap-1">
          <div className="h-5 bg-border rounded-full w-16" />
          <div className="h-5 bg-border rounded-full w-14" />
        </div>
      </div>
    </div>
  );
}

export default function MovieGrid({
  movies,
  title,
  loading,
  emptyMessage = "Фильмы не найдены",
  clickSource = "browse",
}: Props) {
  return (
    <section>
      {title && (
        <h2 className="text-xl font-bold text-text-primary mb-4">{title}</h2>
      )}
      {loading ? (
        <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 xl:grid-cols-6 gap-4">
          {Array.from({ length: 12 }).map((_, i) => <SkeletonCard key={i} />)}
        </div>
      ) : movies.length === 0 ? (
        <div className="text-center py-16 text-text-secondary">
          <p className="text-lg">{emptyMessage}</p>
        </div>
      ) : (
        <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 xl:grid-cols-6 gap-4">
          {movies.map((movie) => (
            <MovieCard key={movie.id} movie={movie} clickSource={clickSource} />
          ))}
        </div>
      )}
    </section>
  );
}
