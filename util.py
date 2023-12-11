import os
import re
from datetime import datetime
import pandas as pd
import csv
import sys
import gspread
from configparser import ConfigParser
from finvizfinance.quote import finvizfinance
from polygon import RESTClient as plygRESTC
from typing import cast
from urllib3 import HTTPResponse
import json

config_object = ConfigParser()
config_object.read("config/config.ini")
DEBUG_PRINT = config_object['main']['DEBUG_PRINT']

# Grab TD configuration values.
polygon_api_key = config_object.get('main', 'POLYGON_API_KEY')
polygon_client = plygRESTC(polygon_api_key)
POLYGON_TRADES_HISTORY_RESPONSE_LIMIT = 50000


def dbg_print(string):
    if DEBUG_PRINT:
        print(string)


def get_gspread_worksheet(spreadsheet_name, worksheet_name):
    # Setup Google Sheets Connection
    gc = gspread.service_account()
    sh = gc.open(spreadsheet_name)
    # Params
    return sh.worksheet(worksheet_name)


def get_gspread_worksheet_values(worksheet):
    # Get all values from the worksheet and store in a dictionary and search for data that way. This reduces the amount
    # of API calls since there is a limit of 300 requests per minute per project and 60 requests per minute per user
    return worksheet.get_all_records()


# These functions use the csv naming convention of <broker>-<date>_<optional_description>.csv
def get_broker(trades_file):
    return os.path.basename(trades_file).split('-')[0]


def get_date(trades_file):
    broker = get_broker(trades_file)

    csv_file_date = re.split('_|\.', os.path.basename(trades_file).split(broker + '-')[1])[0]
    return datetime.strptime(csv_file_date, '%m-%d-%y')


# Read csv file into pandas dataframe
def trades_csv_to_df(trades_file):
    broker = get_broker(trades_file)
    if broker == 'etrade':
        csv_df = pd.DataFrame(columns=["Date", "Time", "Side", "Qty", "Symb", "Price"])

        with open(trades_file, "r") as f:
            # reader = csv.reader(f, delimiter="\t")
            reader = csv.reader(f)
            for i, line in enumerate(reader):
                # line list
                ll = line[0].replace('\t\t', ',').replace(' ', ',').split(",")
                # don't read cancelled or pending entries
                if ll[0].isspace() or ll[-3] != 'Executed':
                    continue
                # join time and AM/PM
                ll[1:3] = [' '.join(ll[1:3])]
                # convert to military to be consistent with cobra
                ll[1] = convert24(ll[1])
                # remove tabs from copy and pasted line
                ll[0] = ll[0].replace('\t', '')
                # remove the dollar sign and tabs
                ll[-1] = ll[-1].replace('$', '').replace('\t', '')
                # ll[0] -> Date
                # ll[1] -> Time
                # ll[3] -> Type
                # ll[4] -> Qty
                # ll[5] -> Symb
                # ll[-1] -> Price
                # csv_df_list[0] -> Date
                # csv_df_list[1] -> Time
                # csv_df_list[2] -> Type
                # csv_df_list[3] -> Qty
                # csv_df_list[4] -> Symb
                # csv_df_list[5] -> Price
                if 'Buy' == ll[3]: ll[3] = 'B'  # So it's consistent with Cobra's naming convention
                if 'Sell' == ll[3]: ll[3] = 'S'  # So it's consistent with Cobra's naming convention

                # For option trades
                if 'Call' in ll or 'Put' in ll:
                    ll[4] = 100 * int(ll[4])
                csv_df_list = [ll[0], ll[1], ll[3], int(ll[4]), ll[5], float(ll[-1])]
                csv_df.loc[len(csv_df)] = csv_df_list

    elif broker == 'cobra':
        csv_df = pd.read_csv(trades_file)
    else:
        print("wrong csv file name format")
        sys.exit()

    return csv_df


def export_trades_df_to_csv(df, trades_file, description):
    csv_idx = trades_file.index(".csv")
    df.to_csv(trades_file[:csv_idx] + '_' + description + '.csv', index=False)


def convert24(str1):
    # Checking if last two elements of time
    # is AM and first two elements are 12
    if str1[-2:] == "AM" and str1[:2] == "12":
        return "00" + str1[2:-3]

    # remove the AM
    elif str1[-2:] == "AM":
        return str1[:-3]

    # Checking if last two elements of time
    # is PM and first two elements are 12
    elif str1[-2:] == "PM" and str1[:2] == "12":
        return str1[:-3]

    else:

        # add 12 to hours and remove PM
        return str(int(str1[:2]) + 12) + str1[2:5]

def grab_finviz_fundamentals(ticker):

    stock = finvizfinance(ticker)
    fundamentals = stock.ticker_fundament()

    stock_dict = dict()

    stock_dict['Float'] = convert_stock_info_string_to_float(fundamentals['Shs Float'])
    stock_dict['Market Cap'] = convert_stock_info_string_to_float(fundamentals['Market Cap'])
    stock_dict['Sector'] = fundamentals['Sector']
    stock_dict['Industry'] = fundamentals['Industry']
    stock_dict['Exchange'] = fundamentals['Exchange']

    return stock_dict

def convert_stock_info_string_to_float(info):
    """
    :type info: 'xxxM' or 'xxxB' (M: 1 Million and B: 1 Billion)
    """
    if info[-1] == 'M':
        info = float(info[0:-1])*1000000
        return info
    elif info[-1] == 'B':
        info = float(info[0:-1])*1000000000
        return info
    else:
        print('data has suffix other than M or B. Exiting program')
        exit()

def get_ticker_list():

    tickers = cast(
        HTTPResponse,
        polygon_client.get_snapshot_all(market_type='stocks', include_otc=True, raw=True),
    )


    ddict = json.loads(tickers.data.decode("utf-8"))
    tickers_df = pd.DataFrame(ddict['tickers'])

    return tickers_df['ticker'].sort_values().tolist()

get_ticker_list()