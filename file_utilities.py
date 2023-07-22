import os
import re
from datetime import datetime
import pandas as pd
import csv
import sys


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
                if ll[7] != 'Executed':
                    continue
                # join time and AM/PM
                ll[1:3] = [' '.join(ll[1:3])]
                # remove tabs from copy and pasted line
                ll[0] = ll[0].replace('\t', '')
                # remove the dollar sign and tabs
                ll[8] = ll[8].replace('$', '').replace('\t', '')
                # ll[0] -> Date
                # ll[1] -> Time
                # ll[3] -> Type
                # ll[4] -> Qty
                # ll[5] -> Symb
                # ll[8] -> Price
                # csv_df_list[0] -> Date
                # csv_df_list[1] -> Time
                # csv_df_list[2] -> Type
                # csv_df_list[3] -> Qty
                # csv_df_list[4] -> Symb
                # csv_df_list[5] -> Price
                if 'Buy' == ll[3]: ll[3] = 'B' # So it's consistent with Cobra's naming convention
                if 'Sell' == ll[3]: ll[3] = 'S' # So it's consistent with Cobra's naming convention
                csv_df_list = [ll[0], ll[1], ll[3], int(ll[4]), ll[5], float(ll[8])]
                csv_df.loc[len(csv_df)] = csv_df_list

    elif broker == 'cobra':
        csv_df = pd.read_csv(trades_file)
    else:
        print("wrong csv file name format")
        sys.exit()

    return csv_df


def export_trades_df_to_csv(df, trades_file, description):
    df.to_csv(trades_file.split('.')[0] + '_' + description + '.csv', index=False)
