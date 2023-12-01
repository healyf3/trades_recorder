import sys
import util
from util import dbg_print
import hloc_utilities
from configparser import ConfigParser
import datetime
import pandas as pd


gspread_worksheet = sys.argv[2]

config_object = ConfigParser()
config_object.read("config/config.ini")

gspread_first_auto_entry_column = 'Prev Close'
gspread_last_auto_entry_column = 'Aft Low Time'

if 'trades' == gspread_worksheet:
    worksheet = util.get_gspread_worksheet(config_object['main']['GSPREAD_SPREADSHEET'],config_object['main']['GSPREAD_TRADES_WORKSHEET'])
elif 'missed_ops' == gspread_worksheet:
    worksheet = util.get_gspread_worksheet(config_object['main']['GSPREAD_SPREADSHEET'],config_object['main']['GSPREAD_MISSED_OPPORTUNITIES_WORKSHEET'])
else:
    print('incorrect worksheet. Exiting program')
    sys.exit(1)


# df = hloc_utilities.get_intraday_ticks(ticker, gspread_trade_date)

gspread_all_values_dict = util.get_gspread_worksheet_values(worksheet)

# Find entries that aren't filled.
for idx, gspread_entries in enumerate(gspread_all_values_dict):
    if gspread_entries['Next Close'] == '':

        # Grab the date of trade
        gspread_trade_date = datetime.datetime.strptime(gspread_entries['Date'], '%m/%d/%Y')

        today_dt = datetime.datetime.today()

        if (today_dt - gspread_trade_date).days < 1:
            dbg_print("For ticker: " + gspread_entries["Ticker"] + "Wait at least one day after trade took place to grab HLOC information")
            continue

        # Wait 3 days to grab data. This doesn't account for holidays and weekends yet.
        if (today_dt - gspread_trade_date).days < 3:
            dbg_print("Wait until market close to grab HLOC information for ticker " + gspread_entries["Ticker"])
            continue

        # Grab hloc info
        hloc_dict = hloc_utilities.get_intraday_data(gspread_entries['Ticker'], gspread_trade_date, gspread_entries['Strategy'])

        gspread_all_values_dict[idx]['Prev Close'] = hloc_dict['previous_close']
        gspread_all_values_dict[idx]['High'] = hloc_dict['high']
        gspread_all_values_dict[idx]['Low'] = hloc_dict['low']
        gspread_all_values_dict[idx]['Open'] = hloc_dict['open']
        gspread_all_values_dict[idx]['Close'] = hloc_dict['close']
        gspread_all_values_dict[idx]['Next High'] = hloc_dict['next_day_high']
        gspread_all_values_dict[idx]['Next Low'] = hloc_dict['next_day_low']
        gspread_all_values_dict[idx]['Next Open'] = hloc_dict['next_day_open']
        gspread_all_values_dict[idx]['Next Close'] = hloc_dict['next_day_close']
        gspread_all_values_dict[idx]['High Time'] = hloc_dict['next_day_close']

# publish updated worksheet
gspread_df = pd.DataFrame(gspread_all_values_dict)
# remove columns that have google sheets formulas so we don't overwrite them
gspread_df = gspread_df.loc[:,gspread_first_auto_entry_column: gspread_last_auto_entry_column]
gspread_first_auto_entry_column_idx = worksheet.find(gspread_first_auto_entry_column)
gspread_last_raw_value_column_idx = worksheet.find(gspread_last_auto_entry_column)
#worksheet.update([gspread_df.columns.values.tolist()] + gspread_df.values.tolist())
worksheet.update(gspread_first_auto_entry_column_idx.address + ':' + gspread_last_raw_value_column_idx.address[0:-1]+str(len(gspread_all_values_dict)+1),