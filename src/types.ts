export type StrokeType = 'freestyle' | 'backstroke' | 'breaststroke' | 'butterfly' | 'mixed';

export interface Workout {
  id: string;
  date: string; // ISO date string YYYY-MM-DD
  distanceYards: number;
  durationMinutes: number;
  stroke: StrokeType;
  notes: string;
}

export type Page = 'dashboard' | 'log' | 'history' | 'insights';
