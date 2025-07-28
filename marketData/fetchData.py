import pandas as pd
from datetime import datetime
import sheldatagateway
from sheldatagateway import environments
import sys
import os
import concurrent.futures

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from shelConfig import SHEL_USERNAME, SHEL_PASSWORD
from sheldatagateway.core import AuthenticationError

# Print settings (optional for console output)
pd.set_option('display.max_rows', None)
pd.set_option('display.max_columns', None)
pd.set_option('display.width', None)
pd.set_option('display.max_colwidth', None)



def fetch_intraday_bars(ticker, date, interval='15min'):
    trades = []

    if isinstance(date, str):
        date = datetime.strptime(date, "%Y-%m-%d").date()

    #print(f"Starting fetch for {ticker} on {date} with interval {interval}")
    try:
        # Connect to SHEL Data Gateway
        with sheldatagateway.Session(environments.env_defs.Prod, SHEL_USERNAME, SHEL_PASSWORD) as session:
            #print("1")
            def collect_trades(obj):
                #print(obj)
                #print("data started")
                if obj['type'] == 'trade':
                    ## TESTING LINE FOR OFF MARKET PRINTS
                    if 'Drk' not in obj['flags'] and obj['mkt'] != 'FINN':
                        trades.append(obj)

            
            handle = session.request_data(collect_trades, ticker, date, date, ['trade'])
            


            #handle.wait()
            try:
                run_with_timeout(handle.wait, 10)  # 10-second timeout
            except TimeoutError as e:
                print(f"SHEL data fetch timed out for {ticker} on {date}: {e}")
                handle.cancel()
                return pd.DataFrame()
            




            handle.raise_on_error()

    except AuthenticationError as e:
        print("Authentication failed: Invalid SHEL username or password.")
        return pd.DataFrame()

    except Exception as e:
        print(f"Unexpected error during SHEL connection: {e}")
        return pd.DataFrame()

    if not trades:
        print(f"No trades found for {ticker} on {date}")
        return pd.DataFrame()
    
    #print("data finished handling")

    # Convert to DataFrame and adjust time
    df = pd.DataFrame(trades)
    df['time'] = pd.to_datetime(df['time'] / 1e9, unit='s')
    df['time'] = df['time'].dt.tz_localize('UTC').dt.tz_convert('US/Eastern')
    df['time'] = df['time'].dt.tz_localize(None)
    df.set_index('time', inplace=True)

    # Remove any duplicate timestamps
    df = df[~df.index.duplicated(keep='first')]

    # Validate required columns
    if df.empty or 'price' not in df.columns or 'size' not in df.columns:
        print(f"Data invalid or missing required columns for {ticker} on {date}")
        return pd.DataFrame()

    # Create time range from 04:00 to 20:00 for the specified date
    start_time = pd.Timestamp(f"{date} 04:00:00")
    end_time = pd.Timestamp(f"{date} 20:00:00")
    full_index = pd.date_range(start=start_time, end=end_time, freq='1min')
    
    # Reindex to ensure full minute coverage
    df = df.reindex(df.index.union(full_index))


    try:
        bars = df.resample(interval).agg({
            'price': ['first', 'max', 'min', 'last'],
            'size': 'sum'
        })
    except Exception as e:
        print(f"Error during resampling: {e}")
        return pd.DataFrame()

    bars.columns = ['open', 'high', 'low', 'close', 'volume']
    bars[['open', 'high', 'low', 'close']] = bars[['open', 'high', 'low', 'close']].round(2)
    bars = bars.dropna()

    #print(df.columns)
    #print(df.head())
    #print(df.index) 

    ### IF you want to print out the data, uncomment line below this 
    #print(bars)
    #print("\n")

    return bars

#fetch_intraday_bars("TSLA", "2024-06-05", interval='15min')

def run_with_timeout(func, timeout, *args, **kwargs):
    with concurrent.futures.ThreadPoolExecutor() as executor:
        future = executor.submit(func, *args, **kwargs)
        try:
            return future.result(timeout=timeout)
        except concurrent.futures.TimeoutError:
            raise TimeoutError("Function timed out")