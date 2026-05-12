"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { Star, Clock, Calendar } from "lucide-react";
import type { Movie } from "@/types/movie";
import { clsx } from "clsx";
import { postersApi, recommendationsApi } from "@/lib/api";
import { useAuthStore } from "@/store/authStore";

interface Props {
  movie: Movie;
  className?: string;
  clickSource?: string;
}

function needsPosterResolve(url?: string | null): boolean {
  if (!url) return true;
  return url.startsWith("/") || url.includes("image.tmdb.org");
}

function PosterPlaceholder({ title }: { title: string }) {
  const colors = ["from-violet-800", "from-cyan-800", "from-purple-800", "from-indigo-800"];
  const color = colors[title.charCodeAt(0) % colors.length];
  return (
    <div className={clsx("w-full h-full flex items-center justify-center bg-gradient-to-br", color, "to-gray-900")}>
      <span className="text-4xl font-bold text-white/30 text-center px-2 line-clamp-2">
        {title.slice(0, 2).toUpperCase()}
      </span>
    </div>
  );
}

export default function MovieCard({ movie, className, clickSource = "browse" }: Props) {
  const [posterBroken, setPosterBroken] = useState(false);
  const [resolvedPosterUrl, setResolvedPosterUrl] = useState<string | null>(movie.poster_url ?? null);
  const [isPosterResolving, setIsPosterResolving] = useState(false);
  const [isPosterLoaded, setIsPosterLoaded] = useState(false);
  const { isAuthenticated } = useAuthStore();
  const genres = movie.genres?.split(",").slice(0, 2).map((g) => g.trim()) ?? [];
  const effectivePosterUrl = resolvedPosterUrl ?? movie.poster_url ?? null;
  const showPoster = Boolean(effectivePosterUrl) && !posterBroken;

  useEffect(() => {
    setPosterBroken(false);
    setIsPosterLoaded(false);
    setResolvedPosterUrl(movie.poster_url ?? null);
    if (!needsPosterResolve(movie.poster_url)) return;

    let isActive = true;
    setIsPosterResolving(true);
    postersApi
      .byMovieId(movie.id)
      .then((res) => {
        if (!isActive) return;
        setResolvedPosterUrl(res.poster_url ?? null);
      })
      .catch(() => {
        if (!isActive) return;
        setResolvedPosterUrl(null);
      })
      .finally(() => {
        if (!isActive) return;
        setIsPosterResolving(false);
      });

    return () => {
      isActive = false;
    };
  }, [movie.id, movie.poster_url]);

  const handleClick = () => {
    if (!isAuthenticated) return;
    recommendationsApi.trackClick(movie.id, clickSource).catch(() => undefined);
  };

  return (
    <Link href={`/movies/${movie.id}`} className={clsx("group block", className)} onClick={handleClick}>
      <div className="bg-card rounded-xl overflow-hidden border border-border card-hover cursor-pointer">
        {/* Poster */}
        <div className="relative aspect-[2/3] overflow-hidden">
          {showPoster ? (
            <img
              src={effectivePosterUrl ?? undefined}
              alt={movie.title}
              className="w-full h-full object-cover transition-transform duration-300 group-hover:scale-105"
              loading="lazy"
              decoding="async"
              onError={() => setPosterBroken(true)}
              onLoad={() => setIsPosterLoaded(true)}
            />
          ) : (
            <PosterPlaceholder title={movie.title} />
          )}
          {(isPosterResolving || (showPoster && !isPosterLoaded)) && (
            <div className="absolute inset-x-0 bottom-0 h-1 bg-black/30">
              <div className="h-full w-1/2 bg-accent animate-pulse" />
            </div>
          )}
          {/* Rating badge */}
          <div className="absolute top-2 right-2 flex items-center gap-1 bg-black/70 backdrop-blur px-2 py-0.5 rounded-full text-xs">
            <Star className="w-3 h-3 text-yellow-400 fill-yellow-400" />
            <span className="text-white font-medium">{movie.vote_average.toFixed(1)}</span>
          </div>
          {/* User rating */}
          {movie.user_rating && (
            <div className="absolute top-2 left-2 flex items-center gap-1 bg-accent/80 backdrop-blur px-2 py-0.5 rounded-full text-xs text-white">
              Вы: {movie.user_rating}★
            </div>
          )}
          {/* Hover overlay */}
          <div className="absolute inset-0 bg-gradient-to-t from-black/80 via-transparent to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-300 flex items-end p-3">
            <p className="text-white text-xs line-clamp-3">{movie.overview}</p>
          </div>
        </div>

        {/* Info */}
        <div className="p-3 space-y-2">
          <h3 className="font-semibold text-text-primary text-sm leading-tight line-clamp-2 group-hover:text-accent transition-colors">
            {movie.title}
          </h3>

          <div className="flex items-center gap-3 text-xs text-text-secondary">
            {movie.year && (
              <span className="flex items-center gap-1">
                <Calendar className="w-3 h-3" />
                {movie.year}
              </span>
            )}
            {movie.runtime && (
              <span className="flex items-center gap-1">
                <Clock className="w-3 h-3" />
                {movie.runtime} мин
              </span>
            )}
          </div>

          {genres.length > 0 && (
            <div className="flex flex-wrap gap-1">
              {genres.map((g) => (
                <span key={g} className="text-xs bg-accent-soft text-accent px-2 py-0.5 rounded-full">
                  {g}
                </span>
              ))}
            </div>
          )}
        </div>
      </div>
    </Link>
  );
}
