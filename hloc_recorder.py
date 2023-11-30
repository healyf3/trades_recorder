import util
from util import dbg_print
import hloc_utilities
from configparser import ConfigParser
import datetime


config_object = ConfigParser()
config_object.read("config/config.ini")

gspread_last_raw_value_column = 'Aft Low Time'
gspread_first_auto_entry = 'High'

# df = hloc_utilities.get_intraday_ticks(ticker, gspread_trade_date)

worksheet = util.get_gspread_worksheet(config_object['main']['GSPREAD_WORKSHEET'])

gspread_all_values_dict = util.get_gspread_worksheet_values(worksheet)

# Find entries that aren't filled.
for idx, gspread_entries in enumerate(gspread_all_values_dict):
    if gspread_entries['Next Close'] == '':

        # Grab the date of trade
        gspread_trade_date = datetime.datetime.strptime(gspread_entries['Date'], '%m/%d/%Y')

        today_dt = datetime.datetime.today()

        if (today_dt - gspread_trade_date).days < 1:
            dbg_print("Wait at least one day to grab HLOC information")
            continue

        # Note: 21 is 4pm Eastern always regardless of whether it is daylight savings time.
        # The below conditional checks if it is after market close of the next day. If it is, the next close and all
        # other hloc information can be grabbed. (Unless it's a holiday or the weekend)
        if today_dt.utcnow().hour < 21 and (today_dt - gspread_trade_date).days < 2:
            dbg_print("Wait until market close to grab HLOC information for ticker " + gspread_entries["Ticker"])
            continue

        # Grab hloc info
        hloc_dict = hloc_utilities.get_intraday_data(gspread_entries['Ticker'], gspread_trade_date, gspread_entries['Strategy'])

        gspread_all_values_dict[idx]['High'] = hloc_dict['high']
        gspread_all_values_dict[idx]['Low'] = hloc_dict['low']
        gspread_all_values_dict[idx]['Open'] = hloc_dict['open']
        gspread_all_values_dict[idx]['Close'] = hloc_dict['close']
        gspread_all_values_dict[idx]['Next High'] = hloc_dict['next_day_high']
        gspread_all_values_dict[idx]['Next Low'] = hloc_dict['next_day_low']
        gspread_all_values_dict[idx]['Next Open'] = hloc_dict['next_day_open']
        gspread_all_values_dict[idx]['Next Close'] = hloc_dict['next_day_close']

# publish updated worksheet
gspread_df = pd.DataFrame(gspread_all_values_dict)
# remove columns that have google sheets formulas so we don't overwrite them
gspread_df = gspread_df.loc[:, :gspread_last_raw_value_column]
#gspread_df = gspread_df.loc[:, :gspread_last_raw_value_column]
worksheet.update([gspread_df.columns.values.tolist()] + gspread_df.values.tolist())