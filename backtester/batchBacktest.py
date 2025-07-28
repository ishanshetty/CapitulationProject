import pandas as pd
import sys
import os
import io
import traceback

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from marketData.fetchData import fetch_intraday_bars
from backtester.analyze import run_capitulation_short_strategy_with_metrics

def backtest_multiple_trades(excel_path, intervals, start_time, end_time, output_path):
    # Read all four columns from the start
    try:
        trades = pd.read_excel(excel_path, header=None, names=["Ticker", "Date", "Grade", "Cap"])
        trades["Date"] = pd.to_datetime(trades["Date"], format='%m/%d/%y', errors='coerce').dt.strftime("%Y-%m-%d")
        print(f"Raw trades data:\n{trades}")
        #print(f"trades dtypes: {trades.dtypes}")
    except Exception as e:
        print(f"Error reading Excel file: {str(e)}")
        return

    all_results = []
    raw_data_sheets = {}
    trade_logs = {}

    for idx, row in trades.iterrows():
        ticker = row["Ticker"]
        date = pd.to_datetime(row["Date"], format='%Y-%m-%d', errors='coerce')
        if pd.isna(date):
            print(f"Skipping invalid date for Ticker {ticker} at row {idx}: {row['Date']}")
            continue
        date = date.strftime("%Y-%m-%d")
        grade = row["Grade"]
        cap = row["Cap"]
        print(f"\nBacktesting {ticker} on {date} (Grade: {grade}, Cap: {cap})...")

        for interval in intervals:
            print(f" → Processing {ticker}, {date}, {interval}")
            try:
                df = fetch_intraday_bars(ticker, date, interval=interval)
                if df.empty:
                    print(f" → No data for {ticker} on {date} at {interval}")
                    continue

                df_for_backtest = df.copy()
                df_raw = df.copy().reset_index()
                df_raw.rename(columns={df_raw.columns[0]: 'timestamp'}, inplace=True)
                raw_data_sheets[f"{ticker}_{interval}"] = df_raw

                old_stdout = sys.stdout
                sys.stdout = buffer = io.StringIO()
                stats = run_capitulation_short_strategy_with_metrics(df_for_backtest, start_time, end_time)
                trade_log = buffer.getvalue().splitlines()
                sys.stdout = old_stdout
                trade_logs[f"{ticker}_{interval}"] = trade_log

                result = {
                    "Ticker": ticker,
                    "Date": date,
                    "Interval": interval,
                    "P&L": round(stats.get("pnl", 0), 2),
                    "EV": round(stats.get("EV", 0), 2),
                    "Win Rate (%)": round(stats.get("win_rate", 0) / 100, 4),
                    "Avg R/R": round(stats.get("avg_risk_reward", 0), 2),
                    "Total Trades": stats.get("total_trades", 0),
                    "Wins": stats.get("wins", 0),
                    "Losses": stats.get("losses", 0),
                    "Max P&L": round(stats.get("max_pnl", 0), 2),
                    "Min P&L": round(stats.get("min_pnl", 0), 2),
                    "Total % Return": round(stats.get("total_percent_return", 0) / 100, 4),
                    "Avg % Return": round(stats.get("avg_percent_return", 0) / 100, 4),
                    "EV/AVG RISK": round(stats.get("ev_risk", 0), 2),
                }
                all_results.append(result)
                print(f" → Successfully processed {ticker}, {date}, {interval}")
            except Exception as e:
                print(f" → Error processing {ticker}, {date}, {interval}: {str(e)}")
                print(f" → Stack trace: {traceback.format_exc()}")
                continue

    summary_df = pd.DataFrame(all_results).drop_duplicates(subset=["Ticker", "Interval", "Date"])

    summary_df = summary_df.merge(trades[["Ticker", "Date"]], on=["Ticker", "Date"], how="left")
    summary_df['original_index'] = summary_df.apply(lambda row: trades.index[trades['Ticker'] == row['Ticker']][0], axis=1)
    summary_df = summary_df.sort_values(by="original_index").drop(columns=["original_index"])

    interval_summary = summary_df.groupby("Interval").agg({
        "P&L": "sum",
        "EV": "mean",
        "Win Rate (%)": "mean",
        "Avg R/R": "mean",
        "Total % Return": "sum",
        "Avg % Return": "mean",
        "EV/AVG RISK": "mean",
    }).reset_index()

    interval_summary = interval_summary.rename(columns={
        "P&L": "Total P&L",
        "EV": "Avg EV",
        "Win Rate (%)": "Avg Win Rate (%)",
        "Avg R/R": "Avg Risk/Reward",
        "Total % Return": "Total % Return",
        "Avg % Return": "Avg % Return",
        "EV/AVG RISK": "Avg EV/AVG RISK",
    })

    interval_summary["Avg EV"] = interval_summary["Avg EV"].round(2)
    interval_summary["Avg Risk/Reward"] = interval_summary["Avg Risk/Reward"].round(2)
    interval_summary["Avg EV/AVG RISK"] = interval_summary["Avg EV/AVG RISK"].round(2)
    interval_summary["SortKey"] = interval_summary["Interval"].str.extract(r'(\d+)').astype(int)
    interval_summary = interval_summary.sort_values(by="SortKey").drop(columns=["SortKey"])

    pivot_df = summary_df.pivot_table(index="Ticker", columns="Interval", values="EV", aggfunc="mean").reset_index()
    chart_start_row = len(interval_summary) + 5

    with pd.ExcelWriter(output_path, engine="xlsxwriter") as writer:
        workbook = writer.book
        workbook.nan_inf_to_errors = True

        raw_sheet_name = "Raw Data"
        raw_ws = workbook.add_worksheet(raw_sheet_name)
        writer.sheets[raw_sheet_name] = raw_ws

        header_format = workbook.add_format({
            'bold': True, 'align': 'center', 'valign': 'vcenter', 'border': 1, 'bg_color': '#D9D9D9'
        })
        date_format = workbook.add_format({'num_format': 'yyyy-mm-dd hh:mm:ss', 'align': 'center'})
        col_format = workbook.add_format({'align': 'center'})
        start_row = 0

        for sheet_name, df_raw in raw_data_sheets.items():
            ticker, interval = sheet_name.split('_')
            interval_num = interval.replace('min', '')
            date_str = pd.to_datetime(df_raw['timestamp'].iloc[0]).strftime("%Y-%m-%d")
            header_title = f"{ticker} - Interval: {interval_num}min [{date_str}]"

            raw_ws.merge_range(start_row, 0, start_row, len(df_raw.columns)-1, header_title, header_format)
            for col_idx, col_name in enumerate(df_raw.columns):
                raw_ws.write(start_row + 1, col_idx, col_name, header_format)
            for row_idx, (_, row) in enumerate(df_raw.iterrows()):
                for col_idx, col_name in enumerate(df_raw.columns):
                    val = row[col_name]
                    if col_name == 'timestamp':
                        raw_ws.write_datetime(start_row + 2 + row_idx, col_idx, val, date_format)
                    else:
                        raw_ws.write(start_row + 2 + row_idx, col_idx, val, col_format)

            trade_log = trade_logs.get(sheet_name, [])
            trade_log_format = workbook.add_format({'align': 'left'})
            first_data_row = start_row + 2
            for log_idx, log_entry in enumerate(trade_log):
                raw_ws.write(first_data_row + log_idx, 6, log_entry, trade_log_format)

            for col_idx, col_name in enumerate(df_raw.columns):
                max_len = max(df_raw[col_name].astype(str).map(len).max(), len(col_name)) + 2
                if pd.isna(max_len): max_len = 10
                raw_ws.set_column(col_idx, col_idx, max_len)
            max_log_len = max([len(entry) for entry in trade_log] + [10]) if trade_log else 10
            raw_ws.set_column(6, 6, max_log_len)

            start_row += len(df_raw) + 3





        summary_df.to_excel(writer, sheet_name="Trade Results", index=False, startrow=0)
        interval_summary.to_excel(writer, sheet_name="Summary by Interval", index=False)
        pivot_df.to_excel(writer, sheet_name="Summary by Interval", index=False, startrow=chart_start_row)

        summary_ws = writer.sheets["Summary by Interval"]
        results_ws = writer.sheets["Trade Results"]

        """""
        current_row = 1
        prev_ticker = None
        for idx, row in summary_df.iterrows():
            ticker = row["Ticker"]
            if prev_ticker and ticker != prev_ticker:
                current_row += 1
            for col_idx, value in enumerate(row):
                write_value = "" if pd.isna(value) else value
                results_ws.write(current_row, col_idx, write_value)
            current_row += 1
            if idx == len(summary_df) - 1 or summary_df.iloc[idx + 1]["Ticker"] != ticker:
                current_row += 1
            prev_ticker = ticker

        for col_idx, column in enumerate(summary_df.columns):
            results_ws.write(0, col_idx, column)

        for i, column in enumerate(summary_df.columns):
            max_len = max(summary_df[column].astype(str).map(len).max(), len(column)) + 2
            if pd.isna(max_len): max_len = 10
            fmt = None
            if column in ["Win Rate (%)", "Total % Return", "Avg % Return"]:
                fmt = workbook.add_format({'num_format': '0.00%', 'align': 'center'})
            elif column == "EV/AVG RISK":
                fmt = workbook.add_format({'num_format': '0.00', 'align': 'center'})
            results_ws.set_column(i, i, max_len, fmt)

        """""

        current_row = 1
        for _, row in summary_df.iterrows():
            for col_idx, value in enumerate(row):
                write_value = "" if pd.isna(value) else value
                results_ws.write(current_row, col_idx, write_value)
            current_row += 1

        # Write column headers
        for col_idx, column in enumerate(summary_df.columns):
            results_ws.write(0, col_idx, column)

        # Column formatting remains unchanged
        for i, column in enumerate(summary_df.columns):
            max_len = max(summary_df[column].astype(str).map(len).max(), len(column)) + 2
            if pd.isna(max_len): max_len = 10
            fmt = None
            if column in ["Win Rate (%)", "Total % Return", "Avg % Return"]:
                fmt = workbook.add_format({'num_format': '0.00%', 'align': 'center'})
            elif column == "EV/AVG RISK":
                fmt = workbook.add_format({'num_format': '0.00', 'align': 'center'})
            results_ws.set_column(i, i, max_len, fmt)






        for i, column in enumerate(interval_summary.columns):
            col_data = interval_summary[column]
            max_len = max(col_data.astype(str).map(len).max(), len(column)) + 2
            if pd.isna(max_len): max_len = 10
            fmt = None
            if column in ["Avg Win Rate (%)", "Total % Return", "Avg % Return"]:
                fmt = workbook.add_format({'num_format': '0.00%', 'align': 'center'})
            elif column == "Avg EV/AVG RISK":
                fmt = workbook.add_format({'num_format': '0.00', 'align': 'center'})
            summary_ws.set_column(i, i, max_len, fmt)

        number_format = workbook.add_format({'num_format': '0.00', 'align': 'center'})
        for j in range(1, len(pivot_df.columns)):
            max_len = max(pivot_df.iloc[:, j].astype(str).map(len).max(), len(pivot_df.columns[j])) + 2
            if pd.isna(max_len): max_len = 10
            summary_ws.set_column(j, j, max_len, number_format)

        pivot_df_chart = summary_df.pivot_table(index="Ticker", values="EV", columns="Interval", aggfunc="mean")
        pivot_df_chart = pivot_df_chart[sorted(pivot_df_chart.columns, key=lambda x: int(x.replace('min', '')))]
        pivot_df_chart = pivot_df_chart.reset_index()
        pivot_df_chart.to_excel(writer, sheet_name="Summary by Interval", index=False, startrow=chart_start_row)

        chart = workbook.add_chart({'type': 'column'})
        chart.add_series({
            'name': 'Avg EV',
            'categories': ['Summary by Interval', 1, 0, len(interval_summary), 0],
            'values': ['Summary by Interval', 1, 2, len(interval_summary), 2],
            'fill': {'color': '#BFBFBF'},
            'border': {'color': 'black'}
        })
        # Overlay ticker line charts
        for i in range(len(pivot_df)):
            ticker = pivot_df.loc[i, "Ticker"]
            chart.add_series({
                'name':       ticker,
                'categories': ['Summary by Interval', chart_start_row, 1,
                               chart_start_row, len(pivot_df.columns) - 1],
                'values':     ['Summary by Interval', chart_start_row + 1 + i, 1,
                               chart_start_row + 1 + i, len(pivot_df.columns) - 1],
                'type': 'line',
                'marker': {'type': 'circle', 'size': 4}
            })

        chart.set_title({'name': 'Interval vs Avg EV (w/ Ticker Overlay)'})
        chart.set_x_axis({'name': 'Interval', 'label_position': 'low'})
        chart.set_y_axis({'name': 'Expected Value'})
        chart.set_size({'width': 720, 'height': 400})
        summary_ws.insert_chart("J2", chart)


        trades_full = pd.read_excel(excel_path, header=None, names=["Ticker", "Date", "Grade", "Cap"])
        trades_full["Date"] = pd.to_datetime(trades_full["Date"], format='%m/%d/%y', errors='coerce').dt.strftime("%Y-%m-%d")
        trades_full["Cap"] = trades_full["Cap"].str.lower().replace({"medium": "Medium"})
        cap_grade_df = trades_full.merge(summary_df, on=["Ticker", "Date"], how="left")
        cap_grade_df["Grade"] = cap_grade_df["Grade"].fillna("Unknown")
        cap_grade_df["Cap"] = cap_grade_df["Cap"].fillna("Unknown")
        print(f"cap_grade_df:\n{cap_grade_df}")

        grade_summary = cap_grade_df.groupby("Grade").agg({"EV": "mean"}).reset_index()
        grade_summary = grade_summary.rename(columns={"EV": "Avg EV by Grade"})
        cap_summary = cap_grade_df.groupby("Cap").agg({"EV": "mean"}).reset_index()
        cap_summary = cap_summary.rename(columns={"EV": "Avg EV by Cap"})
        print(f"grade_summary:\n{grade_summary}")
        print(f"cap_summary:\n{cap_summary}")

        analysis_ws = workbook.add_worksheet("Cap & Grade Analysis")
        analysis_ws.write(0, 0, "Grade")
        analysis_ws.write(0, 1, "Avg EV by Grade")
        for i, row in grade_summary.iterrows():
            analysis_ws.write(i + 1, 0, row["Grade"])
            analysis_ws.write(i + 1, 1, row["Avg EV by Grade"])
        analysis_ws.write(0, 15, "Cap")
        analysis_ws.write(0, 16, "Avg EV by Cap")
        for i, row in cap_summary.iterrows():
            analysis_ws.write(i + 1, 15, row["Cap"])
            analysis_ws.write(i + 1, 16, row["Avg EV by Cap"])

        for i, column in enumerate(["Grade", "Avg EV by Grade"]):
            max_len = max(grade_summary[column].astype(str).map(len).max(), len(column)) + 2 if not grade_summary.empty else 10
            fmt = workbook.add_format({'num_format': '0.00', 'align': 'center'}) if column == "Avg EV by Grade" else workbook.add_format({'align': 'center'})
            analysis_ws.set_column(i, i, max_len, fmt)
        for i, column in enumerate(["Cap", "Avg EV by Cap"]):
            col_idx = i + 15
            max_len = max(cap_summary[column].astype(str).map(len).max(), len(column)) + 2 if not cap_summary.empty else 10
            fmt = workbook.add_format({'num_format': '0.00', 'align': 'center'}) if column == "Avg EV by Cap" else workbook.add_format({'align': 'center'})
            analysis_ws.set_column(col_idx, col_idx, max_len, fmt)

        if not grade_summary.empty:
            grade_chart = workbook.add_chart({'type': 'column'})
            grade_chart.add_series({
                'name': 'Avg EV by Grade',
                'categories': ['Cap & Grade Analysis', 1, 0, len(grade_summary), 0],
                'values': ['Cap & Grade Analysis', 1, 1, len(grade_summary), 1],
                'fill': {'color': '#BFBFBF'},
                'border': {'color': 'black'}
            })
            grade_chart.set_title({'name': 'Avg EV by Grade Across Companies'})
            grade_chart.set_x_axis({'name': 'Grade', 'label_position': 'low'})
            grade_chart.set_y_axis({'name': 'Avg Expected Value'})
            grade_chart.set_size({'width': 720, 'height': 400})
            analysis_ws.insert_chart('C2', grade_chart)

        if not cap_summary.empty:
            cap_chart = workbook.add_chart({'type': 'column'})
            cap_chart.add_series({
                'name': 'Avg EV by Cap',
                'categories': ['Cap & Grade Analysis', 1, 15, len(cap_summary), 15],
                'values': ['Cap & Grade Analysis', 1, 16, len(cap_summary), 16],
                'fill': {'color': '#BFBFBF'},
                'border': {'color': 'black'}
            })
            cap_chart.set_title({'name': 'Avg EV by Cap Type Across Companies'})
            cap_chart.set_x_axis({'name': 'Cap Type', 'label_position': 'low'})
            cap_chart.set_y_axis({'name': 'Avg Expected Value'})
            cap_chart.set_size({'width': 720, 'height': 400})
            analysis_ws.insert_chart('R2', cap_chart)

    print(f"All done! Results saved to '{output_path}'")