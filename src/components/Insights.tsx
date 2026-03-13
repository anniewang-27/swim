import { useMemo } from 'react';
import type { Workout } from '../types';
import { generateInsights } from '../insights';
import { Lightbulb, Trophy, TrendingUp, Sparkles } from 'lucide-react';

interface InsightsProps {
  workouts: Workout[];
}

const iconMap = {
  tip: <Lightbulb size={18} />,
  achievement: <Trophy size={18} />,
  trend: <TrendingUp size={18} />,
  recommendation: <Sparkles size={18} />,
};

const colorMap = {
  tip: 'insight-tip',
  achievement: 'insight-achievement',
  trend: 'insight-trend',
  recommendation: 'insight-recommendation',
};

export default function Insights({ workouts }: InsightsProps) {
  const insights = useMemo(() => generateInsights(workouts), [workouts]);

  return (
    <div className="page">
      <h1 className="page-title">AI Insights</h1>
      <p className="page-subtitle">
        Personalized analysis of your swimming data, powered by pattern
        recognition and training science principles.
      </p>

      <div className="insights-grid">
        {insights.map((ins, i) => (
          <div key={i} className={`insight-card ${colorMap[ins.type]}`}>
            <div className="insight-header">
              <span className="insight-icon">{iconMap[ins.type]}</span>
              <span className="insight-type">{capitalize(ins.type)}</span>
            </div>
            <h3 className="insight-title">{ins.title}</h3>
            <p className="insight-body">{ins.body}</p>
          </div>
        ))}
      </div>
    </div>
  );
}

function capitalize(s: string) {
  return s.charAt(0).toUpperCase() + s.slice(1);
}
