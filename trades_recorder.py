import sys
import os
import csv
import pandas as pd
import gspread
from datetime import datetime

# import scrape_utilities

# from pydrive.auth import GoogleAuth
# from pydrive.auth import ServiceAccountCredentials
# from pydrive.drive import GoogleDrive

from trading_charts_folder_ids import folder_ids

trades_file = sys.argv[1]
print(trades_file)

broker = os.path.basename(trades_file).split('-')[0]
csv_file_date = os.path.basename(trades_file).split(broker + '-')[1].split('.')[0]
csv_file_date = datetime.strptime(csv_file_date, '%m-%d-%y')

# TODO: parse by cobra or etrade csv and make csv column name variables accordingly

# Setup Google Sheets Connection
gc = gspread.service_account()
sh = gc.open("Trades")
# Params
worksheet = sh.worksheet("Trades")
# worksheet = sh.worksheet("TradesTest") # testcase

# Get all values from the worksheet and store in a dictionary and search for data that way. This reduces the amount
# of API calls since there is a limit of 300 requests per minute per project and 60 requests per minute per user
gspread_all_values_dict = worksheet.get_all_records()

# Current Spreadsheet Info
#   Date
#   Ticker
#   Strategy
#   Feeling	Confidence(1-10)
#   Frustration(1-10)
#   Notes
#   News Day After
#   Dilution Risk
#   Run Reason
#   Try No.	Adds
#   Risk
#   Side
#   Entry Shares
#   Exit Shares
#   Reward
#   RR
#   Avg Entry
#   Price
#   Avg Exit Price
#   First Entry Time
#   Last Entry Time
#   Ideal Entry Time
#   Ideal Entry Price
#   First Exit Time
#   Last Exit Time
#   Ideal Exit Time
#   Ideal Exit Price
#   $ Volume
#   Max 3 Year $ Volume
#   % Gain/Loss
#   $ Gain
#   Float
#   Market Cap
#   Sector

# TODO: this will probably be an etrade specific variable
# csv_file_date = datetime.today()

# Read csv file into pandas dataframe
print(os.path.abspath(os.getcwd()))

if broker == 'etrade':
    df = pd.DataFrame(columns=["Date", "Time", "Side", "Qty", "Symb", "Price"])

    with open(trades_file, "r") as f:
        # reader = csv.reader(f, delimiter="\t")
        reader = csv.reader(f)
        for i, line in enumerate(reader):
            # line list
            ll = line[0].replace('\t\t', ',').replace(' ', ',').split(",")
            # don't read cancelled or pending entries
            if ll[7] != 'Executed':
                continue
            # join time and AM/PM
            ll[1:3] = [' '.join(ll[1:3])]
            # remove tabs from copy and pasted line
            ll[0] = ll[0].replace('\t', '')
            # remove the dollar sign and tabs
            ll[8] = ll[8].replace('$', '').replace('\t', '')
            #df_list[0] -> Date
            #df_list[1] -> Time
            #df_list[2] -> Type
            #df_list[3] -> Qty
            #df_list[4] -> Symb
            #df_list[5] -> Price
            df_list = [ll[0], ll[1], ll[3], int(ll[4]), ll[5], float(ll[8])]
            df.loc[len(df)] = df_list

elif broker == 'cobra':
    df = pd.read_csv(trades_file)
else:
    print("wrong csv file name format")
    sys.exit()

# Grab share sum for tickers
df_share_sum = df.groupby(['Symb', 'Side'])['Qty'].sum()
# Group by symbol and time
df = df.sort_values(['Symb', 'Time'])
# Add dollar value to each entry/exit
df['dollar_val'] = df['Price'] * df['Qty']
# print(df.to_string())
# Get first and last time of both the entry and the exit
df_time_min = df.groupby(['Symb', 'Side'])['Time'].min()
df_time_max = df.groupby(['Symb', 'Side'])['Time'].max()
# Get dollar value sum
df_dollar_sum = df.groupby(['Symb', 'Side'])['dollar_val'].sum()
# Get weight
# TODO: the df_weight and df_share_sum are the same data frames right now, but once we do something with the group by time, the two may be different
df_weight = df.groupby(['Symb', 'Side'])['Qty'].sum()

print("first trade executions")
print(df_time_min.to_string())
print("last trade executions")
print(df_time_max.to_string())
print("Dollar Sum")
print(df_dollar_sum.to_string())
print("Weight")
print(df_weight.to_string())
# Compute Average Price
df_avg_prices = df_dollar_sum / df_weight
print("Avgerage Pricing")
print(df_avg_prices.to_string())

# Find first exit shares cell that doesn't equal entry shares cell
for idx, gspread_entries in enumerate(gspread_all_values_dict):
    if gspread_entries['Entry Shares'] != gspread_entries['Exit Shares'] or gspread_entries['Entry Shares'] == "":

        # Grab ticker and ticker's side from spreadsheet
        ticker = gspread_entries['Ticker']
        gspread_ticker_trade_side = gspread_entries['Side']
        if gspread_ticker_trade_side == "":
            print("The trade side is unknown in gspread. Fill out this cell to continue")
            continue

        # Grab the Date of the stocks that we will compute the average entry price for
        trade_date = datetime.strptime(gspread_entries['Date'], '%m/%d/%Y')

        # TODO: this logic isn't correct. Need to verify the time of which the side started and compare to the other side start time
        # Right now we are just recording the trade side manually
        # # Get Side of the trade from the csv data for the given ticker
        # csv_ticker_trade_side = df_share_sum[ticker].keys().values[0]
        # if gspread_ticker_trade_side == "":
        #     gspread_ticker_trade_side = csv_ticker_trade_side

        # TODO: reevaluate average pricing for adds on different days (low priority)
        # ticker_entry_shares = gspread_all_values_dict[idx]['Entry Shares']
        # ticker_avg_entry_price = gspread_all_values_dict[idx]['Avg Entry Price']
        # ticker_exit_shares = gspread_all_values_dict[idx]['Exit Shares']
        # ticker_avg_exit_price = gspread_all_values_dict[idx]['Avg Exit Price']
        ticker_entry_shares = gspread_all_values_dict[idx]['Entry Shares']
        ticker_avg_entry_price = gspread_all_values_dict[idx]['Avg Entry Price']
        ticker_exit_shares = gspread_all_values_dict[idx]['Avg Exit Price']
        ticker_avg_exit_price = gspread_all_values_dict[idx]['Avg Exit Price']

        # If ticker doesn't exist in the share sum data frame, it may just be in another csv file so skip to the next ticker.
        # If the csv file date doesn't match the gspread trade date and the gspread trade date's entry price is none, continue
        # because that's a different trade.
        if df_share_sum.get(ticker) is None or \
                ((trade_date != csv_file_date) and not ticker_entry_shares):
            continue

        for val in df_share_sum[ticker].items():
            if val[0] == gspread_ticker_trade_side:
                # Get ticker's entry shares if the side equals the entry side
                ticker_entry_shares += val[1]
                ticker_avg_entry_price = df_avg_prices[ticker][val[0]]
            else:
                # Get ticker's exit shares if the side is opposite the entry side
                ticker_exit_shares = val[1]
                ticker_avg_exit_price += df_avg_prices[ticker][val[0]]

        # Place average entry and exit, entry and exit shares back in gspread_all_values_dict at the current idx
        gspread_all_values_dict[idx]['Entry Shares'] = ticker_entry_shares
        gspread_all_values_dict[idx]['Avg Entry Price'] = ticker_avg_entry_price
        gspread_all_values_dict[idx]['Exit Shares'] = ticker_exit_shares
        gspread_all_values_dict[idx]['Avg Exit Price'] = ticker_avg_exit_price

# publish updated worksheet
df = pd.DataFrame(gspread_all_values_dict)
# remove columns that have google sheets formulas so we don't overwrite them
df = df.drop(columns=['% Gain/Loss', '$ Gain', 'RR'])
worksheet.update([df.columns.values.tolist()] + df.values.tolist())

# Ideal Entry Prices and Times #
#   1. DD1: Track the high after 10:30am for that day
#   2. OEGD: Track the high before 10:30am for that day
#   3. Multi Day Breakout: After breakout price was hit, track low starting at breakout time and before the high of day
#   4. Below Vwap Afternoon Fade: Manually record when it drops to or below vwap. Then track the high after
#   5. Afternoon Breakout FGD: After breakout price was hit after 1pm, track low starting at breakout time and before high of day
#   6. FailSpike below Vwap Consolidate: After under Vwap for one hour, track high

# Ideal Exit Prices and Times #
#   1. DD1: Track the low after 10:30am between that day and next
#   2. OEGD: Track the low for that day
#   3. Multi Day Breakout: After breakout price was hit, track high starting at breakout time for that day
#   4. Below Vwap Afternoon Fade: Manually record when it drops to or below vwap. Track the low after until next day
#   5. Afternoon Breakout FGD: After breakout price was hit after 1pm, track low starting at breakout time for that day
#   6. FailSpike below Vwap Consolidate: After under Vwap for one hour, track low after until next day


# TODO:
# Focus on dd1 entry and exit price and time
# 1. Finish typing out plan for Avg Entry and Exit Prices
# 2. Make RR formula in google sheets depending on whether you longed or shorted

# Grabbing csv data:
#   * Search for first column where entry shares don't equal exit shares
#   * If exit shares are greater than entry shares, start a new trade column
#   * From that row, match csv ticker with google sheets ticker
#   * If googlesheets ticker doesn't exist after going to last row, make new row with 'B' or 'SS'.
#   * Add share amount
#   * Return Error if type is 'S' for new row
#   * If you found an existing row, make sure the csv type is opposite the side. Otherwise, return error
#   * If you are starting on a new row, you can Grab the following from the csv file:
#       a. First Entry Time
#       b. Last Entry Time
#   * If you are starting on a new row, you can Compute the following from the csv file:
#       a. Avg Entry Price
#   * If you are starting on a new row, you can compute the following from polygon.io:
#       a. Ideal Entry Time
#       b. Ideal Entry Price
#   Question: What if you are short and long within same period?
