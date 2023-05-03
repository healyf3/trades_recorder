import sys
import csv
import pandas as pd
import gspread

import utilities

#from pydrive.auth import GoogleAuth
#from pydrive.auth import ServiceAccountCredentials
#from pydrive.drive import GoogleDrive

from trading_charts_folder_ids import folder_ids

trades_file = sys.argv[1]
print(trades_file)

empty_start_column = 'N'

# Setup Google Sheets Connection
gc = gspread.service_account()
sh = gc.open("Trades")
# Params
worksheet = sh.worksheet("Trades")

# Initialize Google Sheets Data Frame
columns = ["Ticker", "Side", "Avg Entry Price", "Avg Exit Price", "First Entry Time", "Last Entry Time",
           "Ideal Entry Time", "Ideal Entry Price", "First Exit Time", "Last Exit Time", "Ideal Exit Time", "Ideal Exit Price"]

gspread_df = pd.DataFrame(columns=columns)

df = pd.read_csv(trades_file)

# Group by symbol and time
df = df.sort_values(['Symb', 'Time'])

df['dollar_val'] = df['Price']*df['Qty']
print(df.to_string())

# Get first and last time of both the entry and the exit
df_time_min = df.groupby(['Symb','Side'])['Time'].min()
df_time_max = df.groupby(['Symb','Side'])['Time'].max()
print(df_time_min.to_string())
print(df_time_max.to_string())

# Get dollar value sum
df_sum = df.groupby(['Symb','Side'])['dollar_val'].sum()

# Get weight
df_weight = df.groupby(['Symb','Side'])['Qty'].sum()
print(df_sum.to_string())
print(df_weight.to_string())

# Compute Average Price
df_avg_prices = df_sum/df_weight
print(df_avg_prices.to_string())

## place data in google sheets ##
#result = [time[idx], symbol, previous_day_dollar_volume, dollar_volume, previous_close,
#          df.iloc[idx, df.columns.get_loc('open')], df.iloc[idx, df.columns.get_loc('close')],
#          next_open, next_low, next_high, next_close, next_next_open, next_next_low, next_next_high, next_next_close]
#gspread_df.loc[len(gspread_df)] = result

#worksheet.append_row(values=result, table_range=empty_start_column + str((ticker[2])))

alpha_list = ('A','B','C','D','E','F','G','H','I','J','K','L','M','N','O','P','Q','R','S','T','U','V','W','X','Y','Z',
              'AA','AB','AC','AD')

# Columns
symbol_col = 'B'
avg_entry_col = 'P'
avg_exit_col = 'Q'
first_entry_time_col = 'R'
last_entry_time_col = 'S'
ideal_entry_time_col = 'T'
ideal_entry_price_col = 'U'
first_exit_time_col = 'V'
last_exit_time_col = 'W'
ideal_exit_time_col = 'X'
ideal_exit_price_col = 'Y'
dollar_volume_col = "Z"
max_3_year_dollar_volume_col = "AA"
float_col = "AB"
market_cap_col = 'AC'
sector_col = 'AD'

## testcase
#worksheet.update_cell(6,1, "hi")
print(alpha_list.index(symbol_col))
print(worksheet.cell(3,alpha_list.index(avg_entry_col)+1).value)


## search row for column id according to name
cell = worksheet.find("Last Exit Time")
print(cell.col)
## Last complete trade cell
i = 1
print(worksheet.cell(2, cell.col).value)
while worksheet.cell(i, cell.col).value != None:
    print(worksheet.cell(i,cell.col).value)
    i = i + 1
print(i) # First Incomplete trade last completed trade

# Get end of list through trade date or Strategy

# Make ideal exit time intervals based on strategy
# dd1: low of day, vs low of next day vs low of next pm, etc.

