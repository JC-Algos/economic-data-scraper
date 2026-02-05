"""
Backend API for Economic Data Scraper
Deploy this to Heroku, Railway, Render, or any Python hosting service

Uses ScraperAPI to bypass Cloudflare protection on investing.com
"""

from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
import re
import logging
import os
import time

app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ScraperAPI configuration
SCRAPER_API_KEY = os.environ.get('SCRAPER_API_KEY', 'your-scraper-api-key-here')
SCRAPER_API_URL = 'https://api.scraperapi.com/'

# Optional: Add API key authentication for security
API_KEY = "your-secret-api-key-change-this"  # Change this!
USE_API_KEY = False  # Set to True to enable API key authentication

def get_urls(country):
    """Get URLs for economic indicators based on country"""
    if country == "US":
        return [
            "https://www.investing.com/economic-calendar/unemployment-rate-300",
            "https://www.investing.com/economic-calendar/nonfarm-payrolls-227",
            "https://www.investing.com/economic-calendar/average-hourly-earnings-8",
            "https://www.investing.com/economic-calendar/average-hourly-earnings-1777",
            "https://www.investing.com/economic-calendar/adp-nonfarm-employment-change-1",
            "https://www.investing.com/economic-calendar/core-pce-price-index-905",
            "https://www.investing.com/economic-calendar/core-pce-price-index-61",
            "https://www.investing.com/economic-calendar/cpi-733",
            "https://www.investing.com/economic-calendar/cpi-69",
            "https://www.investing.com/economic-calendar/core-cpi-736",
            "https://www.investing.com/economic-calendar/core-cpi-56",
            "https://www.investing.com/economic-calendar/core-ppi-62",
            "https://www.investing.com/economic-calendar/ppi-238",
            "https://www.investing.com/economic-calendar/ism-manufacturing-pmi-173",
            "https://www.investing.com/economic-calendar/ism-non-manufacturing-pmi-176",
            "https://www.investing.com/economic-calendar/industrial-production-1755",
            "https://www.investing.com/economic-calendar/industrial-production-161",
            "https://www.investing.com/economic-calendar/core-retail-sales-63",
            "https://www.investing.com/economic-calendar/retail-sales-256",
            "https://www.investing.com/economic-calendar/housing-starts-151",
            "https://www.investing.com/economic-calendar/existing-home-sales-99",
            "https://www.investing.com/economic-calendar/new-home-sales-222",
            "https://www.investing.com/economic-calendar/cb-consumer-confidence-48",
            "https://www.investing.com/economic-calendar/gdp-375",
            "https://www.investing.com/economic-calendar/durable-goods-orders-86",
            "https://www.investing.com/economic-calendar/core-durable-goods-orders-59",
        ]
    elif country == "China":
        return [
            "https://www.investing.com/economic-calendar/chinese-exports-595",
            "https://www.investing.com/economic-calendar/chinese-imports-867",
            "https://www.investing.com/economic-calendar/chinese-trade-balance-466",
            "https://www.investing.com/economic-calendar/chinese-fixed-asset-investment-460",
            "https://www.investing.com/economic-calendar/chinese-industrial-production-462",
            "https://www.investing.com/economic-calendar/chinese-unemployment-rate-1793",
            "https://www.investing.com/economic-calendar/chinese-cpi-743",
            "https://www.investing.com/economic-calendar/chinese-cpi-459",
            "https://www.investing.com/economic-calendar/chinese-ppi-464",
            "https://www.investing.com/economic-calendar/chinese-new-loans-1060",
            "https://www.investing.com/economic-calendar/chinese-outstanding-loan-growth-1081",
            "https://www.investing.com/economic-calendar/chinese-total-social-financing-1919",
            "https://www.investing.com/economic-calendar/china-loan-prime-rate-5y-2225",
            "https://www.investing.com/economic-calendar/pboc-loan-prime-rate-1967",
            "https://www.investing.com/economic-calendar/chinese-caixin-services-pmi-596",
            "https://www.investing.com/economic-calendar/chinese-composite-pmi-1913",
            "https://www.investing.com/economic-calendar/chinese-manufacturing-pmi-594",
            "https://www.investing.com/economic-calendar/chinese-non-manufacturing-pmi-831",
        ]
    return []

def fetch_via_scraperapi(url, timeout=60):
    """Fetch a URL via ScraperAPI to bypass Cloudflare"""
    payload = {
        'api_key': SCRAPER_API_KEY,
        'url': url,
        'render': 'true'
    }
    response = requests.get(SCRAPER_API_URL, params=payload, timeout=timeout)
    return response

def scrape_data(urls):
    """Scrape economic data from investing.com via ScraperAPI"""
    data = []
    current_date = datetime.now()
    current_month = current_date.replace(day=1)

    for url in urls:
        try:
            logger.info(f"Scraping: {url}")
            response = fetch_via_scraperapi(url)

            if response.status_code != 200:
                logger.error(f"ScraperAPI returned {response.status_code} for {url}")
                continue

            soup = BeautifulSoup(response.content, 'html.parser')
            title = soup.title.string if soup.title else "No title"

            # Try different table selectors
            rows = soup.find_all('tr', class_='js-event-item')  # New investing.com format
            if not rows:
                rows = soup.find_all('tr')  # Fallback to all rows

            logger.info(f"Found {len(rows)} rows for {url}")

            row_counter = 0
            found_data = False

            for row in rows:
                if row_counter >= 6:
                    break

                cols = row.find_all('td')
                logger.debug(f"Row has {len(cols)} columns")

                # Try both 6 and 7 column formats
                if len(cols) >= 6:
                    try:
                        # Extract text from columns
                        cols_text = [col.text.strip() for col in cols[:6]]

                        # Skip future months
                        date_str = cols_text[0]
                        if is_future_month(date_str, current_month, current_date):
                            continue

                        data.append({
                            'title': title,
                            'date': cols_text[0],
                            'time': cols_text[1],
                            'actual': cols_text[2] if cols_text[2] else None,
                            'forecast': cols_text[3] if cols_text[3] else None,
                            'previous': cols_text[4] if cols_text[4] else None
                        })
                        row_counter += 1
                        found_data = True
                        logger.info(f"Successfully scraped row: {cols_text[0]}")
                    except Exception as e:
                        logger.debug(f"Error processing row: {str(e)}")
                        continue

            if not found_data:
                logger.warning(f"No data found for {url}")

            # Small delay between requests to be respectful
            time.sleep(0.5)

        except Exception as e:
            logger.error(f"Error scraping {url}: {str(e)}")

    logger.info(f"Total data points scraped: {len(data)}")
    return data

def is_future_month(date_str, current_month, current_date):
    """Check if date is in a future month"""
    date, month_in_parentheses = parse_date(date_str)
    if date:
        if date.replace(day=1) > current_month:
            return True
        if date.replace(day=1) == current_month and month_in_parentheses:
            return month_in_parentheses.lower() != current_date.strftime("%b").lower()
    return False

def parse_date(date_str):
    """Parse date string from investing.com format"""
    patterns = [
        r'(\w+ \d{2}, \d{4}) \((\w+)\)',
        r'(\w+ \d{2}, \d{4})',
        r'(\w+ \d{2}, \d{4}) \(Q\d\)'
    ]

    for pattern in patterns:
        match = re.match(pattern, date_str)
        if match:
            try:
                date = datetime.strptime(match.group(1), '%b %d, %Y')
                month_in_parentheses = match.group(2) if len(match.groups()) > 1 else None
                return date, month_in_parentheses
            except:
                pass

    return None, None

def parse_value(value):
    """Parse numeric value from string"""
    if isinstance(value, str):
        value = value.strip().rstrip('%').replace(',', '')
        if value.endswith('B'):
            return float(value[:-1]) * 1e9
        elif value.endswith('M'):
            return float(value[:-1]) * 1e6
        elif value.endswith('K'):
            return float(value[:-1]) * 1e3
        else:
            return float(value)
    return value

def calculate_vs_forecast(actual, forecast, indicator, lower_is_better):
    """Compare actual vs forecast values"""
    if not actual or not forecast or actual == '' or forecast == '':
        return ''

    try:
        actual_val = parse_value(actual)
        forecast_val = parse_value(forecast)

        if indicator in lower_is_better:
            return "較好" if actual_val < forecast_val else "較差" if actual_val > forecast_val else "持平"
        else:
            return "較好" if actual_val > forecast_val else "較差" if actual_val < forecast_val else "持平"
    except:
        return ''

def get_lower_is_better(country):
    """Get list of indicators where lower values are better"""
    if country == "US":
        return [
            "United States Unemployment Rate",
            "United States Core PCE Price Index YoY",
            "United States Core PCE Price Index MoM",
            "United States Core Consumer Price Index (CPI) YoY",
            "United States Core Consumer Price Index (CPI) MoM",
            "United States Consumer Price Index (CPI) YoY",
            "United States Consumer Price Index (CPI) MoM",
            "United States Core Producer Price Index (PPI) MoM",
            "United States Producer Price Index (PPI) MoM"
        ]
    elif country == "China":
        return [
            "Chinese Unemployment Rate",
            "China Loan Prime Rate 5Y",
            "People's Bank of China Loan Prime Rate"
        ]
    return []

def process_data(raw_data, country):
    """Process raw scraped data into structured format"""
    indicators = {}
    lower_is_better = get_lower_is_better(country)

    # Group data by indicator
    for item in raw_data:
        indicator = item['title'].split(' - ')[0] if ' - ' in item['title'] else item['title']

        if indicator not in indicators:
            indicators[indicator] = []

        date, month_in_parentheses = parse_date(item['date'])
        if date:
            vs_forecast = calculate_vs_forecast(
                item['actual'],
                item['forecast'],
                indicator,
                lower_is_better
            )

            indicators[indicator].append({
                'date': date.isoformat(),
                'monthInParentheses': month_in_parentheses,
                'vsForcast': vs_forecast,
                'forecast': item['forecast'] if item['forecast'] and item['forecast'] != '-' else None,
                'actual': item['actual'] if item['actual'] and item['actual'] != '-' else None
            })

    # Format for frontend - map data to actual calendar months
    result = []
    now = datetime.now()
    current_month = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    # Build list of target months: this month, 1 month ago, 2 months ago, etc.
    target_months = []
    for i in range(5):
        m = current_month - timedelta(days=1)  # go to previous month
        if i == 0:
            m = current_month
        else:
            m = current_month
            for _ in range(i):
                m = (m - timedelta(days=1)).replace(day=1)
        target_months.append(m)

    # Month abbreviation map for matching monthInParentheses
    month_abbrs = {
        'Jan': 1, 'Feb': 2, 'Mar': 3, 'Apr': 4, 'May': 5, 'Jun': 6,
        'Jul': 7, 'Aug': 8, 'Sep': 9, 'Oct': 10, 'Nov': 11, 'Dec': 12
    }

    for indicator, data_points in indicators.items():
        if data_points:
            sorted_data = sorted(data_points, key=lambda x: x['date'], reverse=True)

            # Get latest data point that has actual data
            latest = None
            for dp in sorted_data:
                if dp['actual']:
                    latest = dp
                    break
            if not latest:
                latest = sorted_data[0]

            date_obj = datetime.fromisoformat(latest['date'])
            date_str = date_obj.strftime("%b %d, %Y")
            if latest['monthInParentheses']:
                date_str += f" ({latest['monthInParentheses']})"

            # Map data points to calendar months using monthInParentheses
            # The reference month (in parentheses) tells us which calendar month this data belongs to
            month_data = {}  # key: (year, month) -> data point
            for dp in sorted_data:
                ref_month = dp.get('monthInParentheses')
                release_date = datetime.fromisoformat(dp['date'])
                if ref_month and ref_month in month_abbrs:
                    # Use the reference month from parentheses
                    ref_month_num = month_abbrs[ref_month]
                    # Determine the year: if reference month > release month, it's previous year
                    ref_year = release_date.year
                    if ref_month_num > release_date.month:
                        ref_year -= 1
                    key = (ref_year, ref_month_num)
                else:
                    # No parentheses - use the release date's month
                    key = (release_date.year, release_date.month)

                if key not in month_data:
                    month_data[key] = dp

            # Map to target months (本月, 1月前, 2月前, 3月前, 4月前)
            def get_month_value(month_idx):
                target = target_months[month_idx]
                key = (target.year, target.month)
                dp = month_data.get(key)
                if dp and dp['actual']:
                    return dp['actual']
                return 'None'

            # Build historical data for charts
            historical_data = []
            for dp in sorted_data[:10]:
                try:
                    historical_data.append({
                        'date': dp['date'],
                        'actual': float(parse_value(dp['actual'])) if dp['actual'] else None,
                        'forecast': float(parse_value(dp['forecast'])) if dp['forecast'] else None
                    })
                except:
                    pass

            result.append({
                'indicator': indicator,
                'date': date_str,
                'vsForcast': latest['vsForcast'] if latest['actual'] else '',
                'forecast': latest['forecast'] if latest['forecast'] else 'None',
                'current': get_month_value(0),   # 本月 (this month)
                'month1': get_month_value(1),    # 1月前
                'month2': get_month_value(2),    # 2月前
                'month3': get_month_value(3),    # 3月前
                'month4': get_month_value(4),    # 4月前
                'category': get_category(indicator, country),
                'historicalData': historical_data
            })

    return result

def get_category(indicator, country):
    """Determine category of indicator"""
    employment_keywords = ['employment', 'unemployment', 'payroll', 'earnings']
    inflation_keywords = ['cpi', 'ppi', 'pce', 'price index', 'inflation']

    indicator_lower = indicator.lower()

    if any(keyword in indicator_lower for keyword in employment_keywords):
        return 'employment'
    elif any(keyword in indicator_lower for keyword in inflation_keywords):
        return 'inflation'
    else:
        return 'other'

@app.before_request
def check_api_key():
    """Optional API key authentication"""
    if USE_API_KEY:
        api_key = request.headers.get('X-API-Key')
        if api_key != API_KEY:
            return jsonify({'error': 'Unauthorized'}), 401

@app.route('/', methods=['GET'])
def home():
    """Serve frontend or health check"""
    if request.args.get('health') == '1':
        return jsonify({
            'status': 'running',
            'message': 'Economic Data Scraper API',
            'endpoints': {
                '/scrape': 'GET - Scrape economic data (params: country=US|China)'
            }
        })
    return send_from_directory('.', 'frontend.html')

@app.route('/scrape', methods=['GET'])
def scrape():
    """Main scraping endpoint"""
    country = request.args.get('country', 'US')

    if country not in ['US', 'China']:
        return jsonify({'error': 'Invalid country. Use US or China'}), 400

    logger.info(f"Scraping data for {country}")

    try:
        urls = get_urls(country)
        logger.info(f"Processing {len(urls)} URLs")

        raw_data = scrape_data(urls)
        logger.info(f"Raw data scraped: {len(raw_data)} data points")

        processed_data = process_data(raw_data, country)

        logger.info(f"Successfully processed {len(processed_data)} indicators")

        return jsonify({
            'success': True,
            'country': country,
            'data': processed_data,
            'raw_count': len(raw_data),
            'processed_count': len(processed_data),
            'timestamp': datetime.now().isoformat()
        })

    except Exception as e:
        logger.error(f"Error in scrape endpoint: {str(e)}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/debug', methods=['GET'])
def debug():
    """Debug endpoint to test a single URL"""
    test_url = "https://www.investing.com/economic-calendar/unemployment-rate-300"

    try:
        response = fetch_via_scraperapi(test_url)
        soup = BeautifulSoup(response.content, 'html.parser')

        # Find all tables
        tables = soup.find_all('table')
        all_rows = soup.find_all('tr')
        event_rows = soup.find_all('tr', class_='js-event-item')

        # Sample first few rows
        sample_rows = []
        for row in all_rows[:10]:
            cols = row.find_all('td')
            sample_rows.append({
                'num_cols': len(cols),
                'classes': row.get('class', []),
                'sample_text': [col.text.strip()[:50] for col in cols[:3]]
            })

        return jsonify({
            'success': True,
            'url': test_url,
            'status_code': response.status_code,
            'title': soup.title.string if soup.title else 'No title',
            'num_tables': len(tables),
            'num_rows': len(all_rows),
            'num_event_rows': len(event_rows),
            'sample_rows': sample_rows
        })

    except Exception as e:
        logger.error(f"Error in debug endpoint: {str(e)}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
