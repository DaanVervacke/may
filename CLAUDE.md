# Project Rules

## Git Commits

- Never include "Co-Authored-By: Claude" or similar AI attribution lines in commits

---

# Project Overview

May is a self-hosted vehicle management application built with Flask. It tracks fuel consumption, expenses, maintenance, trips, EV charging, and more.

## Tech Stack

- **Backend**: Flask (Python 3.12)
- **Database**: SQLite with SQLAlchemy ORM
- **Frontend**: Jinja2 templates with Tailwind CSS
- **Charts**: Chart.js
- **PDF Generation**: WeasyPrint
- **Production Server**: Gunicorn

## Project Structure

```
may/
├── app/
│   ├── __init__.py          # App factory, blueprint registration
│   ├── models.py             # SQLAlchemy models (User, Vehicle, FuelLog, etc.)
│   ├── routes/               # Blueprint route handlers
│   │   ├── main.py           # Dashboard, timeline
│   │   ├── auth.py           # Login, register, settings
│   │   ├── vehicles.py       # Vehicle CRUD
│   │   ├── fuel.py           # Fuel logging
│   │   ├── expenses.py       # Expense tracking
│   │   ├── trips.py          # Trip logging
│   │   ├── charging.py       # EV charging sessions
│   │   ├── stations.py       # Fuel stations, price tracking
│   │   └── ...
│   ├── templates/            # Jinja2 templates
│   └── static/               # CSS, JS, images
├── config.py                 # App configuration, version
├── run.py                    # App entry point
├── Dockerfile                # Container build
├── docker-compose.yml        # Docker deployment
└── docker-entrypoint.sh      # Handles bind mount permissions
```

## Key Models

- **User**: Authentication, preferences, menu visibility settings
- **Vehicle**: Cars, motorcycles, etc. with fuel type support
- **FuelLog**: Fuel fill-ups with consumption calculation
- **Expense**: Maintenance, insurance, tax, etc.
- **Trip**: Business/personal trip logging for tax purposes
- **ChargingSession**: EV charging with kWh, SOC%, cost
- **AppSettings**: Key-value store for app-wide settings (branding, registration toggle)

## Database

SQLite database stored at `/data/may.db`. Flask-SQLAlchemy handles migrations via `db.create_all()` on startup. For schema changes to existing columns, use SQLite ALTER TABLE commands.

## Deployment

### GitHub Actions Workflow

The project uses GitHub Actions (`.github/workflows/docker-build.yml`) to automatically build and push Docker images:

1. On push to `main` or new tags, the workflow triggers
2. Builds a multi-platform Docker image (linux/amd64, linux/arm64)
3. Pushes to GitHub Container Registry: `ghcr.io/dannymcc/may`
4. Tags: `latest` for main branch, version tags (e.g., `v0.3.0`) for releases

### Creating a Release

1. Update `APP_VERSION` in `config.py`
2. Commit and push changes
3. Create a GitHub release with a version tag (e.g., `v0.3.0`)
4. GitHub Actions builds and pushes the Docker image automatically

### Docker Deployment

The container:
- Exposes port **5050** (not 5000)
- Runs as non-root user `may` via entrypoint script
- Handles bind mount permissions automatically
- Health check endpoint: `/health`

Example docker-compose.yml for deployment:
```yaml
services:
  may:
    image: ghcr.io/dannymcc/may:latest
    container_name: may
    restart: unless-stopped
    ports:
      - "5050:5050"
    volumes:
      - ./data:/app/data
    environment:
      - SECRET_KEY=your-secret-key
```

### Reverse Proxy (Caddy)

When using Caddy as a reverse proxy with May running in Docker:
- Connect both containers to the same Docker network
- Use the container name and internal port: `reverse_proxy may:5050`

## Testing Locally

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run development server
python run.py
```

Default login: `admin` / `admin`
