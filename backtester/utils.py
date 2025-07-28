def resample_to_interval(df, minutes):
    return df.resample(f"{minutes}min").agg({
        "open": "first",
        "high": "max",
        "low": "min",
        "close": "last",
        "volume": "sum"
    }).dropna()