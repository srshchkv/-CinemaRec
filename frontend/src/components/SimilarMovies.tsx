import type { Movie } from "@/types/movie";
import MovieCard from "./MovieCard";

interface Props {
  movies: Movie[];
}

export default function SimilarMovies({ movies }: Props) {
  if (!movies.length) return null;
  return (
    <section className="mt-10">
      <h2 className="text-xl font-bold mb-4 text-text-primary">Похожие фильмы</h2>
      <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 gap-4">
        {movies.slice(0, 10).map((m) => (
          <MovieCard key={m.id} movie={m} clickSource="similar" />
        ))}
      </div>
    </section>
  );
}
