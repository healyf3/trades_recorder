import datetime
from datetime import timedelta
import gspread
from grab_holiday_dates import grab_holidays_from_csv
import pytz
from configparser import ConfigParser
import json
import pandas as pd
from typing import cast
from urllib3 import HTTPResponse

import util
from util import polygon_client


def get_daily_ticks(ticker, start_date, end_date, years=0, days=0):

    if not isinstance(start_date, datetime.datetime):
        start_date = datetime.datetime.strptime(start_date, "%Y-%m-%d")
    if not isinstance(end_date, datetime.datetime):
        end_date = datetime.datetime.strptime(end_date, "%Y-%m-%d")

    aggs = cast(
        HTTPResponse,
        polygon_client.get_aggs(ticker, 1, "day", start_date, end_date, raw=True),
    )

    ddict = json.loads(aggs.data.decode("utf-8"))
    tick_df = pd.DataFrame(ddict['results'])

    return tick_df



def get_intraday_data(ticker, start_dt, strategy_name):

    data_dict = dict()
    # Grab the historical prices
    # Ts in nanoseconds specifically for polygon
    # The Date starts at 12am and goes through the next day to 8pm (aftermarket hours)
    end_dt = start_dt + timedelta(days=1, hours=20)
    prev_dt = start_dt - timedelta(days=1)

    while True:
        # TODO: The script can probably do without checking the weekends or holidays. Just go back at most 4 days and if
        # the 4 day doesn't give any data then print a message and continue to the next ticker
        end_dt, holiday_weekend_next_t_delta = set_correct_date_if_holiday_or_weekend(end_dt, 'next')
        prev_dt, _ = set_correct_date_if_holiday_or_weekend(prev_dt, 'prev')
        next_day_t_delta = timedelta(days=1)
        next_day_t_delta = next_day_t_delta + holiday_weekend_next_t_delta

        start_end_td = end_dt - start_dt
        aggs = cast(
            HTTPResponse,
            polygon_client.get_aggs(ticker, 1, "minute", start_dt, end_dt, raw=True),
        )

        ddict = json.loads(aggs.data.decode("utf-8"))
        tick_df = pd.DataFrame(ddict['results'])

        last_timestamp_datetime = datetime.datetime.fromtimestamp(tick_df.iloc[-1]['t']/1000)
        # This accounts for a stock that haulted during the day. This checks to the last timestamp in the frame and
        # verifies that it has data at 10am the next day
        # If there are 10 days between the next day then just break. The company may have changed ticker
        # ($AGIL went bankrupt and became AGILQ)
        if (last_timestamp_datetime > (end_dt - timedelta(hours=10))) or ((end_dt-start_dt).days > 10):
            break
        end_dt = end_dt + timedelta(days=1)
        next_day_t_delta = next_day_t_delta + timedelta(days=1)


    # this previous date logic accounts for halts that may last up to months
    prev_ddict = dict()
    prev_ddict['query_count'] = 0
    previous_date = prev_dt.date()
    while True:
        # grab previous close
        prev_aggs = cast(
            HTTPResponse,
            polygon_client.get_aggs(ticker, 1, "day", previous_date, previous_date, raw=True),
        )

        prev_ddict = json.loads(prev_aggs.data.decode("utf-8"))
        if prev_ddict['queryCount'] > 0:
            break
        previous_date = previous_date - timedelta(days=1)

    prev_tick_df = pd.DataFrame(prev_ddict['results'])
    data_dict['previous_close'] = float(prev_tick_df['c'][0]) # in some cases when the number is even, the type will be int64 which isn't serializable by gspread

    util.dbg_print(ticker + ' at date ' + start_dt.strftime("%m/%d/%Y %H:%M:%S"))
    if tick_df.empty:
        print(ticker + ' df is empty for date ' + start_dt.strftime("%m/%d/%Y, %H:%M:%S"))
        return

    whole_day_data_d = whole_day_hloc(tick_df, t_delta=timedelta())
    pre_mkt_data_d = pre_market_hloc(tick_df, t_delta=timedelta())
    data_dict = data_dict | whole_day_data_d | pre_mkt_data_d


    # grab next pre-market data
    next_pre_mkt_data_d = pre_market_hloc(tick_df, t_delta=next_day_t_delta)
    next_pre_mkt_data_d = {"next" + '_' + k: v for k, v in next_pre_mkt_data_d.items()}
    data_dict = data_dict | next_pre_mkt_data_d

    # grab next day market data
    next_day_mkt_data_d = whole_day_hloc(tick_df, t_delta=next_day_t_delta)
    next_day_mkt_data_d = {"next_day" + '_' + k: v for k, v in next_day_mkt_data_d.items()}
    data_dict = data_dict | next_day_mkt_data_d

    # TODO: upload chart to google drive
    #image = graph_stock.plot_intraday(tick_df, ticker, date, strategy_name)
    #gfile = drive.CreateFile({'parents': [{'id': folder_ids[strategy_name]}]})
    ## Read file and set it as the content of this instance.
    #gfile.SetContentFile(image)
    #gfile.Upload()  # Upload the file.


    return data_dict

def get_intraday_ticks(ticker, start_date, end_date):
    if not isinstance(start_date, datetime.datetime):
        start_date = datetime.datetime.strptime(start_date, "%Y-%m-%d")
    if not isinstance(end_date, datetime.datetime):
        end_date = datetime.datetime.strptime(end_date, "%Y-%m-%d")

    aggs = cast(
        HTTPResponse,
        polygon_client.get_aggs(ticker, 1, "minute", start_date.date(), end_date.date(), raw=True),
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
        check_for_weekend, dt, t_delta = set_correct_date_if_the_weekend(dt, t_delta)
        check_for_holiday, dt, t_delta = is_next_prev_a_holiday(dt, next_or_prev_day, t_delta)

    return dt, t_delta


def get_daily_trade_count():
    return


def get_daily_volume_count():
    return


def get_premarket_volume_count():
    return

def get_day_and_max_3_year_dollar_volume(ticker,start_date_dt):
    end_date_dt = start_date_dt
    start_date_dt = end_date_dt - timedelta(days=3*365)
    # the daily vwap is accurate. Intraday needs to be computed by hand
    aggs = cast(
        HTTPResponse,
        polygon_client.get_aggs(ticker, 1, "day", start_date_dt, end_date_dt, raw=True),
    )

    ddict = json.loads(aggs.data.decode("utf-8"))
    stock_df = pd.DataFrame(ddict['results'])

    stock_df['dollar_volume'] = stock_df['vw'] * stock_df['v']
    day_dollar_volume = stock_df['dollar_volume'].iloc[-1]
    max_3_year_dollar_volume = stock_df['dollar_volume'].max()
    max_dollar_volume_ts = stock_df['t'].iloc[stock_df['dollar_volume'].idxmax()]
    max_3_year_dollar_volume_date = datetime.datetime.fromtimestamp(max_dollar_volume_ts/1000).strftime("%m/%d/%y")

    return day_dollar_volume, max_3_year_dollar_volume, max_3_year_dollar_volume_date

def compute_vwap(stock_df):
    stock_df['vcumsum'] = stock_df['v'].cumsum()
    stock_df['v*p'] = stock_df['v']*((stock_df['h']+stock_df['l']+stock_df['c'])/3)
    stock_df['vp_cumsum'] = stock_df['v*p'].cumsum()
    stock_df['vwap'] = stock_df['vp_cumsum']/stock_df['vcumsum']

    return stock_df


def hloc(frame, time_frame, t_delta, eastern_td):
    """ Returns:
        1. High
        2. Low
        3. Open
        4. Close
        5. High Time
        6. Low Time
        7. Volume
        8. $ Volume
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
    if time_frame[-1] == '00:59:00': # this conditional accounts for daylight savings
        dt_end = str(dt+timedelta(days=1)) + ' ' + time_frame[-1]
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
        hloc_d = hloc(frame, time_frame=['8:00:00', '13:29:59'], t_delta=t_delta, eastern_td=eastern_td)
    else:
        eastern_td = datetime.timedelta(hours=5)
        hloc_d = hloc(frame, time_frame=['9:00:00', '14:29:59'], t_delta=t_delta, eastern_td=eastern_td)

    hloc_d = {"pre_mkt" + '_' + k: v for k, v in hloc_d.items()}
    return hloc_d
def whole_day_hloc(frame, t_delta):
    """ Returns:
    1. High
    2. Low
    3. Open
    4. Close
    5. High Time
    6. Low Time
    8. Regular Hours Morning Volume
    9. Regular Hours Afternoon Volume
    10. Total Volume
    11. Morning High
    12. Morning Low
    13. Afternoon High
    14. Afternoon Low
    15. Morning High Time
    15. Morning Low Time
    15. Afternoon High Time
    15. Afternoon Low Time
    16. $ Volume
    """
    local_frame = frame.copy()
    # check for daylight savings time
    # if utilities.is_dst(self._frame['datetime'][0].date()+t_delta,pytz.timezone("US/Eastern")):
    if is_dst(datetime.datetime.fromtimestamp(local_frame['t'][0] / 1000) + t_delta, pytz.timezone("US/Eastern")):
        time_frame = ['8:00:00', '13:30:00', '16:00:00', '20:00:00', '23:59:00']
        eastern_td = datetime.timedelta(hours=4)
    else:
        time_frame = ['9:00:00', '14:30:00', '17:00:00', '21:00:00', '00:59:00']
        eastern_td = datetime.timedelta(hours=5)

    hloc_d = hloc(local_frame, time_frame, t_delta, eastern_td)
    # morning_df = hloc_d['df'][time_frame[0]:time_frame[1]]

    # unix time units
    dt_morning = str(hloc_d['df'].index[0].date()) + ' ' + time_frame[1] # regular mkt session
    dt_afternoon = str(hloc_d['df'].index[0].date()) + ' ' + time_frame[2] # regular mkt session
    dt_close = str(hloc_d['df'].index[0].date()) + ' ' + time_frame[3] # regular mkt session
    # date_format_str = '%Y-%m-%d %H:%M:%S'

    # make sure the date index exists. If it doesn't this means there wasn't any volume in that period so
    # we will go to the next minute
    # convert afternoon time_frame string into timedelta object incase we need to search for the next index
    morning_time_frame_td = datetime.datetime.strptime(time_frame[1], "%H:%M:%S")
    afternoon_time_frame_td = datetime.datetime.strptime(time_frame[2], "%H:%M:%S")
    close_time_frame_td = datetime.datetime.strptime(time_frame[3], "%H:%M:%S")

    m = 1
    while dt_morning not in hloc_d['df'].index:
        incremented_time = (morning_time_frame_td + datetime.timedelta(minutes=m)).time()
        dt_morning = str(hloc_d['df'].index[0].date()) + ' ' + str(incremented_time)
        m = m + 1
    m = 1
    while dt_afternoon not in hloc_d['df'].index:
        incremented_time = (afternoon_time_frame_td + datetime.timedelta(minutes=m)).time()
        dt_afternoon = str(hloc_d['df'].index[0].date()) + ' ' + str(incremented_time)
        m = m + 1
    m = 1
    while dt_close not in hloc_d['df'].index:
        incremented_time = (close_time_frame_td + datetime.timedelta(minutes=m)).time()
        dt_close = str(hloc_d['df'].index[0].date()) + ' ' + str(incremented_time)
        m = m + 1


    num_idx_morning = hloc_d['df'].index.get_loc(dt_morning)
    num_idx_afternoon = hloc_d['df'].index.get_loc(dt_afternoon)
    num_idx_close = hloc_d['df'].index.get_loc(dt_close)
    morning_frame = hloc_d['df'].iloc[num_idx_morning:num_idx_afternoon]
    afternoon_frame = hloc_d['df'].iloc[num_idx_afternoon:num_idx_close]

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

    if afternoon_frame.empty:
        hloc_d['afternoon_high'] = 'n/a'
        hloc_d['afternoon_low'] = 'n/a'
        hloc_d['afternoon_high_time'] = 'n/a'
        hloc_d['afternoon_low_time'] = 'n/a'
        hloc_d['afternoon_volume'] = 'n/a'
    else:
        hloc_d['afternoon_high'] = afternoon_frame['h'].max()
        hloc_d['afternoon_low'] = afternoon_frame['l'].min()
        hloc_d['afternoon_high_time'] = afternoon_frame['h'].idxmax()
        hloc_d['afternoon_low_time'] = afternoon_frame['l'].idxmin()
        hloc_d['afternoon_volume'] = afternoon_frame['v'].sum()
        hloc_d['afternoon_high_time'] = hloc_d['afternoon_high_time'] - eastern_td
        hloc_d['afternoon_low_time'] = hloc_d['afternoon_low_time'] - eastern_td

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