"""
Stock Prediction Automation System - Railway Version
Runs once daily at 9:30 AM EST for 2 weeks
"""

import os
import sys
import yfinance as yf
import pandas as pd
from openai import OpenAI
from datetime import datetime, timedelta
from openpyxl import Workbook, load_workbook
from openpyxl.styles import Font, Alignment, PatternFill
import time
import json

# Load environment variables from .env file (for local development)
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # python-dotenv not installed, will use system environment variables

# Configuration
TICKERS = ["TSLA", "NVDA", "AMZN", "META", "AAPL"]
OUTPUT_FILE = "predictions.xlsx"
LOG_FILE = "run_log.txt"
CONFIG_FILE = "config.json"
MODEL = "gpt-4o"

# Get API key from environment variable
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")

client = None


def get_openai_client():
    global client
    if client is None:
        if not OPENAI_API_KEY:
            raise ValueError("Set OPENAI_API_KEY environment variable in Railway")
        client = OpenAI(api_key=OPENAI_API_KEY)
    return client


def log(message: str):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_msg = f"[{timestamp}] {message}"
    print(log_msg)
    with open(LOG_FILE, "a") as f:
        f.write(log_msg + "\n")


def get_config():
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "r") as f:
            return json.load(f)
    else:
        config = {
            "start_date": "2026-01-14",
            "end_date": "2026-02-01",
            "run_count": 0,
            "max_runs": 13  # Trading days from Jan 14 - Feb 1
        }
        save_config(config)
        return config


def save_config(config):
    with open(CONFIG_FILE, "w") as f:
        json.dump(config, f, indent=2)


def is_experiment_complete(config) -> bool:
    today = datetime.now().strftime("%Y-%m-%d")
    if today > config["end_date"]:
        return True
    return config["run_count"] >= config["max_runs"]


def is_market_day() -> bool:
    today = datetime.now()
    if today.weekday() > 4:
        return False
    
    holidays = [
        "2025-01-01", "2025-01-20", "2025-02-17", "2025-04-18",
        "2025-05-26", "2025-06-19", "2025-07-04", "2025-09-01",
        "2025-11-27", "2025-12-25",
        "2026-01-01", "2026-01-19", "2026-02-16", "2026-04-03",
        "2026-05-25", "2026-06-19", "2026-07-03", "2026-09-07",
        "2026-11-26", "2026-12-25",
    ]
    
    return today.strftime("%Y-%m-%d") not in holidays


def get_stock_prices(ticker: str) -> dict:
    try:
        stock = yf.Ticker(ticker)
        hist = stock.history(period="5d")
        
        if len(hist) < 2:
            log(f"Warning: Not enough data for {ticker}")
            return None
        
        today_open = hist['Open'].iloc[-1]
        today_close = hist['Close'].iloc[-1]
        yesterday_close = hist['Close'].iloc[-2]
        closing_prices = hist['Close'].tail(10).tolist()
        
        return {
            "ticker": ticker,
            "today_open": round(today_open, 2),
            "today_close": round(today_close, 2),
            "yesterday_close": round(yesterday_close, 2),
            "closing_prices": [round(p, 2) for p in closing_prices]
        }
    except Exception as e:
        log(f"Error fetching {ticker}: {e}")
        return None


def create_prompts(ticker: str, closing_prices: list) -> dict:
    price_list = ", ".join([f"${p}" for p in closing_prices])
    
    return {
        "prompt_1": {
            "name": "Basic",
            "text": f"""For the stock ticker {ticker}, predict the direction of the stock price movement for the next trading day.
Respond with ONLY one of the following options:
UP
DOWN
NEUTRAL
Do not include explanations, numbers, probabilities, or additional text."""
        },
        
        "prompt_2": {
            "name": "Price Data",
            "text": f"""You are given recent closing prices for the stock ticker {ticker}.
Closing prices (most recent last):
{price_list}

Based ONLY on the numerical price pattern shown above, predict the direction of the stock's movement for the next trading day.
Respond with ONLY one of the following options:
UP
DOWN
NEUTRAL
Do not include explanations, indicators, probabilities, or any additional text."""
        },
        
        "prompt_3": {
            "name": "Research",
            "text": f"""For the stock ticker {ticker}, research recent financial news, earnings reports, analyst commentary, and market-relevant events from the past 24–48 hours.
Using your understanding of current news sentiment AND general market context, predict the direction of the stock's movement for the next trading day.
Respond with ONLY one of the following options:
UP
DOWN
NEUTRAL
Do not include explanations, sources, probabilities, numbers, or any additional text."""
        }
    }


def get_prediction(prompt: str) -> str:
    try:
        response = get_openai_client().chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": "You are a financial analyst. Respond only with UP, DOWN, or NEUTRAL."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=10,
            temperature=0.1
        )
        
        result = response.choices[0].message.content.strip().upper()
        
        for valid in ["UP", "DOWN", "NEUTRAL"]:
            if valid in result:
                return valid
        return "INVALID"
        
    except Exception as e:
        log(f"API Error: {e}")
        return "ERROR"


def initialize_excel():
    if os.path.exists(OUTPUT_FILE):
        return
    
    wb = Workbook()
    ws = wb.active
    ws.title = "Predictions"
    
    headers = ["Day #", "Date", "Ticker", "Open", "Close", "Prompt 1", "Prompt 2", "Prompt 3", "Actual", "P1 ✓", "P2 ✓", "P3 ✓"]
    
    header_fill = PatternFill(start_color="4472C4", end_color="4472C4", fill_type="solid")
    header_font = Font(bold=True, color="FFFFFF")
    
    for col, header in enumerate(headers, 1):
        cell = ws.cell(row=1, column=col, value=header)
        cell.fill = header_fill
        cell.font = header_font
        cell.alignment = Alignment(horizontal='center')
    
    wb.save(OUTPUT_FILE)
    log(f"Created {OUTPUT_FILE}")


def run_daily():
    config = get_config()
    
    if is_experiment_complete(config):
        log("=" * 60)
        log("EXPERIMENT COMPLETE! 2 weeks of data collected.")
        log("=" * 60)
        return
    
    if not is_market_day():
        log("Market closed today. Skipping.")
        return
    
    log("=" * 60)
    log(f"DAY {config['run_count'] + 1} of {config['max_runs']}")
    log("=" * 60)
    
    initialize_excel()
    
    wb = load_workbook(OUTPUT_FILE)
    ws = wb.active
    
    today = datetime.now().strftime("%Y-%m-%d")
    day_num = config['run_count'] + 1
    
    for ticker in TICKERS:
        log(f"\n{ticker}:")
        
        prices = get_stock_prices(ticker)
        if not prices:
            continue
        
        log(f"  Today Open: ${prices['today_open']}")
        log(f"  Today Close: ${prices['today_close']}")
        log(f"  Yesterday Close: ${prices['yesterday_close']}")
        
        if prices['today_open'] > prices['yesterday_close']:
            actual = "UP"
        elif prices['today_open'] < prices['yesterday_close']:
            actual = "DOWN"
        else:
            actual = "NEUTRAL"
        
        log(f"  Actual: {actual}")
        
        prompts = create_prompts(ticker, prices['closing_prices'])
        
        predictions = {}
        for key, prompt_data in prompts.items():
            pred = get_prediction(prompt_data['text'])
            predictions[key] = pred
            log(f"  {prompt_data['name']}: {pred}")
            time.sleep(0.5)
        
        p1_correct = "✓" if predictions['prompt_1'] == actual else "✗"
        p2_correct = "✓" if predictions['prompt_2'] == actual else "✗"
        p3_correct = "✓" if predictions['prompt_3'] == actual else "✗"
        
        next_row = ws.max_row + 1
        row_data = [
            day_num, today, ticker,
            prices['today_open'], prices['today_close'],
            predictions['prompt_1'], predictions['prompt_2'], predictions['prompt_3'],
            actual, p1_correct, p2_correct, p3_correct
        ]
        
        for col, value in enumerate(row_data, 1):
            cell = ws.cell(row=next_row, column=col, value=value)
            cell.alignment = Alignment(horizontal='center')
            if col >= 10:
                if value == "✓":
                    cell.font = Font(color="008000", bold=True)
                else:
                    cell.font = Font(color="FF0000")
    
    wb.save(OUTPUT_FILE)
    
    config['run_count'] += 1
    save_config(config)
    
    log(f"\nDay {day_num} complete! Runs until Feb 1st.")


def generate_report():
    if not os.path.exists(OUTPUT_FILE):
        print("No data file found.")
        return
    
    df = pd.read_excel(OUTPUT_FILE)
    
    if df.empty:
        print("No data collected yet.")
        return
    
    print("\n" + "=" * 60)
    print("FINAL RESULTS")
    print("=" * 60)
    
    total = len(df)
    days = df['Day #'].nunique()
    
    print(f"\nPredictions: {total} | Days: {days}")
    
    for col, name in [('P1 ✓', 'Prompt 1 (Basic)'), ('P2 ✓', 'Prompt 2 (Price Data)'), ('P3 ✓', 'Prompt 3 (Research)')]:
        correct = (df[col] == '✓').sum()
        accuracy = (correct / total) * 100
        print(f"{name}: {correct}/{total} = {accuracy:.1f}%")


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--report":
        generate_report()
    else:
        run_daily()
