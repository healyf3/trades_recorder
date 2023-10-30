import sys
import os
import csv
import pandas as pd
from datetime import datetime
import re

trades_file = sys.argv[1]
print(trades_file)

# Read csv file into pandas dataframe
broker = os.path.basename(trades_file).split('-')[0]
csv_file_date = os.path.basename(trades_file).split(broker + '-')[1].split('.')[0]
csv_file_date = datetime.strptime(csv_file_date, '%m-%d-%y')

etrade_df = pd.DataFrame(columns=["date", "time", "side", "qty", "symb", "price"])

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
        ll[0] = ll[0].replace('\t','')
        # remove the dollar sign and tabs
        ll[8] = ll[8].replace('$','').replace('\t','')
        df_list = [ll[0], ll[1],ll[3],ll[4],ll[5],ll[8]]
        etrade_df.loc[len(etrade_df)] = df_list

csv_entry_names_dict = {"symb": "Symb", "side": "Side", "qty": "Qty", "price": "Price", "time": "Time", "date": "Date"}

# These are entries from the actual etrade website statement
# if broker == 'etrade':
#    csv_entry_names_dict = {"date": "Trade Date", "symb": "Security", "side": "Order Type", "qty": "Quantity",
#                            "price": "Executed Price", "time": "Time"}

df = pd.read_csv(trades_file)
# Add dollar value to each entry/exit
df['dollar_val'] = df['Executed Price'] * df['Quantity']
# Get dollar value sum
df_sum = df.groupby(['Security', 'Order Type'])['dollar_val'].sum()
# Get weight
df_weight = df.groupby(['Security', 'Order Type'])['Quantity'].sum()
# Compute Average Price
df_avg_prices = df_sum / df_weight
print(df_avg_prices.to_string())

print('end')
