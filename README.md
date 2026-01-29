# May

A modern, self-hosted vehicle management application for tracking fuel consumption, expenses, and maintenance across your cars, vans, motorbikes, and scooters.

Named after James May, completing the trio of Top Gear presenters (alongside [Clarkson](https://github.com/linuxserver/Clarkson) and [Hammond](https://github.com/AlfHou/hammond)).

## Features

- **Multi-Vehicle Support**: Track cars, vans, motorbikes, and scooters
- **Fuel Logging**: Record fill-ups with automatic consumption calculations
- **Expense Tracking**: Monitor maintenance, insurance, repairs, and other costs
- **Multi-User**: Share vehicles between family members or team members
- **Analytics Dashboard**: View spending trends and consumption statistics
- **Attachment Support**: Upload receipts and documents
- **Customizable Units**: Support for metric/imperial, multiple currencies
- **Docker Ready**: Easy self-hosting via Docker

## Quick Start with Docker

```bash
# Clone the repository
git clone https://github.com/dannymcc/may.git
cd may

# Start with Docker Compose
docker compose up -d
```

Access the application at `http://localhost:5000`

**Default login:**
- Username: `admin`
- Password: `admin`

⚠️ Change the default password after first login!

## Manual Installation

```bash
# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run the application
python run.py
```

## Configuration

Copy `.env.example` to `.env` and configure:

```bash
# Secret key for session encryption
SECRET_KEY=your-secure-random-string

# Database location (default: SQLite)
DATABASE_URL=sqlite:///data/may.db

# Upload folder for attachments
UPLOAD_FOLDER=/app/data/uploads
```

## Tech Stack

- **Backend**: Python / Flask
- **Database**: SQLite
- **Frontend**: Tailwind CSS, HTMX, Chart.js
- **Server**: Gunicorn

## License

MIT
