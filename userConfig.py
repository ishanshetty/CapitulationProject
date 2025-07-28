# user_config.py

#### READ THE README.txt FILE BEFORE RUNNING ###
# === USER CONFIGURATION SECTION === #

# Intervals to test
# ACCEPTABLE INTERVALS
    # "bar-1s", "bar-5s", "bar-15s", "bar-30s", "bar-45s", "bar-1min", "bar-2min", "bar-3min", 
    # "bar-5min", "bar-7min", "bar-10min", "bar-15min", "bar-30min", "bar-1h"
3
INTERVALS_TO_TEST = ["10min", "15min", "30min"]

# Start and end time for trade analysis (24-hour format)
START_TIME = "09:00"
END_TIME = "16:00"

# Path to Excel file with tickers and dates
TRADE_LIST_FILE = "tradeList.xlsx"

# Output Excel file
OUTPUT_FILE = "all_capitulation_results.xlsx"

# === END CONFIGURATION === #


# Now just run the backtest!
from backtester.batchBacktest import backtest_multiple_trades
from shelConfig import SHEL_USERNAME, SHEL_PASSWORD

backtest_multiple_trades(
    excel_path=TRADE_LIST_FILE,
    intervals=INTERVALS_TO_TEST,
    start_time=START_TIME,
    end_time=END_TIME,
    output_path=OUTPUT_FILE
)
