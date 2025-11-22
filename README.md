# Dodzai full-stack scaffold

This repository contains a minimal FastAPI backend and Vite + React frontend that work together to manage simple tasks. The goal is to provide an end-to-end foundation you can extend with additional business logic, authentication, and deployment automation.

## Backend (FastAPI)

### Features
- FastAPI application with CORS enabled for local development.
- SQLAlchemy models for a `Task` entity (`title`, `description`, `status`, timestamps).
- CRUD routes for listing, creating, reading, updating, and deleting tasks.
- SQLite database by default; override with `DATABASE_URL`.

### Getting started (local)
1. Create and activate a virtual environment.
2. Install dependencies:
   ```bash
   pip install -r backend/requirements.txt
   ```
3. (Optional) Copy `.env.example` to `.env` inside `backend/` to override `DATABASE_URL`.
4. Start the API:
   ```bash
   uvicorn app.main:app --reload --app-dir backend
   ```
5. The server runs at `http://localhost:8000` with interactive docs at `/docs`.

### Getting started (Docker)
1. Build and start the stack:
   ```bash
   docker compose up --build
   ```
2. The backend is available at `http://localhost:8000` and the frontend at `http://localhost:5173`.
3. To persist SQLite data locally, Docker mounts a named volume (`backend_data`).

## Frontend (React + Vite)

### Features
- React UI that lists tasks from the API and allows creating new tasks.
- React Query handles fetching and cache invalidation.
- Environment variable `VITE_API_URL` configures the backend base URL (defaults to `http://localhost:8000`).

### Getting started
1. Install Node.js dependencies:
   ```bash
   cd frontend
   npm install
   ```
2. (Optional) Copy `.env.example` to `.env` and edit `VITE_API_URL` if your backend is hosted elsewhere.
3. Run the dev server:
   ```bash
   npm run dev
   ```
4. Open the printed localhost URL (default `http://localhost:5173`) in your browser.

## Repository layout
- `backend/`: FastAPI application, models, and routing.
- `frontend/`: React client built with Vite. Uses React Query for data fetching.

## Development tips
- Ensure the backend is running before using the frontend to avoid network errors.
- Update `VITE_API_URL` in a `.env` file under `frontend/` if your API host differs from `http://localhost:8000`.
- The backend will automatically create database tables on startup.
