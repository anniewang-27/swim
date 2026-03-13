import type { Page } from '../types';
import { Waves, LayoutDashboard, PlusCircle, Clock, Lightbulb } from 'lucide-react';

interface NavProps {
  current: Page;
  onChange: (p: Page) => void;
}

const links: { page: Page; label: string; icon: React.ReactNode }[] = [
  { page: 'dashboard', label: 'Dashboard', icon: <LayoutDashboard size={18} /> },
  { page: 'log', label: 'Log Workout', icon: <PlusCircle size={18} /> },
  { page: 'history', label: 'History', icon: <Clock size={18} /> },
  { page: 'insights', label: 'AI Insights', icon: <Lightbulb size={18} /> },
];

export default function Nav({ current, onChange }: NavProps) {
  return (
    <nav className="navbar">
      <div className="navbar-brand">
        <Waves size={24} className="brand-icon" />
        <span className="brand-name">Swim</span>
      </div>
      <ul className="nav-links">
        {links.map(({ page, label, icon }) => (
          <li key={page}>
            <button
              className={`nav-btn${current === page ? ' active' : ''}`}
              onClick={() => onChange(page)}
            >
              {icon}
              <span>{label}</span>
            </button>
          </li>
        ))}
      </ul>
    </nav>
  );
}
