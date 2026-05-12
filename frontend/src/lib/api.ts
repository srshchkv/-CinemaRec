import axios from "axios";
import type { Movie, MovieDetail, MovieSearchResult, MovieFilters } from "@/types/movie";
import type { AuthToken, LoginData, RegisterData, User } from "@/types/user";

const api = axios.create({
  baseURL: process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000",
});

api.interceptors.request.use((config) => {
  const token = typeof window !== "undefined" ? localStorage.getItem("token") : null;
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

api.interceptors.response.use(
  (r) => r,
  (err) => {
    if (err.response?.status === 401 && typeof window !== "undefined") {
      localStorage.removeItem("token");
      localStorage.removeItem("user");
    }
    return Promise.reject(err);
  }
);

// Auth
export const authApi = {
  login: (data: LoginData) => api.post<AuthToken>("/api/auth/login", data).then((r) => r.data),
  register: (data: RegisterData) => api.post<AuthToken>("/api/auth/register", data).then((r) => r.data),
  me: () => api.get<User>("/api/auth/me").then((r) => r.data),
};

// Movies
export const moviesApi = {
  list: (filters: MovieFilters = {}) =>
    api.get<MovieSearchResult>("/api/movies/", { params: filters }).then((r) => r.data),
  detail: (id: number) => api.get<MovieDetail>(`/api/movies/${id}`).then((r) => r.data),
};

export interface PosterResponse {
  poster_url: string | null;
  backdrop_url: string | null;
  width: number;
  source: string;
  skipped: boolean;
}

export const postersApi = {
  byMovieId: (movieId: number) =>
    api.get<PosterResponse>(`/api/posters/movie/${movieId}`).then((r) => r.data),
};

// Recommendations
export const recommendationsApi = {
  personal: (n = 20) =>
    api.get<Movie[]>("/api/recommendations/", { params: { n } }).then((r) => r.data),
  popular: (n = 20) =>
    api.get<Movie[]>("/api/recommendations/popular", { params: { n } }).then((r) => r.data),
  similar: (movieId: number, n = 10) =>
    api.get<Movie[]>(`/api/recommendations/similar/${movieId}`, { params: { n } }).then((r) => r.data),
  trackClick: (movie_id: number, source = "recommendation") =>
    api.post("/api/recommendations/click", { movie_id, source }).then((r) => r.data),
};

// Ratings
export const ratingsApi = {
  rate: (movie_id: number, rating: number) =>
    api.post("/api/ratings/", { movie_id, rating }).then((r) => r.data),
  myRatings: () => api.get("/api/ratings/my").then((r) => r.data),
  delete: (movie_id: number) => api.delete(`/api/ratings/${movie_id}`).then((r) => r.data),
};

// Admin
export const adminApi = {
  stats: () => api.get("/api/admin/stats").then((r) => r.data),
  analytics: () => api.get("/api/admin/analytics").then((r) => r.data),
  metrics: () => api.get("/api/admin/metrics").then((r) => r.data),
  users: () => api.get("/api/admin/users").then((r) => r.data),
};

export default api;
