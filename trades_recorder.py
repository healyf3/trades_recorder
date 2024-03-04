import sys
import os
import csv
import pandas as pd
import gspread
from datetime import datetime
from datetime import timedelta
import re
from configparser import ConfigParser

import util
import hloc_utilities
from trading_charts_folder_ids import folder_ids
from graph_stock import graph_stock

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

worksheet = util.get_gspread_worksheet(config_object['main']['GSPREAD_SPREADSHEET'],
                                       config_object['main']['GSPREAD_TRADES_WORKSHEET'])
worksheet_test = util.get_gspread_worksheet(config_object['main']['GSPREAD_SPREADSHEET'], 'ttest')

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
gspread_first_auto_entry_column = 'Broker'
gspread_first_hloc_column = '$ Volume'

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


for idx, gspread_entries in enumerate(gspread_all_values_dict):

    ticker = gspread_entries['Ticker']
    # Grab the Date of the stocks that we will compute the average entry price for
    gspread_trade_date = datetime.strptime(gspread_entries['Date'], '%m/%d/%Y')
    strategy = gspread_entries['Strategy']

    # Find first exit shares cell that doesn't equal entry shares cell
    if gspread_entries['Entry Shares'] != gspread_entries['Exit Shares'] or gspread_entries['Entry Shares'] == "":

        # Get fundamental data
        float = gspread_all_values_dict[idx]['Float']
        mkt_cap = gspread_all_values_dict[idx]['Market Cap']
        sector = gspread_all_values_dict[idx]['Sector']
        industry = gspread_all_values_dict[idx]['Industry']
        exchange = gspread_all_values_dict[idx]['Exchange']
        fundamentals_dict = dict()
        update_fundamentals = False

        curr_date_trade_date_delta = datetime.today().date() - gspread_trade_date.date()
        # want to fundamental info somewhat accurate so don't record it if 5 days have passed
        if curr_date_trade_date_delta < timedelta(days=5) and (
                float == '' or mkt_cap == '' or sector == '' or industry == '' or exchange == ''):
            fundamentals_dict = util.grab_finviz_fundamentals(gspread_entries['Ticker'])
            update_fundamentals = True

        # update fundamentals if need be regardless of appropriate hloc recording
        if update_fundamentals:
            gspread_all_values_dict[idx]['Float'] = fundamentals_dict['Float']
            gspread_all_values_dict[idx]['Market Cap'] = fundamentals_dict['Market Cap']
            gspread_all_values_dict[idx]['Sector'] = fundamentals_dict['Sector']
            gspread_all_values_dict[idx]['Industry'] = fundamentals_dict['Industry']
            gspread_all_values_dict[idx]['Exchange'] = fundamentals_dict['Exchange']

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

        # Grab current graph data. We may be adding more links
        graphs = gspread_entries['Charts']

        # Grab ticker and ticker's side from spreadsheet
        if gspread_all_values_dict[idx]['Side'] == "":
            if broker == 'cobra':
                gspread_all_values_dict[idx]['Side'] = 'SS'
            elif broker == 'etrade':
                gspread_all_values_dict[idx]['Side'] = 'B'
            else:
                print("Broker unknown. Skipping trade")
                continue

        csv_file_buys = csv_df.loc[(csv_df['Side'] == 'B') & (csv_df['Symb'] == ticker)].values.tolist()
        csv_file_sells = csv_df.loc[
            ((csv_df['Side'] == 'S') | (csv_df['Side'] == 'SS')) & (csv_df['Symb'] == ticker)].values.tolist()

        # update buys and sells list to be universally indexed between brokers
        parsed_buys = []
        parsed_sells = []
        if gspread_entries['Buys'] != "":
            parsed_buys = eval(gspread_entries['Buys'])
        if gspread_entries['Sells'] != "":
            parsed_sells = eval(gspread_entries['Sells'])
        if broker == 'cobra':
            for i, x in enumerate(csv_file_buys):
                parsed_buys.append({'date': csv_file_date.strftime("%m/%d/%y"),
                                    'time': x[0][:-3], # don't include seconds
                                    'price': x[3]
                                    })

            for i, x in enumerate(csv_file_sells):
                parsed_sells.append({'date': csv_file_date.strftime("%m/%d/%y"),
                                    'time': x[0][:-3], # don't include seconds
                                    'price': x[3]
                                    })
        if broker == 'etrade':
            for i, x in enumerate(csv_file_buys):
                parsed_buys.append({'date': x[0],
                                    'time': x[1],
                                    'price': x[5]
                                    })
            for i, x in enumerate(csv_file_sells):
                parsed_sells.append({'date': x[0],
                                    'time': x[1],
                                    'price': x[5]
                                    })

        # TODO: (This may not be needed): Avoid duplicate entries and exits
        #if str(parsed_buys) not in gspread_entries['Buys'] and gspread_entries['Buys'] != "":
        #    parsed_buys.insert(0, eval(gspread_entries['Buys'])[0])
        #if str(parsed_sells) not in gspread_entries['Sells'] and gspread_entries['Sells'] != "":
        #    parsed_sells.insert(0, eval(gspread_entries['Sells'])[0])

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

                # TODO: grab float info
                # float_sector_info_dict = util.get_float_sector_info(ticker)

                ## I'm rounding the market cap with the afternoon high for now
                # if float_sector_info_dict['shares outstanding'] != 'N/A':
                #    data_dict['mktCap'] = data_dict['afternoon_high'] * float_sector_info_dict['shares outstanding']
                # else:
                #    data_dict['mktCap'] = 'N/A'
                # data_dict['float'] = float_sector_info_dict['float']
                # data_dict['short interest'] = float_sector_info_dict['short interest']
                # data_dict['sector'] = float_sector_info_dict['sector']
                # data_dict['industry'] = float_sector_info_dict['industry']

                # data_dict['google_chart_link'] = gfile.get('alternateLink')

        worksheet_test = util.get_gspread_worksheet(config_object['main']['GSPREAD_SPREADSHEET'], 'ttest')
        # if ticker_avg_exit_price != "": # just graph the stock if the trade is finished
        graphs = graph_stock(ticker, gspread_trade_date, csv_file_date, strategy, ticker_entry_shares, parsed_buys, parsed_sells,
                                 risk=gspread_entries['Risk Price'], avg_entry=ticker_avg_entry_price,
                                 avg_exit=ticker_avg_exit_price, entry_time=ticker_first_entry_datetime,
                                 exit_time=ticker_last_exit_datetime, trade_side=gspread_all_values_dict[idx]['Side'],
                                 right=gspread_entries['Right'], wrong=gspread_entries['Wrong'],
                                 cont=gspread_entries['Continue'], notes=gspread_entries['Notes']) + "\n"

        # Place average entry and exit, entry and exit shares, and times back in gspread_all_values_dict at the current idx
        gspread_all_values_dict[idx]['Entry Shares'] = ticker_entry_shares
        gspread_all_values_dict[idx]['Avg Entry Price'] = ticker_avg_entry_price
        gspread_all_values_dict[idx]['Exit Shares'] = ticker_exit_shares
        gspread_all_values_dict[idx]['Buys'] = str(parsed_buys) if parsed_buys else ""
        gspread_all_values_dict[idx]['Sells'] = str(parsed_sells) if parsed_sells else ""
        gspread_all_values_dict[idx]['Avg Exit Price'] = ticker_avg_exit_price
        gspread_all_values_dict[idx]['First Entry Time'] = str(ticker_first_entry_datetime)
        gspread_all_values_dict[idx]['Last Entry Time'] = str(ticker_last_entry_datetime)
        gspread_all_values_dict[idx]['First Exit Time'] = str(ticker_first_exit_datetime)
        gspread_all_values_dict[idx]['Last Exit Time'] = str(ticker_last_exit_datetime)
        gspread_all_values_dict[idx]['Broker'] = broker
        gspread_all_values_dict[idx]['Charts'] = graphs

        # Ideal Entry Prices and Times #
        # Ideal entry prices and times can be computed after market close
        # Ideal exit times can also be computed after market close except for dd1 and aft bo strategies. These will
        # be computed after next day's market close

        # Grabbing csv data:
        # Question: What if you are short and long within same period?

# publish updated worksheet
gspread_df = pd.DataFrame(gspread_all_values_dict)
# remove columns that have google sheets formulas so we don't overwrite them
# gspread_df = gspread_df.loc[:, :gspread_first_hloc_column]
# select column range to write to
gspread_df = gspread_df.loc[:, gspread_first_auto_entry_column: gspread_first_hloc_column]
gspread_first_auto_entry_column_idx = worksheet.find(gspread_first_auto_entry_column)
gspread_last_raw_value_column_idx = worksheet.find(gspread_first_hloc_column)
# worksheet.update([gspread_df.columns.values.tolist()] + gspread_df.values.tolist())
worksheet.update(
    gspread_first_auto_entry_column_idx.address + ':' + gspread_last_raw_value_column_idx.address[0:-1] + str(
        len(gspread_all_values_dict) + 1),
    [gspread_df.columns.values.tolist()] + gspread_df.values.tolist())
