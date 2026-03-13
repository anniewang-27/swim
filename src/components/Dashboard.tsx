import type { Workout } from '../types';
import {
  ResponsiveContainer,
  AreaChart,
  Area,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
} from 'recharts';
import { formatDate, pacePerHundred, totalDistanceMiles } from '../utils';
import { TrendingUp, Droplets, Timer, Flame } from 'lucide-react';

interface DashboardProps {
  workouts: Workout[];
}

export default function Dashboard({ workouts }: DashboardProps) {
  const sorted = [...workouts].sort((a, b) => a.date.localeCompare(b.date));
  const totalYards = workouts.reduce((s, w) => s + w.distanceYards, 0);
  const totalMins = workouts.reduce((s, w) => s + w.durationMinutes, 0);
  const avgDist =
    workouts.length > 0 ? Math.round(totalYards / workouts.length) : 0;
  const last = sorted[sorted.length - 1];

  const chartData = sorted.slice(-10).map((w) => ({
    date: formatDate(w.date).split(',')[0],
    yards: w.distanceYards,
    pace: parseFloat(
      ((w.durationMinutes / w.distanceYards) * 100).toFixed(2),
    ),
  }));

  const strokeCounts: Record<string, number> = {};
  for (const w of workouts) {
    strokeCounts[w.stroke] = (strokeCounts[w.stroke] ?? 0) + 1;
  }
  const favoriteStroke =
    workouts.length > 0
      ? Object.entries(strokeCounts).sort((a, b) => b[1] - a[1])[0][0]
      : '—';

  return (
    <div className="page">
      <h1 className="page-title">Dashboard</h1>

      {/* Stats cards */}
      <div className="stats-grid">
        <StatCard
          icon={<Droplets size={20} />}
          label="Total Distance"
          value={`${totalYards.toLocaleString()} yd`}
          sub={`${totalDistanceMiles(totalYards)} miles`}
          color="blue"
        />
        <StatCard
          icon={<Timer size={20} />}
          label="Total Time"
          value={`${Math.floor(totalMins / 60)}h ${totalMins % 60}m`}
          sub={`${workouts.length} sessions`}
          color="teal"
        />
        <StatCard
          icon={<TrendingUp size={20} />}
          label="Avg Distance"
          value={`${avgDist.toLocaleString()} yd`}
          sub="per workout"
          color="indigo"
        />
        <StatCard
          icon={<Flame size={20} />}
          label="Last Pace"
          value={
            last
              ? `${pacePerHundred(last.distanceYards, last.durationMinutes)} /100yd`
              : '—'
          }
          sub={last ? formatDate(last.date) : 'No workouts yet'}
          color="violet"
        />
      </div>

      {/* Chart */}
      {chartData.length > 1 && (
        <div className="card">
          <h2 className="card-title">Distance Over Time (last 10 sessions)</h2>
          <ResponsiveContainer width="100%" height={220}>
            <AreaChart data={chartData}>
              <defs>
                <linearGradient id="distGrad" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#3b82f6" stopOpacity={0.3} />
                  <stop offset="95%" stopColor="#3b82f6" stopOpacity={0} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
              <XAxis dataKey="date" tick={{ fontSize: 12 }} />
              <YAxis tick={{ fontSize: 12 }} />
              <Tooltip formatter={(v) => [`${v} yd`, 'Distance']} />
              <Area
                type="monotone"
                dataKey="yards"
                stroke="#3b82f6"
                strokeWidth={2}
                fill="url(#distGrad)"
              />
            </AreaChart>
          </ResponsiveContainer>
        </div>
      )}

      {/* Favorite stroke */}
      {workouts.length > 0 && (
        <div className="card">
          <h2 className="card-title">Stroke Breakdown</h2>
          <div className="stroke-bars">
            {Object.entries(strokeCounts)
              .sort((a, b) => b[1] - a[1])
              .map(([stroke, count]) => (
                <div key={stroke} className="stroke-bar-row">
                  <span className="stroke-label">{capitalize(stroke)}</span>
                  <div className="stroke-bar-bg">
                    <div
                      className={`stroke-bar-fill stroke-${stroke}`}
                      style={{
                        width: `${(count / workouts.length) * 100}%`,
                      }}
                    />
                  </div>
                  <span className="stroke-count">{count}</span>
                </div>
              ))}
          </div>
          <p className="favorite-note">
            Favorite stroke: <strong>{capitalize(favoriteStroke)}</strong>
          </p>
        </div>
      )}

      {workouts.length === 0 && (
        <div className="empty-state">
          <p>No workouts yet. Log your first swim!</p>
        </div>
      )}
    </div>
  );
}

function StatCard({
  icon,
  label,
  value,
  sub,
  color,
}: {
  icon: React.ReactNode;
  label: string;
  value: string;
  sub: string;
  color: string;
}) {
  return (
    <div className={`stat-card stat-${color}`}>
      <div className="stat-icon">{icon}</div>
      <div>
        <div className="stat-label">{label}</div>
        <div className="stat-value">{value}</div>
        <div className="stat-sub">{sub}</div>
      </div>
    </div>
  );
}

function capitalize(s: string) {
  return s.charAt(0).toUpperCase() + s.slice(1);
}
