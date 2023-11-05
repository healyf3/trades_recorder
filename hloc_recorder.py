import util
import hloc_utilities
from configparser import ConfigParser


config_object = ConfigParser()
config_object.read("config/config.ini")

# df = hloc_utilities.get_intraday_ticks(ticker, gspread_trade_date)
