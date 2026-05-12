"use client";

import { useQuery } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { useEffect } from "react";
import {
  Users, Film, Star, TrendingUp, MousePointerClick,
  Eye, BarChart3, Target, Zap
} from "lucide-react";
import { adminApi } from "@/lib/api";
import { useAuthStore } from "@/store/authStore";
import {
  BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer,
  PieChart, Pie, Cell, Legend
} from "recharts";

const COLORS = ["#7c3aed", "#06b6d4", "#10b981", "#f59e0b", "#ef4444", "#8b5cf6", "#ec4899", "#14b8a6"];

function StatCard({ icon: Icon, label, value, sub, color = "text-accent" }: {
  icon: React.ElementType;
  label: string;
  value: string | number;
  sub?: string;
  color?: string;
}) {
  return (
    <div className="bg-card border border-border rounded-xl p-5 space-y-2">
      <div className="flex items-center gap-2 text-muted text-xs uppercase tracking-wide">
        <Icon className={`w-4 h-4 ${color}`} />
        {label}
      </div>
      <p className="text-2xl font-bold text-text-primary">{value}</p>
      {sub && <p className="text-xs text-muted">{sub}</p>}
    </div>
  );
}

export default function AdminPage() {
  const { isAuthenticated, isAdmin } = useAuthStore();
  const router = useRouter();

  useEffect(() => {
    if (!isAuthenticated || !isAdmin) router.push("/");
  }, [isAuthenticated, isAdmin, router]);

  const { data: stats } = useQuery({ queryKey: ["admin-stats"], queryFn: adminApi.stats });
  const { data: analytics } = useQuery({ queryKey: ["admin-analytics"], queryFn: adminApi.analytics });
  const { data: metrics } = useQuery({ queryKey: ["admin-metrics"], queryFn: adminApi.metrics });

  return (
    <div className="max-w-7xl mx-auto px-4 py-8 space-y-8">
      <div>
        <h1 className="text-2xl font-bold text-text-primary">Панель администратора</h1>
        <p className="text-text-secondary text-sm mt-1">Аналитика системы и метрики рекомендаций</p>
      </div>

      {/* KPI cards */}
      {stats && (
        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-5 gap-4">
          <StatCard icon={Users} label="Пользователи" value={stats.total_users} />
          <StatCard icon={Film} label="Фильмы" value={stats.total_movies?.toLocaleString()} color="text-cyan" />
          <StatCard icon={Star} label="Оценки" value={stats.total_ratings?.toLocaleString()} color="text-yellow-400" />
          <StatCard icon={TrendingUp} label="Средний рейтинг" value={stats.avg_rating?.toFixed(2)} color="text-green-400" />
          <StatCard icon={Users} label="Новые (7д)" value={stats.registrations_last_7d} sub="регистраций" color="text-pink-400" />
        </div>
      )}

      {/* Model metrics */}
      {metrics && (
        <div className="bg-card border border-border rounded-xl p-6 space-y-4">
          <h2 className="font-bold flex items-center gap-2">
            <Target className="w-5 h-5 text-accent" />
            Метрики качества рекомендаций
          </h2>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <div className="text-center p-4 bg-surface rounded-xl border border-border">
              <p className="text-xs text-muted mb-1">Precision@10</p>
              <p className="text-2xl font-bold text-accent">{(metrics.precision_at_10 * 100).toFixed(1)}%</p>
            </div>
            <div className="text-center p-4 bg-surface rounded-xl border border-border">
              <p className="text-xs text-muted mb-1">Recall@10</p>
              <p className="text-2xl font-bold text-cyan">{(metrics.recall_at_10 * 100).toFixed(1)}%</p>
            </div>
            <div className="text-center p-4 bg-surface rounded-xl border border-border">
              <p className="text-xs text-muted mb-1">NDCG@10</p>
              <p className="text-2xl font-bold text-green-400">{(metrics.ndcg_at_10 * 100).toFixed(1)}%</p>
            </div>
            <div className="text-center p-4 bg-surface rounded-xl border border-border">
              <p className="text-xs text-muted mb-1">RMSE</p>
              <p className="text-2xl font-bold text-yellow-400">
                {metrics.rmse != null ? metrics.rmse.toFixed(3) : "—"}
              </p>
            </div>
          </div>
          <p className="text-xs text-muted">
            <Zap className="inline w-3 h-3 mr-1" />
            Выполните <code className="bg-surface px-1 rounded">cd ml && python main.py</code>, чтобы переобучить модели и обновить метрики.
          </p>
        </div>
      )}

      {/* Charts */}
      {analytics && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Genre distribution */}
          <div className="bg-card border border-border rounded-xl p-6">
            <h3 className="font-semibold mb-4 flex items-center gap-2">
              <BarChart3 className="w-4 h-4 text-accent" />
              Распределение жанров
            </h3>
            <ResponsiveContainer width="100%" height={280}>
              <BarChart data={analytics.genre_distribution?.slice(0, 12)} layout="vertical">
                <XAxis type="number" tick={{ fontSize: 11, fill: "#64748b" }} />
                <YAxis dataKey="genre" type="category" tick={{ fontSize: 11, fill: "#94a3b8" }} width={90} />
                <Tooltip
                  contentStyle={{ background: "#1a1a2e", border: "1px solid #2a2a42", borderRadius: 8 }}
                  labelStyle={{ color: "#e2e8f0" }}
                />
                <Bar dataKey="count" fill="#7c3aed" radius={[0, 4, 4, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>

          {/* Language pie */}
          <div className="bg-card border border-border rounded-xl p-6">
            <h3 className="font-semibold mb-4 flex items-center gap-2">
              <BarChart3 className="w-4 h-4 text-cyan" />
              Распределение языков
            </h3>
            <ResponsiveContainer width="100%" height={280}>
              <PieChart>
                <Pie
                  data={analytics.language_distribution}
                  dataKey="count"
                  nameKey="language"
                  cx="50%"
                  cy="50%"
                  outerRadius={100}
                  label={({ language, percent }) =>
                    `${String(language).toUpperCase()} ${(Number(percent) * 100).toFixed(0)}%`
                  }
                  labelLine={false}
                >
                  {analytics.language_distribution?.map((_: unknown, i: number) => (
                    <Cell key={i} fill={COLORS[i % COLORS.length]} />
                  ))}
                </Pie>
                <Tooltip
                  contentStyle={{ background: "#1a1a2e", border: "1px solid #2a2a42", borderRadius: 8 }}
                />
              </PieChart>
            </ResponsiveContainer>
          </div>

          {/* Year distribution */}
          <div className="bg-card border border-border rounded-xl p-6 lg:col-span-2">
            <h3 className="font-semibold mb-4">Фильмы по годам</h3>
            <ResponsiveContainer width="100%" height={200}>
              <BarChart data={analytics.year_distribution?.slice(-40)}>
                <XAxis dataKey="year" tick={{ fontSize: 10, fill: "#64748b" }} interval={4} />
                <YAxis tick={{ fontSize: 10, fill: "#64748b" }} />
                <Tooltip
                  contentStyle={{ background: "#1a1a2e", border: "1px solid #2a2a42", borderRadius: 8 }}
                  labelStyle={{ color: "#e2e8f0" }}
                />
                <Bar dataKey="count" fill="#06b6d4" radius={[2, 2, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
      )}

      {/* Top clicked movies */}
      {analytics?.top_clicked?.length > 0 && (
        <div className="bg-card border border-border rounded-xl p-6">
          <h3 className="font-semibold mb-4 flex items-center gap-2">
            <MousePointerClick className="w-4 h-4 text-accent" />
            Топ фильмов по кликам
          </h3>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left text-muted text-xs uppercase border-b border-border">
                  <th className="pb-2 pr-4">Фильм</th>
                  <th className="pb-2 pr-4 text-right">Клики</th>
                  <th className="pb-2 pr-4 text-right">Просмотры</th>
                  <th className="pb-2 text-right">CTR</th>
                </tr>
              </thead>
              <tbody>
                {analytics.top_clicked.map((item: { movie_id: number; title: string; clicks: number; views: number; ctr: number }) => (
                  <tr key={item.movie_id} className="border-b border-border/50 hover:bg-surface/50">
                    <td className="py-2 pr-4 text-text-primary font-medium">{item.title}</td>
                    <td className="py-2 pr-4 text-right text-accent">{item.clicks}</td>
                    <td className="py-2 pr-4 text-right text-text-secondary">{item.views}</td>
                    <td className="py-2 text-right text-green-400">{(item.ctr * 100).toFixed(1)}%</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}
