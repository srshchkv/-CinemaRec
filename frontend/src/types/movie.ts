export interface Movie {
  id: number;
  title: string;
  vote_average: number;
  vote_count: number;
  runtime: number | null;
  original_language: string | null;
  overview: string | null;
  popularity: number;
  genres: string | null;
  keywords: string | null;
  year: number | null;
  poster_url: string | null;
  country: string | null;
  user_rating?: number | null;
}

export interface MovieDetail extends Movie {
  similar_movies: Movie[];
  clicks: number;
  views: number;
}

export interface MovieSearchResult {
  movies: Movie[];
  total: number;
  page: number;
  limit: number;
  total_pages: number;
}

export interface MovieFilters {
  q?: string;
  genre?: string;
  year_from?: number;
  year_to?: number;
  language?: string;
  min_rating?: number;
  sort_by?: "popularity" | "rating" | "year" | "votes";
  page?: number;
  limit?: number;
}
