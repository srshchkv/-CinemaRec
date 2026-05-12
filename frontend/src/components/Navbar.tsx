"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { Film, Search, User, LogOut, LayoutDashboard, Shield } from "lucide-react";
import { useAuthStore } from "@/store/authStore";

export default function Navbar() {
  const { isAuthenticated, isAdmin, user, logout } = useAuthStore();
  const router = useRouter();

  const handleLogout = () => {
    logout();
    router.push("/");
  };

  return (
    <nav className="sticky top-0 z-50 bg-surface/90 backdrop-blur border-b border-border h-16">
      <div className="max-w-7xl mx-auto px-4 h-full flex items-center justify-between">
        {/* Logo */}
        <Link href="/" className="flex items-center gap-2 group">
          <Film className="text-accent w-6 h-6" />
          <span className="font-bold text-lg text-gradient">CinemaRec</span>
        </Link>

        {/* Center links */}
        <div className="hidden md:flex items-center gap-6 text-sm text-text-secondary">
          <Link href="/search" className="hover:text-text-primary transition-colors flex items-center gap-1">
            <Search className="w-4 h-4" />
            Поиск
          </Link>
          {isAuthenticated && (
            <Link href="/dashboard" className="hover:text-text-primary transition-colors flex items-center gap-1">
              <LayoutDashboard className="w-4 h-4" />
              Мой профиль
            </Link>
          )}
          {isAdmin && (
            <Link href="/admin" className="hover:text-accent transition-colors flex items-center gap-1">
              <Shield className="w-4 h-4" />
              Админ
            </Link>
          )}
        </div>

        {/* Auth buttons */}
        <div className="flex items-center gap-3">
          {isAuthenticated ? (
            <>
              <span className="text-sm text-text-secondary hidden md:block">
                {user?.username}
              </span>
              <button
                onClick={handleLogout}
                className="flex items-center gap-1 text-sm text-text-secondary hover:text-red-400 transition-colors"
              >
                <LogOut className="w-4 h-4" />
              </button>
            </>
          ) : (
            <>
              <Link
                href="/login"
                className="text-sm text-text-secondary hover:text-text-primary transition-colors"
              >
                Войти
              </Link>
              <Link
                href="/register"
                className="text-sm bg-accent hover:bg-accent-hover text-white px-4 py-1.5 rounded-lg transition-colors"
              >
                Регистрация
              </Link>
            </>
          )}
        </div>
      </div>
    </nav>
  );
}
