import datetime
import gspread
from grab_holiday_dates import grab_holidays_from_csv
import requests
from bs4 import BeautifulSoup
import re
import pytz
from configparser import ConfigParser
from polygon import RESTClient as plygRESTC
from typing import cast
from urllib3 import HTTPResponse
import json
import pandas as pd

# Grab TD configuration values.
config = ConfigParser()
config.read('config/config.ini')
polygon_api_key = config.get('main', 'POLYGON_API_KEY')
polygon_client = plygRESTC(polygon_api_key)
POLYGON_TRADES_HISTORY_RESPONSE_LIMIT = 50000


def get_intraday_ticks(ticker, date):
    if not isinstance(date, datetime.datetime):
        date = datetime.datetime.strptime(date, "%Y-%m-%d")

    aggs = cast(
        HTTPResponse,
        polygon_client.get_aggs(ticker, 1, "minute", date.date(), date.date(), raw=True),
    )

    ddict = json.loads(aggs.data.decode("utf-8"))
    tick_df = pd.DataFrame(ddict['results'])

    return tick_df

def is_dst(dt, timeZone):
    aware_dt = timeZone.localize(dt)
    return aware_dt.dst() != datetime.timedelta(0, 0)


def set_correct_date_if_the_weekend(dt, t_delta):
    is_a_weekend = False
    # In this case, we are trying to grab the previous day
    if dt.weekday() == 6:  # For Sunday. (Wanting to grab previous day)
        is_a_weekend = True
        dt = dt - datetime.timedelta(days=2)
        t_delta = t_delta - datetime.timedelta(days=2)
    # In this case, we are trying to grab the next day
    elif dt.weekday() == 5:  # For Saturday. (Wanting to grab next day)
        is_a_weekend = True
        dt = dt + datetime.timedelta(days=2)
        t_delta = t_delta + datetime.timedelta(days=2)

    return is_a_weekend, dt, t_delta


def is_next_prev_a_holiday(dt, next_or_prev_day, t_delta):
    holidays = grab_holidays_from_csv()
    is_a_holiday = False
    while str(dt.date()) in holidays:
        is_a_holiday = True
        if next_or_prev_day == 'prev':
            dt = dt - datetime.timedelta(days=1)
            t_delta = t_delta - datetime.timedelta(days=1)
        elif next_or_prev_day == 'next':
            dt = dt + datetime.timedelta(days=1)
            t_delta = t_delta + datetime.timedelta(days=1)
        else:
            print('neither next or prev day for holiday filter')

    return is_a_holiday, dt, t_delta


def set_correct_date_if_holiday_or_weekend(dt, next_or_prev_day):
    t_delta = datetime.timedelta(0)
    check_for_weekend = True
    check_for_holiday = True

    while check_for_weekend or check_for_holiday:
        check_for_holiday, dt, t_delta = set_correct_date_if_the_weekend(dt, t_delta)
        check_for_weekend, dt, t_delta = is_next_prev_a_holiday(dt, next_or_prev_day, t_delta)

    return dt, t_delta


def get_daily_trade_count():
    return


def get_daily_volume_count():
    return


def get_premarket_volume_count():
    return


def setup_gspread_worksheet_connection(spreadsheet_name, worksheet_name):
    gc = gspread.service_account()
    sh = gc.open(spreadsheet_name)
    return sh.worksheet(worksheet_name)


def grab_gspread_tickers_to_backtest(worksheet, empty_start_column_idx):
    # Grab next row to fill. (We start filling data out in the empty start column)
    float_list = list(filter(None, worksheet.col_values(empty_start_column_idx)))
    empty_row = (len(float_list) + 1)

    # Grab remaining tickers
    date_list = list(filter(None, worksheet.col_values(1)))
    last_date_row = len(date_list)
    ticker_list = list(filter(None, worksheet.col_values(2)))

    date_list = date_list[empty_row - 1:last_date_row]
    ticker_list = ticker_list[empty_row - 1:last_date_row]

    rows = list(range(empty_row, last_date_row + 1))

    tickers = list(zip(date_list, ticker_list, rows))
    # tickers = list(zip(date_list, ticker_list, list(range(100))))

    return tickers
    # return tickers[1:]


def get_gspread_all_tickers(worksheet):
    ticker_list = list(filter(None, worksheet.col_values(1)))
    date_list = list(filter(None, worksheet.col_values(2)))
    rows = list(range(0, len(ticker_list)))
    tickers = list(zip(ticker_list, date_list, rows))
    return tickers[1:]


def get_sector_info(url):
    html = requests.get(url).text
    soup = BeautifulSoup(html, 'html.parser')
    sector_label = soup.find("span", text="Sector")
    sector = 'N/A'
    industry = 'N/A'
    try:
        sector = sector_label.next_sibling.next_sibling.getText()
        industry_label = soup.find("span", text="Industry")
        industry = industry_label.next_sibling.next_sibling.getText()
        # remove \t, \n, etc.
        sector = sector.strip()
        industry = industry.strip()
    except:
        print('sector not found')

    return sector, industry
    # test
    # return "na", "na"


def get_float_sector_info(ticker):
    floatchecker_url = 'https://www.floatchecker.com/stock?float='
    floatchecker_url = floatchecker_url + ticker
    html = requests.get(floatchecker_url).text
    soup = BeautifulSoup(html, 'html.parser')
    regex_list = [re.compile('Morningstar.'), re.compile('FinViz'), re.compile('Yahoo Finance'),
                  re.compile('Wall Street Journal')]
    info_dict = {}
    l = [None] * 5
    grab_sector = True
    # while the float is unavailable, search in the next regex
    i = 0
    while l[2] is None and i < len(regex_list):
        j = 0
        num = [None] * 3  # list for float, short interest, and outstanding shares
        for link in soup.find_all('a'):
            title = link.get('title')
            if re.match(regex_list[i], str(title)):
                # only grab sector once
                if grab_sector:
                    sector, industry = get_sector_info(link.get('href'))
                    l[0] = sector
                    l[1] = industry
                    grab_sector = False

                num[j] = re.findall('\d*\.?\d+', link.getText())
                # If the float is available for the regex column then we will try to grab short interest and oustanding shares too.
                # If not, then we will move to the next regex
                if not num[0]:
                    j = 0
                    break

                if num[j]:
                    l[j + 2] = num[j][0]
                j = j + 1
        i = i + 1

    info_dict['sector'] = 'N/A'
    info_dict['industry'] = 'N/A'
    info_dict['float'] = 'N/A'
    info_dict['short interest'] = 'N/A'
    info_dict['shares outstanding'] = 'N/A'

    info_dict['sector'] = l[0]
    info_dict['industry'] = l[1]
    if l[2] is not None:
        info_dict['float'] = float(l[2]) * 1000000
    else:
        info_dict['float'] = 'N/A'
    if l[3] is not None:
        info_dict['short interest'] = float(l[3]) / 100
    else:
        info_dict['short interest'] = 'N/A'
    if l[4] is not None:
        info_dict['shares outstanding'] = float(l[4]) * 1000000
    else:
        info_dict['short interest'] = 'N/A'

    return info_dict


def hloc(frame, time_frame, t_delta, eastern_td):
    """ Returns:
        1. High
        2. Low
        3. Open
        4. Close
        5. High Time
        6. Low Time
        7. Volume
    """

    hloc_d = dict()
    hloc_d['high'] = 'N/A'
    hloc_d['low'] = 'N/A'
    hloc_d['open'] = 'N/A'
    hloc_d['close'] = 'N/A'
    hloc_d['high_time'] = 'N/A'
    hloc_d['low_time'] = 'N/A'
    hloc_d['volume'] = 0
    hloc_d['df'] = 'N/A'
    hloc_d['high_time'] = 'N/A'
    hloc_d['low_time'] = 'N/A'

    # unix time units
    local_frame = frame.copy()
    dt = datetime.datetime.fromtimestamp(local_frame['t'][0] / 1000).date() + t_delta
    dt_start = str(dt) + ' ' + time_frame[0]
    dt_end = str(dt) + ' ' + time_frame[-1]
    # create regular market hour frame
    local_frame['t'] = local_frame.t.apply(
        lambda x: datetime.datetime.fromtimestamp(x / 1000).astimezone(pytz.timezone('UTC')))
    df = local_frame.set_index('t')
    df = df.loc[dt_start:dt_end]
    if df.empty:
        print('DataFrame is empty!')
        return hloc_d

    hloc_d['high'] = df['h'].max()
    hloc_d['low'] = df['l'].min()
    hloc_d['open'] = df['o'][0]
    hloc_d['close'] = df['c'][-1]
    hloc_d['high_time'] = df['h'].idxmax()
    hloc_d['low_time'] = df['l'].idxmin()
    hloc_d['volume'] = df['v'].sum()
    hloc_d['df'] = df
    # convert to readable time

    hloc_d['high_time'] = hloc_d['high_time'] - eastern_td
    hloc_d['low_time'] = hloc_d['low_time'] - eastern_td

    return hloc_d


def pre_market_hloc(frame, t_delta):
    """ Returns:
        1. Premarket High
        2. Premarket Low
        3. Premarket Open
        4. Premarket Close
        5. Premarket High Time
        6. Premarket Low Time
        7. Premarket Volume
    """
    local_frame = frame.copy()
    if is_dst(datetime.datetime.fromtimestamp(local_frame['t'][0] / 1000) + t_delta, pytz.timezone("US/Eastern")):
        eastern_td = datetime.timedelta(hours=4)
        hloc_d = hloc(frame, time_frame=['8:00:00', '13:29:00'], t_delta=t_delta, eastern_td=eastern_td)
    else:
        eastern_td = datetime.timedelta(hours=5)
        hloc_d = hloc(frame, time_frame=['9:00:00', '14:29:00'], t_delta=t_delta, eastern_td=eastern_td)

    hloc_d = {"pre_mkt" + '_' + k: v for k, v in hloc_d.items()}
    return hloc_d


def reg_market_hloc(frame, t_delta):
    """ Returns:
     1. Regular Hours High
     2. Regular Hours Low
     3. Regular Hours Open
     4. Regular Hours Close
     5. Regular Hours High Time
     6. Regular Hours Low Time
     8. Regular Hours Morning Volume
     9. Regular Hours Afternoon Volume
        7. Regular Hours Total Volume
        8. Morning High
        9. Morning Low
        10. Afternoon High
        11. Afternoon Low
    """
    local_frame = frame.copy()
    # check for daylight savings time
    # if utilities.is_dst(self._frame['datetime'][0].date()+t_delta,pytz.timezone("US/Eastern")):
    if is_dst(datetime.datetime.fromtimestamp(local_frame['t'][0] / 1000) + t_delta, pytz.timezone("US/Eastern")):
        time_frame = ['13:30:00', '16:00:00', '19:59:00']
        eastern_td = datetime.timedelta(hours=4)
    else:
        time_frame = ['14:30:00', '17:00:00', '20:59:00']
        eastern_td = datetime.timedelta(hours=5)

    hloc_d = hloc(local_frame, time_frame, t_delta, eastern_td)
    # morning_df = hloc_d['df'][time_frame[0]:time_frame[1]]

    # unix time units
    dt_afternoon = str(hloc_d['df'].index[0].date()) + ' ' + time_frame[1]
    # date_format_str = '%Y-%m-%d %H:%M:%S'

    # make sure the date index exists. If it doesn't this means there wasn't any volume in that period so
    # we will go to the next minute
    # convert afternoon time_frame string into timedelta object incase we need to search for the next index
    afternoon_time_frame_td = datetime.datetime.strptime(time_frame[1], "%H:%M:%S")
    m = 1
    while dt_afternoon not in hloc_d['df'].index:
        incremented_time = (afternoon_time_frame_td + datetime.timedelta(minutes=m)).time()
        dt_afternoon = str(hloc_d['df'].index[0].date()) + ' ' + str(incremented_time)
        m = m + 1

    num_idx_afternoon = hloc_d['df'].index.get_loc(dt_afternoon)
    morning_frame = hloc_d['df'].iloc[:num_idx_afternoon]
    afternoon_frame = hloc_d['df'].iloc[num_idx_afternoon:]

    # for IPO's coming out in the afternoon
    if morning_frame.empty:
        hloc_d['morning_high'] = 'n/a'
        hloc_d['morning_low'] = 'n/a'
        hloc_d['morning_high_time'] = 'n/a'
        hloc_d['morning_low_time'] = 'n/a'
        hloc_d['morning_volume'] = 'n/a'
    else:
        hloc_d['morning_high'] = morning_frame['h'].max()
        hloc_d['morning_low'] = morning_frame['l'].min()
        hloc_d['morning_high_time'] = morning_frame['h'].idxmax()
        hloc_d['morning_low_time'] = morning_frame['l'].idxmin()
        hloc_d['morning_volume'] = int(morning_frame['v'].sum())
        # convert to readable time
        hloc_d['morning_high_time'] = hloc_d['morning_high_time'] - eastern_td
        hloc_d['morning_low_time'] = hloc_d['morning_low_time'] - eastern_td

    hloc_d['afternoon_high'] = afternoon_frame['h'].max()
    hloc_d['afternoon_low'] = afternoon_frame['l'].min()
    hloc_d['afternoon_high_time'] = afternoon_frame['h'].idxmax()
    hloc_d['afternoon_low_time'] = afternoon_frame['l'].idxmin()
    hloc_d['afternoon_volume'] = afternoon_frame['v'].sum()
    hloc_d['afternoon_high_time'] = hloc_d['afternoon_high_time'] - eastern_td
    hloc_d['afternoon_low_time'] = hloc_d['afternoon_low_time'] - eastern_td

    return hloc_d
