import type { Workout } from './types';

const STORAGE_KEY = 'swim_workouts';

export function loadWorkouts(): Workout[] {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return getSampleWorkouts();
    return JSON.parse(raw) as Workout[];
  } catch {
    return getSampleWorkouts();
  }
}

export function saveWorkouts(workouts: Workout[]): void {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(workouts));
}

export function generateId(): string {
  return `${Date.now()}-${Math.random().toString(36).slice(2, 9)}`;
}

export function formatDate(dateStr: string): string {
  const [year, month, day] = dateStr.split('-').map(Number);
  const d = new Date(year, month - 1, day);
  return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
}

export function pacePerHundred(distanceYards: number, durationMinutes: number): string {
  if (distanceYards === 0) return '—';
  const minutesPer100 = (durationMinutes / distanceYards) * 100;
  const mins = Math.floor(minutesPer100);
  const secs = Math.round((minutesPer100 - mins) * 60);
  return `${mins}:${secs.toString().padStart(2, '0')}`;
}

export function totalDistanceMiles(yards: number): string {
  return (yards / 1760).toFixed(2);
}

// Sample workouts so the app looks populated on first load
function getSampleWorkouts(): Workout[] {
  const today = new Date();
  const workouts: Workout[] = [];
  const strokes: Workout['stroke'][] = ['freestyle', 'backstroke', 'breaststroke', 'butterfly', 'mixed'];
  const distances = [1000, 1500, 2000, 2500, 1200, 1800];
  const durations = [20, 30, 40, 50, 25, 35];

  for (let i = 8; i >= 0; i--) {
    const d = new Date(today);
    d.setDate(d.getDate() - i * 3);
    workouts.push({
      id: generateId(),
      date: d.toISOString().slice(0, 10),
      distanceYards: distances[i % distances.length],
      durationMinutes: durations[i % durations.length],
      stroke: strokes[i % strokes.length],
      notes: i === 0 ? 'Great session today!' : '',
    });
  }
  return workouts;
}
