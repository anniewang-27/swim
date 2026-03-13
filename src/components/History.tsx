import { useState } from 'react';
import type { Workout, StrokeType } from '../types';
import { formatDate, pacePerHundred } from '../utils';
import { Trash2, ChevronDown, ChevronUp } from 'lucide-react';

interface HistoryProps {
  workouts: Workout[];
  onDelete: (id: string) => void;
}

type SortField = 'date' | 'distance' | 'duration';

function SortIcon({
  field,
  sortField,
  sortAsc,
}: {
  field: SortField;
  sortField: SortField;
  sortAsc: boolean;
}) {
  if (sortField !== field) return null;
  return sortAsc ? <ChevronUp size={14} /> : <ChevronDown size={14} />;
}

export default function History({ workouts, onDelete }: HistoryProps) {
  const [search, setSearch] = useState('');
  const [strokeFilter, setStrokeFilter] = useState<StrokeType | 'all'>('all');
  const [sortField, setSortField] = useState<SortField>('date');
  const [sortAsc, setSortAsc] = useState(false);
  const [deleteId, setDeleteId] = useState<string | null>(null);

  const filtered = workouts
    .filter((w) => {
      const matchStroke = strokeFilter === 'all' || w.stroke === strokeFilter;
      const matchSearch =
        search === '' ||
        w.date.includes(search) ||
        w.notes.toLowerCase().includes(search.toLowerCase()) ||
        w.stroke.includes(search.toLowerCase());
      return matchStroke && matchSearch;
    })
    .sort((a, b) => {
      let diff = 0;
      if (sortField === 'date') diff = a.date.localeCompare(b.date);
      if (sortField === 'distance') diff = a.distanceYards - b.distanceYards;
      if (sortField === 'duration') diff = a.durationMinutes - b.durationMinutes;
      return sortAsc ? diff : -diff;
    });

  function toggleSort(field: SortField) {
    if (sortField === field) setSortAsc((v) => !v);
    else {
      setSortField(field);
      setSortAsc(false);
    }
  }

  return (
    <div className="page">
      <h1 className="page-title">Workout History</h1>

      {/* Filters */}
      <div className="filter-bar">
        <input
          type="text"
          placeholder="Search by date, stroke, or notes…"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="search-input"
        />
        <select
          value={strokeFilter}
          onChange={(e) => setStrokeFilter(e.target.value as StrokeType | 'all')}
          className="stroke-select"
        >
          <option value="all">All Strokes</option>
          <option value="freestyle">Freestyle</option>
          <option value="backstroke">Backstroke</option>
          <option value="breaststroke">Breaststroke</option>
          <option value="butterfly">Butterfly</option>
          <option value="mixed">Mixed</option>
        </select>
      </div>

      {filtered.length === 0 ? (
        <div className="empty-state">
          {workouts.length === 0
            ? 'No workouts logged yet. Head to "Log Workout" to add your first!'
            : 'No workouts match your filters.'}
        </div>
      ) : (
        <div className="card table-card">
          <div className="table-meta">{filtered.length} workout{filtered.length !== 1 ? 's' : ''}</div>
          <div className="table-wrapper">
            <table className="workout-table">
              <thead>
                <tr>
                  <th onClick={() => toggleSort('date')} className="sortable">
                    Date <SortIcon field="date" sortField={sortField} sortAsc={sortAsc} />
                  </th>
                  <th onClick={() => toggleSort('distance')} className="sortable">
                    Distance <SortIcon field="distance" sortField={sortField} sortAsc={sortAsc} />
                  </th>
                  <th onClick={() => toggleSort('duration')} className="sortable">
                    Time <SortIcon field="duration" sortField={sortField} sortAsc={sortAsc} />
                  </th>
                  <th>Pace</th>
                  <th>Stroke</th>
                  <th>Notes</th>
                  <th></th>
                </tr>
              </thead>
              <tbody>
                {filtered.map((w) => (
                  <tr key={w.id}>
                    <td>{formatDate(w.date)}</td>
                    <td>{w.distanceYards.toLocaleString()} yd</td>
                    <td>{w.durationMinutes} min</td>
                    <td className="pace-cell">
                      {pacePerHundred(w.distanceYards, w.durationMinutes)}/100yd
                    </td>
                    <td>
                      <span className={`stroke-badge stroke-${w.stroke}`}>
                        {capitalize(w.stroke)}
                      </span>
                    </td>
                    <td className="notes-cell">{w.notes || '—'}</td>
                    <td>
                      {deleteId === w.id ? (
                        <div className="confirm-delete">
                          <button
                            className="btn-danger-sm"
                            onClick={() => {
                              onDelete(w.id);
                              setDeleteId(null);
                            }}
                          >
                            Confirm
                          </button>
                          <button
                            className="btn-cancel-sm"
                            onClick={() => setDeleteId(null)}
                          >
                            Cancel
                          </button>
                        </div>
                      ) : (
                        <button
                          className="delete-btn"
                          onClick={() => setDeleteId(w.id)}
                          title="Delete workout"
                        >
                          <Trash2 size={15} />
                        </button>
                      )}
                    </td>
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

function capitalize(s: string) {
  return s.charAt(0).toUpperCase() + s.slice(1);
}
