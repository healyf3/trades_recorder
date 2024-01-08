import sys
import util
from util import dbg_print
import hloc_utilities
from configparser import ConfigParser
import datetime
import pandas as pd


gspread_worksheet = sys.argv[1]

config_object = ConfigParser()
config_object.read("config/config.ini")

gspread_first_auto_entry_column = 'Float'
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

    # For testing
    #if gspread_entries['Ticker'] == 'NGM' or gspread_entries['Ticker'] == 'VYGR':
    #    continue

    dbg_print(gspread_entries['Ticker'])

    # Grab the date of trade
    gspread_trade_dt = datetime.datetime.strptime(gspread_entries['Date'], '%m/%d/%Y')

    # Get fundamental data
    float = gspread_all_values_dict[idx]['Float']
    mkt_cap = gspread_all_values_dict[idx]['Market Cap']
    sector = gspread_all_values_dict[idx]['Sector']
    industry = gspread_all_values_dict[idx]['Industry']
    exchange = gspread_all_values_dict[idx]['Exchange']
    fundamentals_dict = dict()
    update_fundamentals = False

    curr_date_trade_date_delta = datetime.datetime.today().date() - gspread_trade_dt.date()
    # want to fundamental info somewhat accurate so don't record it if 5 days have passed
    if curr_date_trade_date_delta < datetime.timedelta(days=5) and (exchange == ''):
        fundamentals_dict = util.grab_finviz_fundamentals(gspread_entries['Ticker'])
        update_fundamentals = True

    if gspread_entries['Next Close'] == '':


        today_dt = datetime.datetime.today()

        # Wait 4 days to grab data. This doesn't account for holidays and weekends yet.
        able_to_grab_data = (today_dt - gspread_trade_dt).days < 4
        if able_to_grab_data:
            dbg_print("Wait until market close to grab HLOC information for ticker " + gspread_entries["Ticker"])
            continue

        # Grab hloc info
        hloc_dict = hloc_utilities.get_intraday_data(gspread_entries['Ticker'], gspread_trade_dt, gspread_entries['Strategy'])

        hloc_dict['dollar_volume'], hloc_dict['max_3_year_dollar_volume'], hloc_dict['max_3_year_dollar_volume_date'] = \
            hloc_utilities.get_day_and_max_3_year_dollar_volume(gspread_entries['Ticker'], gspread_trade_dt)

        gspread_all_values_dict[idx]['$ Volume'] = hloc_dict['dollar_volume']
        gspread_all_values_dict[idx]['Max 3 Year $ Volume'] = hloc_dict['max_3_year_dollar_volume']
        gspread_all_values_dict[idx]['Max 3 Year $ Vol Date'] = hloc_dict['max_3_year_dollar_volume_date']
        gspread_all_values_dict[idx]['Prev Close'] = hloc_dict['previous_close']
        gspread_all_values_dict[idx]['High'] = hloc_dict['high']
        gspread_all_values_dict[idx]['Low'] = hloc_dict['low']
        gspread_all_values_dict[idx]['Open'] = hloc_dict['open']
        gspread_all_values_dict[idx]['Close'] = hloc_dict['close']
        gspread_all_values_dict[idx]['Next High'] = hloc_dict['next_day_high']
        gspread_all_values_dict[idx]['Next Low'] = hloc_dict['next_day_low']
        gspread_all_values_dict[idx]['Next Open'] = hloc_dict['next_day_open']
        gspread_all_values_dict[idx]['Next Close'] = hloc_dict['next_day_close']
        gspread_all_values_dict[idx]['High Time'] = hloc_dict['high_time'].to_pydatetime().replace(tzinfo=None).strftime("%Y-%m-%d %H:%M:%S")
        gspread_all_values_dict[idx]['Low Time'] = hloc_dict['low_time'].to_pydatetime().replace(tzinfo=None).strftime("%Y-%m-%d %H:%M:%S")
        gspread_all_values_dict[idx]['Next High Time'] = hloc_dict['next_day_high_time'].to_pydatetime().replace(tzinfo=None).strftime("%Y-%m-%d %H:%M:%S")
        gspread_all_values_dict[idx]['Next Low Time'] = hloc_dict['next_day_low_time'].to_pydatetime().replace(tzinfo=None).strftime("%Y-%m-%d %H:%M:%S")
        gspread_all_values_dict[idx]['Morn High'] = hloc_dict['morning_high']
        gspread_all_values_dict[idx]['Morn Low'] = hloc_dict['morning_low']
        gspread_all_values_dict[idx]['Aft High'] = hloc_dict['afternoon_high']
        gspread_all_values_dict[idx]['Aft Low'] = hloc_dict['afternoon_low']
        gspread_all_values_dict[idx]['Morn High Time'] = hloc_dict['morning_high_time'].to_pydatetime().replace(tzinfo=None).strftime("%Y-%m-%d %H:%M:%S")
        gspread_all_values_dict[idx]['Morn Low Time'] = hloc_dict['morning_low_time'].to_pydatetime().replace(tzinfo=None).strftime("%Y-%m-%d %H:%M:%S")
        gspread_all_values_dict[idx]['Aft High Time'] = hloc_dict['afternoon_high_time'].to_pydatetime().replace(tzinfo=None).strftime("%Y-%m-%d %H:%M:%S")
        gspread_all_values_dict[idx]['Aft Low Time'] = hloc_dict['afternoon_low_time'].to_pydatetime().replace(tzinfo=None).strftime("%Y-%m-%d %H:%M:%S")

        # For testing
        #if gspread_entries['Ticker'] == 'TTOO':
        #    break

    # update fundamentals if need be regardless of appropriate hloc recording
    if update_fundamentals:
        gspread_all_values_dict[idx]['Float'] = fundamentals_dict['Float']
        gspread_all_values_dict[idx]['Market Cap'] = fundamentals_dict['Market Cap']
        gspread_all_values_dict[idx]['Sector'] = fundamentals_dict['Sector']
        gspread_all_values_dict[idx]['Industry'] = fundamentals_dict['Industry']
        gspread_all_values_dict[idx]['Exchange'] = fundamentals_dict['Exchange']




# publish updated worksheet
gspread_df = pd.DataFrame(gspread_all_values_dict)
# remove columns that have google sheets formulas so we don't overwrite them
gspread_df = gspread_df.loc[:,gspread_first_auto_entry_column: gspread_last_auto_entry_column]
gspread_first_auto_entry_column_idx = worksheet.find(gspread_first_auto_entry_column)
gspread_last_raw_value_column_idx = worksheet.find(gspread_last_auto_entry_column)
#worksheet.update([gspread_df.columns.values.tolist()] + gspread_df.values.tolist())
worksheet.update(gspread_first_auto_entry_column_idx.address + ':' + gspread_last_raw_value_column_idx.address[0:-1]+str(len(gspread_all_values_dict)+1),
                 [gspread_df.columns.values.tolist()] + gspread_df.values.tolist())
