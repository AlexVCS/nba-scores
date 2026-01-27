# AGENTS.md - AI Coding Agent Guidelines

This document provides guidelines for AI coding agents working in the nba-scores codebase.

## Project Overview

NBA Scores is a full-stack web application displaying NBA game scores and boxscores.
- **Frontend**: React 18 + TypeScript + Vite + Tailwind CSS v4
- **Backend**: Python FastAPI server (in `server/`)
- **Package Manager**: pnpm (required)

## Build/Lint/Test Commands

```bash
pnpm install          # Install dependencies
pnpm dev              # Start frontend dev server (http://localhost:5173)
pnpm build            # Build for production
pnpm lint             # Run linting
pnpm preview          # Preview production build
```

**Backend (FastAPI):** `cd server && source venv/bin/activate && uvicorn server.main:app --reload`

**Running both:** Start the backend in one terminal, then run `pnpm dev` in another terminal.

**Testing:** No test framework configured. Recommended: Vitest. Single test: `pnpm test -- <file>`

## Project Structure

```
src/
├── main.tsx              # App entry point, React Router setup
├── App.tsx               # Root component with QueryClientProvider
├── components/           # Reusable UI components
├── routes/games/         # Games list and boxscore views
├── context/              # React Context definitions
├── providers/            # Context provider components
├── hooks/                # Custom React hooks
├── services/             # API service functions
└── helpers/              # Utility functions and shared types

server/                   # Python FastAPI backend
├── main.py               # FastAPI routes
└── requirements.txt      # Python dependencies
```

## Code Style Guidelines

### TypeScript Configuration

- **Target**: ES2020, **Strict mode**: Enabled
- **Path alias**: Use `@/` for `./src/*` imports
- `noUnusedLocals`, `noUnusedParameters`, `noFallthroughCasesInSwitch`: true

### Import Style

```typescript
import {useState, useEffect} from "react";       // External packages first
import {Team, Player} from "@/helpers/helpers";  // Path alias for src files
import StatsTable from "./StatsTable";           // Relative for same directory
```

- Use named imports: `import {useState} from "react"`
- Prefer `@/` path alias over relative paths for cross-directory imports

### Component Patterns

```typescript
interface GameCardProps {
  showScores: boolean;
  game: GameData;
}

function GameCard({game, showScores = false}: GameCardProps) {
  return <div>...</div>;
}

export default GameCard;
```

- Functional components only (no class components)
- Props interface defined inline, above the component
- Default export for all components
- One component per file (named same as file)

### Naming Conventions

| Type | Convention | Example |
|------|------------|---------|
| Components | PascalCase | `GameCard.tsx` |
| Hooks | camelCase with `use` prefix | `useTheme.ts` |
| Services/Helpers | camelCase | `nbaService.ts` |
| Types/Interfaces | PascalCase | `GameCardProps`, `Player` |
| Constants | SCREAMING_SNAKE_CASE | `COLOR_MODE_KEY` |

### Type Definitions

```typescript
export type Theme = "light" | "dark";           // Type alias for unions
export interface Player { personId: number; }   // Interface for object shapes
```

- Define types close to where they're used
- Export shared types from `@/helpers/helpers.tsx`

### Error Handling

```typescript
// API services: throw Error with descriptive message
if (!response.ok) throw new Error("Scoreboard fetch failed");

// localStorage: try/catch with console.log
try {
  window.localStorage.setItem(key, JSON.stringify(value));
} catch (error) {
  console.log(error);
}

// Hooks: throw Error for invalid context usage
if (context === undefined) {
  throw new Error('useTheme must be used within a ThemeProvider');
}
```

### State Management

- **Server state**: TanStack Query (React Query) with `useQuery`
- **Local state**: `useState` + `useEffect`
- **Theme/Global state**: React Context (ThemeContext/ThemeProvider pattern)
- **Persistence**: localStorage via helpers (`setItem`/`getItem`)

### Styling

- **Framework**: Tailwind CSS v4 (utility-first classes)
- **Dark mode**: Class-based (`dark:` prefix)
- **Custom styles**: Inline `style` prop for dynamic values

```tsx
<div className="flex flex-col dark:text-slate-50"
     style={{textShadow: "0 0 5px rgba(245, 158, 11, 0.7)"}}>
```

## Environment Variables

Store in `.env` (gitignored). Access via `import.meta.env.VITE_*`:
- `VITE_API_URL_DEV` - Development API URL (e.g., http://localhost:8000)
- `VITE_API_URL_PROD` - Production API URL

## ESLint

Uses ESLint 9 flat config with TypeScript-ESLint, React Hooks, and React Refresh rules. Run `pnpm lint` before committing.

## Key Dependencies

- **UI**: @adobe/react-spectrum, react-aria, lucide-react
- **Data**: @tanstack/react-query (v5), **Routing**: react-router (v7)
- **Animation**: framer-motion, **Dates**: date-fns, react-day-picker
- **NBA Logos**: react-nba-logos
