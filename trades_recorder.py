import sys
import csv
import pandas as pd
import gspread

#from pydrive.auth import GoogleAuth
#from pydrive.auth import ServiceAccountCredentials
#from pydrive.drive import GoogleDrive

from trading_charts_folder_ids import folder_ids

trades_file = sys.argv[1]

empty_start_column = 'G'

# Setup Google Sheets Connection
gc = gspread.service_account()
sh = gc.open("Trades")
# Params
worksheet = sh.worksheet("Trades")

#gauth = GoogleAuth()
#scope = ['https://www.googleapis.com/auth/drive']
#gauth.credentials = ServiceAccountCredentials.from_json_keyfile_name(
#    os.path.expanduser('~/.config/gspread/service_account.json'), scope)
#drive = GoogleDrive(gauth)
# Setup Google Sheets Connection
#worksheet = utilities.setup_gspread_worksheet_connection(spreadsheet_name=spreadsheet_name,
#                                                         worksheet_name=worksheet_name)

# Initialize Google Sheets Data Frame
columns = ["Ticker", "Side", "Avg Entry Price", "Avg Exit Price", "% gain/loss", "First Entry Time", "Last Entry Time",
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
result = [time[idx], symbol, previous_day_dollar_volume, dollar_volume, previous_close,
          df.iloc[idx, df.columns.get_loc('open')], df.iloc[idx, df.columns.get_loc('close')],
          next_open, next_low, next_high, next_close, next_next_open, next_next_low, next_next_high, next_next_close]
gspread_df.loc[len(gspread_df)] = result

worksheet.append_row(values=result, table_range=empty_start_column + str((ticker[2])))
