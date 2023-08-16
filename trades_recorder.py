import sys
import os
import csv
import pandas as pd
import gspread
from datetime import datetime
import re

# import scrape_utilities
import file_utilities
import hloc_utilities
from trading_charts_folder_ids import folder_ids

trades_file = sys.argv[1]
print(trades_file)

# grab broker type and file date from csv file name
broker = file_utilities.get_broker(trades_file)
csv_file_date = file_utilities.get_date(trades_file)

time_fmt = '%H:%M:%S'
if 'etrade' == broker:
    time_fmt = '%H:%M'

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
#   % Open Gain
gspread_last_raw_value_column = '% Open Gain'

# TODO: this will probably be an etrade specific variable if we are grabbing from the etrade website trade document
# csv_file_date = datetime.today()

# Read csv file into pandas dataframe
csv_df = file_utilities.trades_csv_to_df(trades_file)

# Group by symbol and time
csv_df = csv_df.sort_values(['Symb', 'Time'])
# Add dollar value to each entry/exit
csv_df['dollar_val'] = csv_df['Price'] * csv_df['Qty']
# print(csv_df.to_string())
# Get first and last time of both the entry and the exit
csv_df_time_min = csv_df.groupby(['Symb', 'Side'])['Time'].min()
csv_df_time_max = csv_df.groupby(['Symb', 'Side'])['Time'].max()
# Get dollar value sum
csv_df_dollar_sum = csv_df.groupby(['Symb', 'Side'])['dollar_val'].sum()
# Grab share sum for tickers (weight)
csv_df_share_sum = csv_df.groupby(['Symb', 'Side'])['Qty'].sum()
csv_df_weight = csv_df.groupby(['Symb', 'Side'])['Qty'].sum()

print("first trade executions")
print(csv_df_time_min.to_string())
print("last trade executions")
print(csv_df_time_max.to_string())
# Compute Average Price from csv file
csv_df_avg_prices = csv_df_dollar_sum / csv_df_share_sum
print("Average Pricing")
print(csv_df_avg_prices.to_string())

# TODO: the start of recognizing different trades from the same ticker. More logic than what its
#for symb in csv_df.Symb.unique():
#    if csv_df.loc([symb == ''])
#    print(symb)


# Find first exit shares cell that doesn't equal entry shares cell
for idx, gspread_entries in enumerate(gspread_all_values_dict):
    if gspread_entries['Entry Shares'] != gspread_entries['Exit Shares'] or gspread_entries['Entry Shares'] == "":

        # Grab ticker and ticker's side from spreadsheet
        ticker = gspread_entries['Ticker']
        gspread_ticker_trade_side = gspread_entries['Side']
        if gspread_ticker_trade_side == "":
            print("The trade side for " + ticker + "at " + gspread_entries['Date'] + " is unknown in gspread. Fill out this cell to continue")
            continue

        # Grab the Date of the stocks that we will compute the average entry price for
        trade_date = datetime.strptime(gspread_entries['Date'], '%m/%d/%Y')

        # TODO: this logic isn't correct. Need to verify the time of which the side started and compare to the other side start time
        # Right now we are just recording the trade side manually
        # # Get Side of the trade from the csv data for the given ticker
        # csv_ticker_trade_side = csv_df_share_sum[ticker].keys().values[0]
        # if gspread_ticker_trade_side == "":
        #     gspread_ticker_trade_side = csv_ticker_trade_side

        # TODO: reevaluate average pricing for adds on different days (low priority)
        ticker_entry_shares = gspread_all_values_dict[idx]['Entry Shares']
        ticker_avg_entry_price = gspread_all_values_dict[idx]['Avg Entry Price']
        ticker_exit_shares = gspread_all_values_dict[idx]['Exit Shares']
        ticker_avg_exit_price = gspread_all_values_dict[idx]['Avg Exit Price']
        ticker_first_entry_datetime = gspread_all_values_dict[idx]['First Entry Time']
        ticker_last_entry_datetime = gspread_all_values_dict[idx]['Last Entry Time']
        ticker_first_exit_datetime = gspread_all_values_dict[idx]['First Exit Time']
        ticker_last_exit_datetime = gspread_all_values_dict[idx]['Last Exit Time']

        # If ticker doesn't exist in the share sum data frame, it may just be in another csv file so skip to the next ticker.
        # If the csv file date doesn't match the gspread trade date and the gspread trade date's entry price is none, continue
        # because that's a different trade.
        if csv_df_share_sum.get(ticker) is None or \
                ((trade_date != csv_file_date) and not ticker_entry_shares):
            continue

        for val in csv_df_share_sum[ticker].items():
            if val[0] == gspread_ticker_trade_side:
                # change ticker_entry_shares to int if we haven't filled it out yet
                if ticker_entry_shares == '':
                    ticker_entry_shares = 0
                # Get ticker's entry shares if the side equals the entry side
                ticker_entry_shares += val[1]
                ticker_avg_entry_price = csv_df_avg_prices[ticker][val[0]]
                # assign first and last entry times
                if ticker_first_entry_datetime == '':
                    first_entry_time = datetime.strptime(csv_df_time_min[ticker][val[0]], time_fmt)
                    ticker_first_entry_datetime = datetime.combine(trade_date, first_entry_time.time())
                last_entry_time = datetime.strptime(csv_df_time_max[ticker][val[0]], time_fmt)
                ticker_last_entry_datetime = datetime.combine(trade_date, last_entry_time.time())
            else:
                # change ticker_exit_shares to int if we haven't filled it out yet
                if ticker_exit_shares == '':
                    ticker_exit_shares = 0
                # Get ticker's exit shares if the side is opposite the entry side
                ticker_exit_shares += val[1]
                ticker_avg_exit_price = csv_df_avg_prices[ticker][val[0]]
                # assign first and last exit times
                if ticker_first_exit_datetime == '':
                    first_exit_time = datetime.strptime(csv_df_time_min[ticker][val[0]], time_fmt)
                    ticker_first_exit_datetime = datetime.combine(trade_date, first_exit_time.time())
                last_exit_time = datetime.strptime(csv_df_time_max[ticker][val[0]], time_fmt)
                ticker_last_exit_datetime = datetime.combine(trade_date, last_exit_time.time())


        #TODO: start of polygon logic
        #df = hloc_utilities.get_intraday_ticks(ticker, trade_date)


        # Place average entry and exit, entry and exit shares, and times back in gspread_all_values_dict at the current idx
        gspread_all_values_dict[idx]['Entry Shares'] = ticker_entry_shares
        gspread_all_values_dict[idx]['Avg Entry Price'] = ticker_avg_entry_price
        gspread_all_values_dict[idx]['Exit Shares'] = ticker_exit_shares
        gspread_all_values_dict[idx]['Avg Exit Price'] = ticker_avg_exit_price
        gspread_all_values_dict[idx]['First Entry Time'] = str(ticker_first_entry_datetime)
        gspread_all_values_dict[idx]['Last Entry Time'] = str(ticker_last_entry_datetime)
        gspread_all_values_dict[idx]['First Exit Time'] = str(ticker_first_exit_datetime)
        gspread_all_values_dict[idx]['Last Exit Time'] = str(ticker_last_exit_datetime)

        # Ideal Entry Prices and Times #
        #   1. dd1: Track the high after 10:30am for that day
        #   2. oegd: Track the high before 10:30am for that day
        #   3. md bo: After breakout price was hit, track low starting at breakout time and before the high of day
        #   4. vwap tank: Manually record when it drops to or below vwap. Then track the high after
        #   5. aft bo: After breakout price was hit after 1pm, track low starting at breakout time and before high of day
        #   6. FailSpike below Vwap Consolidate: After under Vwap for one hour, track high

        # Ideal Exit Prices and Times #
        #   1. dd1: Track the low after 10:30am between that day and next
        #   2. oegd: Track the low for that day
        #   3. md bo: After breakout price was hit, track high starting at breakout time for that day
        #   4. vwap tank: Manually record when it drops to or below vwap. Track the low after until next day
        #   5. aft bo: After breakout price was hit after 1pm, track low starting at breakout time for that day
        #   6. FailSpike below Vwap Consolidate: After under Vwap for one hour, track low after until next day

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


# publish updated worksheet
gspread_df = pd.DataFrame(gspread_all_values_dict)
# remove columns that have google sheets formulas so we don't overwrite them
gspread_df = gspread_df.loc[:,:gspread_last_raw_value_column]
worksheet.update([gspread_df.columns.values.tolist()] + gspread_df.values.tolist())
