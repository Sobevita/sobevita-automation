# Flask Order Processing API

## Overview
A minimal Python/Flask REST API that provides health checks, order processing, and AI-powered product sync via Anthropic Claude.

## Tech Stack
- **Language:** Python 3
- **Framework:** Flask 3.0.0
- **Production Server:** Gunicorn 21.2.0
- **AI:** Anthropic Claude (claude-opus-4-5)
- **Other deps:** requests, python-dotenv, anthropic

## Project Structure
```
app.py            # Main Flask application
requirements.txt  # Python dependencies
Procfile          # Process definition (gunicorn)
```

## API Endpoints

### `GET /health`
Returns `{"status": "healthy"}` with 200.

### `POST /process-order`
Accepts JSON `{"orderId": "..."}`, returns `{"status": "success", "orderId": "..."}`.

### `POST /sync-tradelle`
Accepts a list of products and uses Claude to analyze them. Returns:
- **categories** — products grouped by category
- **insights** — 2–3 actionable inventory/pricing insights
- **flagged** — products needing attention (zero stock, missing price, low inventory)

**Request body:**
```json
{
  "products": [
    {"name": "Widget", "price": 9.99, "category": "Tools", "stock": 50}
  ]
}
```

## Environment Variables / Secrets
- `ANTHROPIC_API_KEY` — required for `/sync-tradelle` Claude integration

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
