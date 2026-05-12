"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { Search, X } from "lucide-react";

interface Props {
  initialQuery?: string;
  onSearch?: (q: string) => void;
}

export default function SearchBar({ initialQuery = "", onSearch }: Props) {
  const [q, setQ] = useState(initialQuery);
  const router = useRouter();

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (onSearch) {
      onSearch(q);
    } else {
      router.push(`/search?q=${encodeURIComponent(q)}`);
    }
  };

  return (
    <form onSubmit={handleSubmit} className="relative w-full max-w-xl">
      <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-muted" />
      <input
        type="text"
        value={q}
        onChange={(e) => setQ(e.target.value)}
        placeholder="Поиск фильмов, жанров, ключевых слов..."
        className="w-full bg-card border border-border rounded-xl pl-10 pr-10 py-3 text-sm text-text-primary placeholder:text-muted focus:outline-none focus:border-accent transition-colors"
      />
      {q && (
        <button
          type="button"
          onClick={() => {
            setQ("");
            if (onSearch) onSearch("");
          }}
          className="absolute right-3 top-1/2 -translate-y-1/2 text-muted hover:text-text-primary"
        >
          <X className="w-4 h-4" />
        </button>
      )}
    </form>
  );
}
