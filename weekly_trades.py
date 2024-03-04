import util
from configparser import ConfigParser
import webbrowser
import datetime
from util import dbg_print


config_object = ConfigParser()
config_object.read("config/config.ini")

today = datetime.date.today()
last_monday = today+datetime.timedelta(days=-today.weekday())
last_friday = last_monday+datetime.timedelta(days=4)

worksheet = util.get_gspread_worksheet(config_object['main']['GSPREAD_SPREADSHEET'],
                                       config_object['main']['GSPREAD_TRADES_WORKSHEET'])

gspread_all_values_dict = util.get_gspread_worksheet_values(worksheet)

weekly_trades_url_list = []
for idx, gspread_entries in enumerate(gspread_all_values_dict):
    if last_monday <= datetime.datetime.strptime(gspread_entries['Date'], "%m/%d/%Y").date() <= last_friday:
        dbg_print(gspread_entries['Ticker'])
        weekly_trades_url_list.append(gspread_entries['Charts'])

for i in weekly_trades_url_list:
    webbrowser.open(i)