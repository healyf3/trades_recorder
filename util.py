import os
import re
from datetime import datetime
import pandas as pd
import csv
import sys
import gspread

# TODO: move constants to a more centralized location
DBG_PRINT = False
spreadsheet_name = "Trades"
def dbg_print(str):
    if (DBG_PRINT):
        print(str)

def get_gspread_worksheet_values(trades_file):
    # Setup Google Sheets Connection
    gc = gspread.service_account()
    sh = gc.open(spreadsheet_name)
    # Params
    worksheet = sh.worksheet(spreadsheet_name)
    # worksheet = sh.worksheet("TradesTest") # testcase

    # Get all values from the worksheet and store in a dictionary and search for data that way. This reduces the amount
    # of API calls since there is a limit of 300 requests per minute per project and 60 requests per minute per user
    gspread_all_values_dict = worksheet.get_all_records()

    return gspread_all_values_dict


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
                if 'Buy' == ll[3]: ll[3] = 'B' # So it's consistent with Cobra's naming convention
                if 'Sell' == ll[3]: ll[3] = 'S' # So it's consistent with Cobra's naming convention

                # For option trades
                if 'Call' in ll or 'Put' in ll:
                    ll[4] = 100*int(ll[4])
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
