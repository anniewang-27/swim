import { useState } from 'react';
import type { Page, Workout } from './types';
import { loadWorkouts, saveWorkouts } from './utils';
import Nav from './components/Nav';
import Dashboard from './components/Dashboard';
import LogWorkout from './components/LogWorkout';
import History from './components/History';
import Insights from './components/Insights';
import './App.css';

function App() {
  const [page, setPage] = useState<Page>('dashboard');
  const [workouts, setWorkouts] = useState<Workout[]>(loadWorkouts);

  function handleSave(w: Workout) {
    const updated = [...workouts, w];
    setWorkouts(updated);
    saveWorkouts(updated);
  }

  function handleDelete(id: string) {
    const updated = workouts.filter((w) => w.id !== id);
    setWorkouts(updated);
    saveWorkouts(updated);
  }

  return (
    <div className="app">
      <Nav current={page} onChange={setPage} />
      <main className="main-content">
        {page === 'dashboard' && <Dashboard workouts={workouts} />}
        {page === 'log' && (
          <LogWorkout
            onSave={(w) => {
              handleSave(w);
              setPage('dashboard');
            }}
          />
        )}
        {page === 'history' && (
          <History workouts={workouts} onDelete={handleDelete} />
        )}
        {page === 'insights' && <Insights workouts={workouts} />}
      </main>
    </div>
  );
}

export default App;
