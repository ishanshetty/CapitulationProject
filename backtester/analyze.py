import pandas as pd

def run_capitulation_short_strategy_with_metrics(df, start_time="09:30", end_time="16:00"):
    position = None
    entry_price = None
    stop_price = None
    high_of_day = float('-inf')
    total_pnl = 0.0
    total_percent_return = 0.0
    wins = 0
    losses = 0
    risk_reward_ratios = []
    individual_pnls = []
    percent_returns = []
    win_pnls = []
    loss_pnls = []
    num_trades = 0
    ev_risk_ratios = []
    unitsRisked = 0

    df_filtered = df.between_time("04:00", "20:00")
    times = df_filtered.index
    
    #just added
    high_of_day = -float('inf')
    capitulation_occurred = False                          
    #just added

    for i in range(1, len(times)):
        curr_time = times[i]
        prev = df_filtered.loc[times[i - 1]]
        curr = df_filtered.loc[times[i]]

        high_of_day = max(high_of_day, curr["high"])
        current_time = curr_time.time()
        start_t = pd.to_datetime(start_time).time()
        end_t = pd.to_datetime(end_time).time()


        if position is None and not (start_t <= current_time <= end_t):
            continue

        ### [ADDED] -- Stop scanning for new trades after capitulation
        if position is None and capitulation_occurred:
            continue

        if position is None:
            if curr["low"] < prev["low"]:
                entry_price = prev["low"]
                stop_price = high_of_day
                position = "short"
                num_trades += 1
                print(f"[{curr_time}] ENTER SHORT @ {entry_price:.2f} | Initial Stop: {stop_price:.2f}")

        elif position == "short":
            trailing_stop = prev["high"]
            if trailing_stop < stop_price:
                print(f"[{curr_time}] TRAIL STOP adjusted: {stop_price:.2f} → {trailing_stop:.2f}")
                stop_price = trailing_stop

            if curr["high"] >= stop_price:
                exit_price = stop_price
                pnl = entry_price - exit_price
                percent_return = (pnl / entry_price) * 100
                risk = high_of_day - entry_price
                reward = entry_price - exit_price
                #rr_ratio = risk / reward if reward != 0 else float('inf')
                rr_ratio = reward / risk if risk > 0 else 0
                unitsRisked += risk


                print(f"[{curr_time}] EXIT SHORT @ {exit_price:.2f}")
                print(f"P&L: {pnl:.2f} | % Return: {percent_return:.2f}% | Risk: {risk:.2f} | Reward: {reward:.2f} | R/R: {rr_ratio:.2f}\n")

                total_pnl += pnl
                total_percent_return += percent_return
                individual_pnls.append(pnl)
                percent_returns.append(percent_return)

                if pnl > 0:
                    win_pnls.append(pnl)
                    wins += 1
                else:
                    loss_pnls.append(pnl)
                    losses += 1

                risk_reward_ratios.append(rr_ratio)
                position = None

                # NEW: Check if move from high of day to exit was ≥10%
                drop_from_high = (high_of_day - exit_price) / high_of_day
                if drop_from_high >= 0.10:
                    capitulation_occurred = True

    if position == "short":
        final_close = df_filtered.iloc[-1]["close"]
        pnl = entry_price - final_close
        percent_return = (pnl / entry_price) * 100
        risk = max(stop_price - entry_price, 0.01)
        reward = abs(entry_price - final_close)
        #rr_ratio = risk / reward if reward != 0 else float('inf')
        rr_ratio = reward / risk if risk > 0 else 0
        unitsRisked += risk


        #print(f"[{df_filtered.index[-1]}] EOD EXIT SHORT @ {final_close:.2f}")
        #print(f"P&L: {pnl:.2f} | % Return: {percent_return:.2f}% | Risk: {risk:.2f} | Reward: {reward:.2f} | R/R: {rr_ratio:.2f}\n")

        total_pnl += pnl
        total_percent_return += percent_return
        individual_pnls.append(pnl)
        percent_returns.append(percent_return)

        if pnl > 0:
            win_pnls.append(pnl)
            wins += 1
        else:
            loss_pnls.append(pnl)
            losses += 1

        risk_reward_ratios.append(rr_ratio)

    win_rate = wins / num_trades if num_trades > 0 else 0
    loss_rate = losses / num_trades if num_trades > 0 else 0
    avg_win = sum(win_pnls) / len(win_pnls) if win_pnls else 0
    avg_loss = sum(loss_pnls) / len(loss_pnls) if loss_pnls else 0
    expected_value = (win_rate * avg_win) + (loss_rate * avg_loss)
    
    #TESTED
    avgRisk = unitsRisked / num_trades if num_trades > 0 else 0

    avg_rr = sum(risk_reward_ratios) / len(risk_reward_ratios) if risk_reward_ratios else 0
    max_pnl = max(individual_pnls) if individual_pnls else 0
    min_pnl = min(individual_pnls) if individual_pnls else 0
    avg_percent_return = sum(percent_returns) / len(percent_returns) if percent_returns else 0

    ev_risk = expected_value / unitsRisked if unitsRisked else 0

    return {
        "pnl": round(total_pnl, 2),
        "EV": round(expected_value, 2),
        "win_rate": round(win_rate * 100, 2),
        "avg_risk_reward": round(avg_rr, 2),
        "total_trades": num_trades,
        "wins": wins,
        "losses": losses,
        "max_pnl": round(max_pnl, 2),
        "min_pnl": round(min_pnl, 2),
        "total_percent_return": round(total_percent_return, 2),
        "avg_percent_return": round(avg_percent_return, 2),
        "ev_risk": round(ev_risk, 4)
    }