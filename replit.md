# Flask Order Processing API

## Overview
A minimal Python/Flask REST API that provides health checks and order processing endpoints.

## Tech Stack
- **Language:** Python 3
- **Framework:** Flask 3.0.0
- **Production Server:** Gunicorn 21.2.0
- **Other deps:** requests, python-dotenv

## Project Structure
```
app.py            # Main Flask application
requirements.txt  # Python dependencies
Procfile          # Process definition (gunicorn)
```

## API Endpoints
- `GET /health` — Returns `{"status": "healthy"}` with 200
- `POST /process-order` — Accepts JSON `{"orderId": "..."}`, returns `{"status": "success", "orderId": "..."}`

## Running Locally
The "Start application" workflow runs:
```
python app.py
```
App listens on `0.0.0.0:5000`.

## Deployment
Configured as **autoscale** using gunicorn:
```
gunicorn --bind=0.0.0.0:5000 --reuse-port app:app
```
