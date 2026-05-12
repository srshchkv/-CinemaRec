"use client";

import { useState } from "react";
import { Star } from "lucide-react";
import { clsx } from "clsx";

interface Props {
  value?: number;
  onChange?: (rating: number) => void;
  readonly?: boolean;
  size?: "sm" | "md" | "lg";
}

const STEPS = [0.5, 1, 1.5, 2, 2.5, 3, 3.5, 4, 4.5, 5];

export default function StarRating({ value = 0, onChange, readonly = false, size = "md" }: Props) {
  const [hover, setHover] = useState<number | null>(null);

  const sizeClass = { sm: "w-4 h-4", md: "w-5 h-5", lg: "w-7 h-7" }[size];
  const display = hover ?? value;
  const fullStars = Math.floor(display);
  const halfStar = display % 1 >= 0.5;

  return (
    <div
      className={clsx("flex items-center gap-0.5", readonly ? "cursor-default" : "cursor-pointer")}
      onMouseLeave={() => !readonly && setHover(null)}
    >
      {[1, 2, 3, 4, 5].map((star) => {
        const filled = star <= fullStars;
        const half = !filled && star === fullStars + 1 && halfStar;
        return (
          <span
            key={star}
            className="relative"
            onMouseMove={(e) => {
              if (readonly) return;
              const rect = e.currentTarget.getBoundingClientRect();
              const half = e.clientX - rect.left < rect.width / 2;
              setHover(half ? star - 0.5 : star);
            }}
            onClick={() => {
              if (readonly || !onChange) return;
              const next = hover ?? star;
              onChange(next);
            }}
          >
            <Star
              className={clsx(sizeClass, "transition-colors", {
                "fill-yellow-400 text-yellow-400": filled,
                "fill-yellow-400/50 text-yellow-400": half,
                "text-muted": !filled && !half,
              })}
            />
          </span>
        );
      })}
      {value > 0 && (
        <span className="ml-1 text-xs text-text-secondary">{value.toFixed(1)}</span>
      )}
    </div>
  );
}
