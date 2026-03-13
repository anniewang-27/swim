import { useState } from 'react';
import type { Workout, StrokeType } from '../types';
import { generateId } from '../utils';
import { CheckCircle } from 'lucide-react';

interface LogWorkoutProps {
  onSave: (w: Workout) => void;
}

const STROKES: StrokeType[] = ['freestyle', 'backstroke', 'breaststroke', 'butterfly', 'mixed'];

export default function LogWorkout({ onSave }: LogWorkoutProps) {
  const today = new Date().toISOString().slice(0, 10);

  const [date, setDate] = useState(today);
  const [distanceYards, setDistanceYards] = useState('');
  const [durationMinutes, setDurationMinutes] = useState('');
  const [stroke, setStroke] = useState<StrokeType>('freestyle');
  const [notes, setNotes] = useState('');
  const [saved, setSaved] = useState(false);
  const [errors, setErrors] = useState<Record<string, string>>({});

  function validate(): boolean {
    const e: Record<string, string> = {};
    if (!date) e.date = 'Date is required.';
    const dist = parseFloat(distanceYards);
    if (!distanceYards || isNaN(dist) || dist <= 0)
      e.distance = 'Enter a positive distance in yards.';
    const dur = parseFloat(durationMinutes);
    if (!durationMinutes || isNaN(dur) || dur <= 0)
      e.duration = 'Enter a positive duration in minutes.';
    setErrors(e);
    return Object.keys(e).length === 0;
  }

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!validate()) return;

    const workout: Workout = {
      id: generateId(),
      date,
      distanceYards: parseFloat(distanceYards),
      durationMinutes: parseFloat(durationMinutes),
      stroke,
      notes: notes.trim(),
    };
    onSave(workout);

    // Reset form
    setDate(today);
    setDistanceYards('');
    setDurationMinutes('');
    setStroke('freestyle');
    setNotes('');
    setErrors({});

    setSaved(true);
    setTimeout(() => setSaved(false), 3000);
  }

  return (
    <div className="page">
      <h1 className="page-title">Log a Workout</h1>

      {saved && (
        <div className="success-banner">
          <CheckCircle size={18} />
          <span>Workout saved successfully!</span>
        </div>
      )}

      <div className="card form-card">
        <form onSubmit={handleSubmit} noValidate>
          {/* Date */}
          <div className="form-group">
            <label htmlFor="date">Date</label>
            <input
              id="date"
              type="date"
              value={date}
              max={today}
              onChange={(e) => setDate(e.target.value)}
              className={errors.date ? 'error' : ''}
            />
            {errors.date && <span className="error-msg">{errors.date}</span>}
          </div>

          {/* Distance */}
          <div className="form-row">
            <div className="form-group">
              <label htmlFor="distance">Distance (yards)</label>
              <input
                id="distance"
                type="number"
                min="1"
                step="25"
                placeholder="e.g. 1500"
                value={distanceYards}
                onChange={(e) => setDistanceYards(e.target.value)}
                className={errors.distance ? 'error' : ''}
              />
              {errors.distance && (
                <span className="error-msg">{errors.distance}</span>
              )}
            </div>

            {/* Duration */}
            <div className="form-group">
              <label htmlFor="duration">Duration (minutes)</label>
              <input
                id="duration"
                type="number"
                min="1"
                step="1"
                placeholder="e.g. 30"
                value={durationMinutes}
                onChange={(e) => setDurationMinutes(e.target.value)}
                className={errors.duration ? 'error' : ''}
              />
              {errors.duration && (
                <span className="error-msg">{errors.duration}</span>
              )}
            </div>
          </div>

          {/* Live pace preview */}
          {distanceYards && durationMinutes && (
            <div className="pace-preview">
              Estimated pace:{' '}
              <strong>
                {calcPace(parseFloat(distanceYards), parseFloat(durationMinutes))}{' '}
                / 100 yd
              </strong>
            </div>
          )}

          {/* Stroke */}
          <div className="form-group">
            <label>Primary Stroke</label>
            <div className="stroke-selector">
              {STROKES.map((s) => (
                <button
                  key={s}
                  type="button"
                  className={`stroke-chip${stroke === s ? ' selected' : ''}`}
                  onClick={() => setStroke(s)}
                >
                  {capitalize(s)}
                </button>
              ))}
            </div>
          </div>

          {/* Notes */}
          <div className="form-group">
            <label htmlFor="notes">Notes (optional)</label>
            <textarea
              id="notes"
              rows={3}
              placeholder="How did it feel? Any goals for next time?"
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              maxLength={500}
            />
            <span className="char-count">{notes.length}/500</span>
          </div>

          <button type="submit" className="btn-primary">
            Save Workout
          </button>
        </form>
      </div>
    </div>
  );
}

function calcPace(yards: number, mins: number): string {
  if (!yards || !mins) return '—';
  const paceMin = (mins / yards) * 100;
  const m = Math.floor(paceMin);
  const s = Math.round((paceMin - m) * 60);
  return `${m}:${s.toString().padStart(2, '0')}`;
}

function capitalize(s: string) {
  return s.charAt(0).toUpperCase() + s.slice(1);
}
