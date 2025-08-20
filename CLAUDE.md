# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Q-Vanish is an AI-powered quantitative trading platform built for retail investors. It features a React frontend with a Python FastAPI backend, using SQLite for data persistence and integrating with various financial APIs and AI services.

## Architecture

- **Frontend**: React 18 with TypeScript, Vite, TailwindCSS, and Zustand for state management
- **Backend**: Python FastAPI with SQLAlchemy ORM, SQLite database
- **Communication**: REST API with axios client, JWT authentication
- **AI Integration**: OpenAI API integration for trading assistance via LangChain

The frontend runs on port 3000 and proxies API calls to the backend on port 8000. Authentication uses JWT tokens stored in localStorage with automatic token injection via axios interceptors.

## Development Commands

### Quick Start
```bash
npm run dev          # Start both frontend and backend concurrently
npm run setup        # Install all dependencies (root + frontend)
```

### Frontend Only
```bash
cd frontend
npm run dev          # Start Vite dev server on port 3000
npm run build        # Build for production
npm run preview      # Preview production build
```

### Backend Only
```bash
cd backend
uvicorn app.main:app --reload    # Start FastAPI server on port 8000
```

### Manual Setup
```bash
npm install                      # Install root dependencies
cd frontend && npm install       # Install frontend dependencies
cd ../backend && pip install -r requirements.txt  # Install backend dependencies
```

## Project Structure

```
q-vanish/
├── frontend/                    # React frontend
│   ├── src/
│   │   ├── components/         # Reusable UI components
│   │   ├── pages/             # Route components
│   │   └── services/api.ts    # API client with types
│   ├── vite.config.ts         # Vite config with proxy setup
│   └── package.json
├── backend/                    # FastAPI backend
│   ├── app/
│   │   ├── main.py            # FastAPI app entry point
│   │   ├── config.py          # Environment configuration
│   │   ├── database.py        # SQLAlchemy setup
│   │   ├── models.py          # Database models
│   │   ├── schemas.py         # Pydantic schemas
│   │   ├── crud.py            # Database operations
│   │   ├── routers/           # API route handlers
│   │   └── utils/             # Utility functions and sample data
│   ├── requirements.txt
│   └── data/qvanish.db        # SQLite database file
└── package.json               # Root package with concurrently scripts
```

## Key Integration Points

### API Communication
- Frontend uses axios with base URL `http://localhost:8000/api`
- Vite proxy rewrites `/api` requests to backend
- JWT token automatically added via request interceptor
- 401 responses trigger automatic logout and redirect

**Current Status**: Frontend-backend integration is partially complete:
- Frontend calls are implemented with proper TypeScript interfaces
- Many backend endpoints are missing or have different paths than expected
- API routes like `/dashboard/*`, `/portfolio/*`, `/orders` return 404
- Backend trading logic exists at `/trading/*` but doesn't match frontend expectations

### Database
- SQLAlchemy with SQLite (`data/qvanish.db`)
- Models defined in `backend/app/models.py`
- Database initialized on app startup
- Session management via dependency injection

### Authentication Flow
- Login endpoint: `/api/auth/token` (form-encoded)
- Token stored in localStorage as `authToken`
- Protected routes use `ProtectedRoute` component
- Backend validates JWT tokens for protected endpoints

## Configuration

### Environment Variables
The backend uses python-dotenv to load configuration from environment variables:
- `DATABASE_URL`: Database connection string (defaults to SQLite)
- `SECRET_KEY`: JWT signing key (auto-generated if not set)
- `OPENAI_API_KEY`: Required for AI assistant functionality
- `DEBUG`: Enable debug mode
- `ENVIRONMENT`: Runtime environment

### Frontend Proxy Setup
Vite proxy configuration in `frontend/vite.config.ts` handles API routing:
- `/api/*` requests proxied to `http://localhost:8000`
- Path rewriting removes `/api` prefix
- Enables seamless local development

## API Structure

The backend follows a modular router structure:
- `/api/auth` - Authentication endpoints
- `/api/users` - User management
- `/api/strategies` - Trading strategy CRUD
- `/api/backtest` - Strategy backtesting
- `/api/trading` - Order management
- `/api/market-data` - Market data feeds  
- `/api/ai-assistant` - AI-powered trading assistance

All API types and functions are centralized in `frontend/src/services/api.ts` with TypeScript interfaces matching backend Pydantic schemas.