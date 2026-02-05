# JC Algos 經濟數據分析 - Economic Data Scraper

Scrapes US and China economic indicators from investing.com via **ScraperAPI** (bypasses Cloudflare).

## Structure

```
backend/
  app.py              # Flask API server (deploy to your backend VPS)
  requirements.txt    # Python dependencies
frontend/
  economic.html       # Frontend page (deploy to Hostinger)
```

## Backend Setup

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Set your ScraperAPI key
export SCRAPER_API_KEY="your-key-here"

# 3. Run
python app.py
# Runs on port 5000 (or PORT env var)
```

### Deploy as systemd service

```bash
# Create service file
cat > /etc/systemd/system/economic-scraper.service << 'EOF'
[Unit]
Description=Economic Data Scraper API
After=network.target

[Service]
Type=simple
WorkingDirectory=/path/to/backend
Environment=PORT=5005
Environment=SCRAPER_API_KEY=your-key-here
ExecStart=/path/to/venv/bin/python3 app.py
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable economic-scraper
systemctl start economic-scraper
```

## Frontend Setup

1. Open `frontend/economic.html`
2. Change `BACKEND_API_URL` to your backend server URL
3. Upload to Hostinger

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | Health check |
| `/scrape?country=US` | GET | Scrape US economic data |
| `/scrape?country=China` | GET | Scrape China economic data |
| `/debug` | GET | Test single URL |

## ScraperAPI

- Free tier: 5,000 requests/month
- US scan = 26 requests, China scan = 18 requests
- Get key at: https://www.scraperapi.com

## What Changed (from original)

- **Backend:** `requests` → routes through ScraperAPI proxy (`render=true`) to bypass Cloudflare
- **Frontend:** Only `BACKEND_API_URL` changed. Everything else identical.
