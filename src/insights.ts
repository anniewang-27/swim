import type { Workout } from './types';

export interface Insight {
  type: 'tip' | 'achievement' | 'trend' | 'recommendation';
  title: string;
  body: string;
}

/**
 * Generates rule-based AI insights from a list of workouts.
 * Uses pattern recognition to give personalized training recommendations.
 */
export function generateInsights(workouts: Workout[]): Insight[] {
  if (workouts.length === 0) {
    return [
      {
        type: 'tip',
        title: 'Welcome to Swim!',
        body: 'Log your first workout to start receiving personalized AI-powered training insights.',
      },
    ];
  }

  const insights: Insight[] = [];
  const sorted = [...workouts].sort((a, b) => a.date.localeCompare(b.date));
  const recent = sorted.slice(-5);

  // ── Consistency Check ──────────────────────────────────────────
  const daysSinceLast = daysBetween(sorted[sorted.length - 1].date, todayStr());
  if (daysSinceLast === 0) {
    insights.push({
      type: 'achievement',
      title: 'Workout Today! 🎉',
      body: 'You swam today. Keep the momentum going!',
    });
  } else if (daysSinceLast > 7) {
    insights.push({
      type: 'recommendation',
      title: 'Time to Get Back in the Pool',
      body: `It's been ${daysSinceLast} days since your last swim. Even a short recovery swim can help maintain your fitness base.`,
    });
  }

  // ── Streak detection ──────────────────────────────────────────
  const streak = computeWeeklyStreak(sorted);
  if (streak >= 3) {
    insights.push({
      type: 'achievement',
      title: `${streak}-Week Streak 🏅`,
      body: `You've swum at least once every week for the past ${streak} weeks. Consistency is the key to improvement!`,
    });
  }

  // ── Volume trend (last 5 workouts) ────────────────────────────
  if (recent.length >= 3) {
    const avgRecent = avg(recent.map((w) => w.distanceYards));
    const avgPrior = avg(sorted.slice(0, Math.max(1, sorted.length - 5)).map((w) => w.distanceYards));
    const change = ((avgRecent - avgPrior) / avgPrior) * 100;
    if (change > 10) {
      insights.push({
        type: 'trend',
        title: 'Volume Is Climbing 📈',
        body: `Your average distance over the last 5 sessions is ${change.toFixed(0)}% higher than before. Remember the 10% rule: increase weekly volume gradually to avoid injury.`,
      });
    } else if (change < -10) {
      insights.push({
        type: 'trend',
        title: 'Volume Has Dipped',
        body: `Your recent workouts are averaging ${Math.abs(change).toFixed(0)}% less yardage than your historical average. That's fine for recovery weeks, but consider ramping back up soon.`,
      });
    }
  }

  // ── Pace trend ────────────────────────────────────────────────
  const freestyleWorkouts = sorted.filter((w) => w.stroke === 'freestyle' && w.distanceYards > 0);
  if (freestyleWorkouts.length >= 4) {
    const paces = freestyleWorkouts.map((w) => w.durationMinutes / w.distanceYards);
    const firstHalf = avg(paces.slice(0, Math.floor(paces.length / 2)));
    const secondHalf = avg(paces.slice(Math.floor(paces.length / 2)));
    const improvement = ((firstHalf - secondHalf) / firstHalf) * 100;
    if (improvement > 3) {
      insights.push({
        type: 'trend',
        title: 'Freestyle Pace Improving 🚀',
        body: `Your freestyle pace has improved by ~${improvement.toFixed(0)}% since you started tracking. Excellent work!`,
      });
    }
  }

  // ── Stroke variety ────────────────────────────────────────────
  const strokeSet = new Set(workouts.map((w) => w.stroke));
  if (strokeSet.size === 1 && workouts.length >= 4) {
    const stroke = [...strokeSet][0];
    insights.push({
      type: 'recommendation',
      title: 'Mix Up Your Strokes',
      body: `All your recent workouts have been ${stroke}. Adding backstroke or breaststroke sets can build complementary muscle groups and prevent overuse injuries.`,
    });
  }

  // ── Rest day recommendation ───────────────────────────────────
  const last7 = sorted.filter(
    (w) => daysBetween(w.date, todayStr()) <= 7,
  );
  if (last7.length >= 6) {
    insights.push({
      type: 'recommendation',
      title: 'Consider a Rest Day',
      body: "You've swum 6 or more times in the past week. Rest days are essential for muscle recovery and long-term performance gains.",
    });
  }

  // ── Butterfly encouragement ───────────────────────────────────
  const hasButterfly = workouts.some((w) => w.stroke === 'butterfly');
  if (!hasButterfly && workouts.length >= 5) {
    insights.push({
      type: 'tip',
      title: 'Try Butterfly Drills',
      body: 'Butterfly is the most technically demanding stroke. Even a few 25-yard butterfly efforts in a workout can dramatically improve your core strength and hip flexibility.',
    });
  }

  // ── Milestone: total yardage ──────────────────────────────────
  const totalYards = workouts.reduce((s, w) => s + w.distanceYards, 0);
  const milestones = [10000, 25000, 50000, 100000, 250000, 500000];
  for (const m of milestones) {
    const prevTotal = totalYards - (recent[recent.length - 1]?.distanceYards ?? 0);
    if (prevTotal < m && totalYards >= m) {
      insights.push({
        type: 'achievement',
        title: `${(m / 1000).toFixed(0)}K Yards Milestone! 🏊`,
        body: `You've now logged over ${m.toLocaleString()} yards tracked in Swim. That's approximately ${(m / 1760).toFixed(1)} miles!`,
      });
    }
  }

  // ── Next workout suggestion ───────────────────────────────────
  const lastDist = sorted[sorted.length - 1]?.distanceYards ?? 0;
  const suggestedDist = Math.round(lastDist * 1.05 / 50) * 50;
  insights.push({
    type: 'recommendation',
    title: 'Suggested Next Workout',
    body: `Based on your recent sessions, try a ${suggestedDist}-yard workout focusing on ${suggestFocus(sorted)} to build on your current fitness level.`,
  });

  return insights;
}

// ── Helpers ──────────────────────────────────────────────────────

function todayStr(): string {
  return new Date().toISOString().slice(0, 10);
}

function daysBetween(a: string, b: string): number {
  const diff = new Date(b).getTime() - new Date(a).getTime();
  return Math.round(diff / 86_400_000);
}

function avg(arr: number[]): number {
  if (arr.length === 0) return 0;
  return arr.reduce((s, v) => s + v, 0) / arr.length;
}

function computeWeeklyStreak(sorted: Workout[]): number {
  if (sorted.length === 0) return 0;
  const weekSet = new Set(sorted.map((w) => isoWeek(w.date)));
  const currentWeek = isoWeek(todayStr());
  let streak = 0;
  for (let w = currentWeek; weekSet.has(w); w--) {
    streak++;
  }
  return streak;
}

/**
 * Returns a numeric week identifier (year * 100 + ISO week number) for a given
 * date string (YYYY-MM-DD). Weeks start on Monday per ISO 8601.
 */
function isoWeek(dateStr: string): number {
  const d = new Date(dateStr);
  // Shift so Monday = 0 ... Sunday = 6
  const dayOfWeek = (d.getDay() + 6) % 7;
  // Move to the Thursday of this week (ISO 8601: week belongs to the year that contains its Thursday)
  const thursday = new Date(d);
  thursday.setDate(d.getDate() - dayOfWeek + 3);
  const yearStart = new Date(thursday.getFullYear(), 0, 1);
  const weekNum = Math.ceil(((thursday.getTime() - yearStart.getTime()) / 86_400_000 + 1) / 7);
  return thursday.getFullYear() * 100 + weekNum;
}

function suggestFocus(sorted: Workout[]): string {
  const recent5 = sorted.slice(-5);
  const strokes = recent5.map((w) => w.stroke);
  const counts: Record<string, number> = {};
  for (const s of strokes) counts[s] = (counts[s] ?? 0) + 1;
  // suggest least-used stroke
  const all: Workout['stroke'][] = ['freestyle', 'backstroke', 'breaststroke', 'butterfly'];
  const least = all.sort((a, b) => (counts[a] ?? 0) - (counts[b] ?? 0))[0];
  return least;
}
