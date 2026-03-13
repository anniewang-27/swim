# Swim

**Swim** is a smart swimming workout tracker with AI-powered insights. It is the final project for 05-318 (Human-AI Interaction) at Carnegie Mellon University.

## Features

- **Dashboard** – Overview of your total distance, time logged, average workout length, and most recent pace. Includes a chart of distance over your last 10 sessions plus a stroke-breakdown bar chart.
- **Log Workout** – Quickly record a swim with date, distance (yards), duration (minutes), primary stroke, and optional notes. A live pace preview updates as you type.
- **History** – Sortable, filterable table of all past workouts. Filter by stroke type or search by date/notes. Delete individual entries.
- **AI Insights** – Rule-based AI engine that analyses your history and surfaces personalised recommendations, achievement badges, trend alerts, and training tips.

## Tech Stack

- [React 19](https://react.dev/) + [TypeScript](https://www.typescriptlang.org/)
- [Vite](https://vite.dev/) for fast dev/build
- [Recharts](https://recharts.org/) for charts
- [Lucide React](https://lucide.dev/) for icons
- `localStorage` for persistence (no backend required)

## Getting Started

```bash
npm install
npm run dev
```

Then open [http://localhost:5173](http://localhost:5173).

## Build

```bash
npm run build
```

## Linting

```bash
npm run lint
```
