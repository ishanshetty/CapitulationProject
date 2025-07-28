==========================
Capitulation Backtester
==========================

Overview:
----------  
This project is a Python-based backtesting tool used to evaluate capitulation short strategies on intraday stock data. The core components include trade data ingestion from the SHEL Data Gateway, r
esampling into time intervals, strategy execution, and exporting summary statistics to Excel.

Project Folder Structure:
--------------------------
capitulationAnalyzer/
│
├── userConfig.py              # Main file to run — set your inputs and run this script.
├── shelConfig.py              # Stores SHEL_USERNAME and SHEL_PASSWORD credentials.
├── tradeList.xlsx             # Excel input file with tickers, dates, grade, cap(four columns: Ticker, Date, Grade, Cap).
│
├── backtester/
│   ├── batchBacktest.py       # Logic to loop through tickers/dates/intervals and run backtests.
│   └── analyze.py             # Strategy logic and performance metric calculation.
│
├── marketData/
│   └── fetchData.py           # Pulls intraday data from SHEL and resamples into bars.
│
└── all_capitulation_results.xlsx   # Automatically generated output file with results.

How to Run:
------------
1. Open `shelConfig.py`.
2. Set the following variables:
   - `SHEL_USERNAME` and `SHEL_PASSWORD`: Your SHEL Data Gateway credentials.

3. Open `userConfig.py`.
4. Set the following variables:
   - `INTERVALS_TO_TEST`: List of intervals to backtest (e.g., ["10min", "15min"]).
   - `START_TIME` and `END_TIME`: Time window during the trading day to analyze.
   - `TRADE_LIST_FILE`: Path to Excel file containing tickers and dates.
   - `OUTPUT_FILE`: Name of the Excel output file to be generated.

3. Run the file:
   python3 userConfig.py

Important Notes
    Excelfile Ticker Import: tradeList.xlsx(or other excel file) must have no headers.
        Column A: Ticker (e.g., AAPL)
        Column B: Date (format: YYYY-MM-DD)
        Column C: Grade (A, B, C)
        Column D: CAP (Micro, Small, Medium, Large, ETF)

    Output:
    The program will create an Excel file (e.g., all_capitulation_results.xlsx) with:
        Sheet 1: Raw Data
        Sheet 2: Individual trade results
        Sheet 3: Summary grouped by interval
        Sheet 4: Cap and Grade Analysis

    Error Handling:
        If invalid SHEL credentials are provided, the script will print "Authentication failed" and skip processing.
        If no data is found or something goes wrong in the resampling step, the program will print an error and continue gracefully.

    Customization:
        To add more strategies or improve existing ones, modify analyze.py.
        To add more statistics or alter output format, edit batchBacktest.py.

    Notes:
        Ensure sheldatagateway is installed via pip and you're authorized to access the data.
        Timestamps are adjusted to U.S. Eastern Time and normalized to run between 04:00 and 20:00 by default.
