import sys
import os
import csv
import pandas as pd
import gspread
from datetime import datetime
import re
from configparser import ConfigParser

# import scrape_utilities
import util
from trading_charts_folder_ids import folder_ids

trades_file = sys.argv[1]
print(trades_file)

config_object = ConfigParser()
config_object.read("config/config.ini")

# grab broker type and file date from csv file name
broker = util.get_broker(trades_file)
csv_file_date = util.get_date(trades_file)

time_fmt = '%H:%M:%S'
if 'etrade' == broker:
    time_fmt = '%H:%M'


worksheet = util.get_gspread_worksheet(config_object['main']['GSPREAD_WORKSHEET'])

gspread_all_values_dict = util.get_gspread_worksheet_values(worksheet)

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
csv_df = util.trades_csv_to_df(trades_file)

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
# for symb in csv_df.Symb.unique():
#    if csv_df.loc([symb == ''])
#    print(symb)


# Find first exit shares cell that doesn't equal entry shares cell
for idx, gspread_entries in enumerate(gspread_all_values_dict):
    if gspread_entries['Entry Shares'] != gspread_entries['Exit Shares'] or gspread_entries['Entry Shares'] == "":

        # Grab the Date of the stocks that we will compute the average entry price for
        gspread_trade_date = datetime.strptime(gspread_entries['Date'], '%m/%d/%Y')

        # Grab ticker and ticker's side from spreadsheet
        ticker = gspread_entries['Ticker']
        if gspread_all_values_dict[idx]['Side'] == "" and gspread_trade_date == csv_file_date:
            if broker == 'cobra':
                gspread_all_values_dict[idx]['Side'] = 'SS'
            elif broker == 'etrade':
                gspread_all_values_dict[idx]['Side'] = 'B'
            else:
                print("Broker unknown. Skipping trade")
                continue

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
                ((gspread_trade_date != csv_file_date) and not ticker_entry_shares):
            continue

        for val in csv_df_share_sum[ticker].items():
            if val[0] == gspread_all_values_dict[idx]['Side']:
                # change ticker_entry_shares and ticker_avg_entry_price to int if we haven't filled it out yet
                if ticker_entry_shares == '':
                    ticker_entry_shares = 0
                if ticker_avg_entry_price == '':
                    ticker_avg_entry_price = 0

                # if there is already an entry price and we are adding to the position, need to re-evaluate avg price
                prev_ticker_entry_shares = ticker_entry_shares
                prev_avg_entry_price = ticker_avg_entry_price

                current_day_entry_shares = val[1]
                current_day_avg_entry_price = csv_df_avg_prices[ticker][val[0]]

                # Get ticker's total entry shares
                ticker_entry_shares += current_day_entry_shares
                # Get the weighted entry incase there was already an average entry price
                ticker_avg_entry_price = ((prev_ticker_entry_shares * prev_avg_entry_price) + (
                        current_day_entry_shares * current_day_avg_entry_price)) / \
                                         ticker_entry_shares
                # assign first and last entry times
                if ticker_first_entry_datetime == '':
                    first_entry_time = datetime.strptime(csv_df_time_min[ticker][val[0]], time_fmt)
                    ticker_first_entry_datetime = datetime.combine(gspread_trade_date, first_entry_time.time())
                last_entry_time = datetime.strptime(csv_df_time_max[ticker][val[0]], time_fmt)
                ticker_last_entry_datetime = datetime.combine(gspread_trade_date, last_entry_time.time())
            else:
                # change ticker_exit_shares and ticker_avg_exit_price to int if we haven't filled it out yet
                if ticker_exit_shares == '':
                    ticker_exit_shares = 0
                if ticker_avg_exit_price == '':
                    ticker_avg_exit_price = 0

                # if there is already an entry price and we are adding to the position, need to re-evaluate avg price
                prev_ticker_exit_shares = ticker_exit_shares
                prev_avg_exit_price = ticker_avg_exit_price

                current_day_exit_shares = val[1]
                current_day_avg_exit_price = csv_df_avg_prices[ticker][val[0]]

                # Get ticker's total exit shares
                ticker_exit_shares += current_day_exit_shares
                ticker_avg_exit_price = ((prev_ticker_exit_shares * prev_avg_exit_price) + (
                        current_day_exit_shares * current_day_avg_exit_price)) / \
                                        ticker_exit_shares
                # assign first and last exit times
                # The exit date should be grabbed from the csv_file_date so those that are held overnight
                if ticker_first_exit_datetime == '':
                    first_exit_time = datetime.strptime(csv_df_time_min[ticker][val[0]], time_fmt)
                    ticker_first_exit_datetime = datetime.combine(csv_file_date, first_exit_time.time())
                last_exit_time = datetime.strptime(csv_df_time_max[ticker][val[0]], time_fmt)
                ticker_last_exit_datetime = datetime.combine(csv_file_date, last_exit_time.time())

        # Place average entry and exit, entry and exit shares, and times back in gspread_all_values_dict at the current idx
        gspread_all_values_dict[idx]['Entry Shares'] = ticker_entry_shares
        gspread_all_values_dict[idx]['Avg Entry Price'] = ticker_avg_entry_price
        gspread_all_values_dict[idx]['Exit Shares'] = ticker_exit_shares
        gspread_all_values_dict[idx]['Avg Exit Price'] = ticker_avg_exit_price
        gspread_all_values_dict[idx]['First Entry Time'] = str(ticker_first_entry_datetime)
        gspread_all_values_dict[idx]['Last Entry Time'] = str(ticker_last_entry_datetime)
        gspread_all_values_dict[idx]['First Exit Time'] = str(ticker_first_exit_datetime)
        gspread_all_values_dict[idx]['Last Exit Time'] = str(ticker_last_exit_datetime)
        gspread_all_values_dict[idx]['Broker'] = broker

        # Ideal Entry Prices and Times #
        # Ideal entry prices and times can be computed after market close
        # Ideal exit times can also be computed after market close except for dd1 and aft bo strategies. These will
        # be computed after next day's market close

        # Grabbing csv data:
        # Question: What if you are short and long within same period?

# publish updated worksheet
gspread_df = pd.DataFrame(gspread_all_values_dict)
# remove columns that have google sheets formulas so we don't overwrite them
gspread_df = gspread_df.loc[:, :gspread_last_raw_value_column]
worksheet.update([gspread_df.columns.values.tolist()] + gspread_df.values.tolist())
