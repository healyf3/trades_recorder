import plotly.graph_objects as go
from plotly.subplots import make_subplots
import datetime
import pytz
import hloc_utilities
from PIL import Image
import os

from pydrive.auth import GoogleAuth
from pydrive.auth import ServiceAccountCredentials
from pydrive.drive import GoogleDrive

gauth = GoogleAuth()
scope = ['https://www.googleapis.com/auth/drive']
gauth.credentials = ServiceAccountCredentials.from_json_keyfile_name(
    os.path.expanduser('~/.config/gspread/service_account.json'), scope)
drive = GoogleDrive(gauth)

from configparser import ConfigParser
from trading_charts_folder_ids import folder_ids
import util

# Grab configuration values.
config_object = ConfigParser()
config_object.read("config/config.ini")

IMAGE_PATH = 'graphs/'


def plot_intraday(frame, ticker, date, buys, sells, strategy_name=None, risk=None, avg_entry=None, avg_exit=None,
                  entry_time=None, exit_time=None, trade_side=None,
                  right=None, wrong=None, cont=None):
    gain_perc = None
    if avg_exit is not None and avg_exit != "":
        if trade_side == 'B':
            gain_perc = (avg_exit - avg_entry) / avg_entry
        elif trade_side == 'SS':
            gain_perc = (avg_entry - avg_exit) / avg_entry

        gain_perc = round(gain_perc * 100, 2)

    stock_df = frame.copy()
    stock_df['datetime'] = stock_df.t.apply(
        lambda x: datetime.datetime.fromtimestamp(x / 1000).astimezone(pytz.timezone('UTC')))
    stock_df['datetime'] = stock_df['datetime'].dt.tz_convert('US/Eastern')
    time = stock_df['datetime'].tolist()

    # determine vwap
    stock_df = hloc_utilities.compute_vwap(stock_df)

    # Find high and low points
    # d = .02
    # stock_df["marker"] = np.where(stock_df["open"] < stock_df["close"], stock_df["high"] + d, stock_df["low"] - d)
    # stock_df["symbol"] = np.where(stock_df["open"] < stock_df["close"], "triangle-down", "triangle-up")
    # stock_df["color"] = np.where(stock_df["open"] < stock_df["close"], "green", "red")
    high_point = [stock_df['datetime'][stock_df['h'].idxmax()], stock_df['h'].max()]
    low_point = [stock_df['datetime'][stock_df['l'].idxmin()], stock_df['l'].min()]

    # fig = make_subplots(specs=[[{"secondary_y": True}]])
    fig = make_subplots(rows=2, cols=1, row_heights=[0.9, 0.1])
    fig.add_trace(go.Candlestick(x=stock_df['datetime'],
                                 open=stock_df['o'],
                                 high=stock_df['h'],
                                 low=stock_df['l'],
                                 close=stock_df['c'],
                                 showlegend=False), row=1, col=1)

    # fig.add_trace(go.Bar(x=stock_df['datetime'], y=stock_df['v'], marker=dict(color="pink"), showlegend=False), secondary_y=False)
    fig.add_trace(go.Bar(x=stock_df['datetime'], y=stock_df['v'], marker=dict(color="pink"), showlegend=False), row=2,
                  col=1)
    # fig.add_trace(go.Bar(x=stock_df['datetime'], y=stock_df['v'], marker=dict(color="pink"), showlegend=False), secondary_y=False)
    # fig.update_layout(bargap=0.9, autosize=True, barmode='group')
    # fig.update_traces(width=1000*3600*24*0.8)

    if buys != None:
        for i in buys:
            dt_str = i['date'] + ' ' + i['time']
            dt = datetime.datetime.strptime(dt_str, "%m/%d/%y %H:%M")
            fig.add_trace(
                go.Scatter(x=[dt], y=[i['price']], showlegend=False,
                           marker=go.scatter.Marker(size=15, symbol=['triangle-up'], color='#74F478')),
                secondary_y=True)
    if sells != None:
        for i in sells:
            dt_str = i['date'] + ' ' + i['time']
            dt = datetime.datetime.strptime(dt_str, "%m/%d/%y %H:%M")
            fig.add_trace(
                go.Scatter(x=[dt], y=[i['price']], showlegend=False,
                           marker=go.scatter.Marker(size=15, symbol=['triangle-down'], color='#951D0F')),
                secondary_y=True)

    fig.add_trace(go.Scatter(x=[low_point[0], high_point[0]], y=[low_point[1], high_point[1]], mode='markers+text',
                             text=['low', 'high'], textfont=dict(size=25), textposition='top center', showlegend=False,
                             marker=go.scatter.Marker(size=25, symbol=['triangle-up', 'triangle-down'], color='Blue')),
                  row=1, col=1)

    # fig.add_vline(x=time[ticker_index_width=0.6, line_color='white')
    fig.add_trace(go.Scatter(x=stock_df['datetime'], y=stock_df['vwap'], mode='lines', name='VWAP',
                             marker=go.scatter.Marker(color='Purple')),
                  row=1, col=1)

    # fig.add_trace(go.Scatter(x=stock_df['datetime'], y=stock_df['marker'], mode='markers', name='markers',
    #                         marker=go.scatter.Marker(size=5, symbol=stock_df['symbol'], color=stock_df['color'])), secondary_y=True)

    fig.layout.yaxis2.showgrid = False

    fig.update_layout(width=2000, xaxis_rangeslider_visible=False, template='plotly_dark')
    # fig.update_layout(xaxis_rangeslider_visible=False)
    fig.update_xaxes(rangebreaks=[dict(bounds=["sat", "mon"]),  # hide weekends, eg. hide sat to before mon
                                  dict(bounds=[20, 4], pattern="hour")])

    pm_ext_open_hours = ["09:30:00", "19:59:00", "16:00:00"]
    for x in time:
        time_str = x.strftime('%H:%M:%S')
        if not any(x in time_str for x in pm_ext_open_hours):
            # if "16:00:00" not in time_str:
            continue
        fig.add_vline(x=x, line_width=0.6, line_color='white', line_dash='dash')

    fig.update_yaxes(title='Price', title_font=dict(size=40), row=1)
    fig.update_yaxes(title='Volume', title_font=dict(size=40), row=2)

    #   fig.add_annotation(
    #       x=5, y=35,  # Text annotation position
    #       xref="x", yref="y",  # Coordinate reference system
    #       text='Test',  # Text content
    #       showarrow=False  # Hide arrow
    #   )

    if risk != None or avg_entry != None or avg_exit != None or right != None or wrong != None or cont != None \
            or entry_time != None or exit_time != None:
        fig.add_annotation(dict(font=dict(color='yellow', size=15),
                                x=-0.15,
                                y=-0.16,
                                showarrow=False,
                                text='Gain%: ' + str(gain_perc),
                                textangle=0,
                                xanchor='left',
                                xref="paper",
                                yref="paper"))

        fig.add_annotation(dict(font=dict(color='yellow', size=15),
                                x=-0.15,
                                y=-0.22,
                                showarrow=False,
                                text='Risk: ' + str(risk),
                                textangle=0,
                                xanchor='left',
                                xref="paper",
                                yref="paper"))

        fig.add_annotation(dict(font=dict(color='yellow', size=15),
                                x=0.10,
                                y=-0.22,
                                showarrow=False,
                                text='Avg Entry: ' + str(avg_entry),
                                textangle=0,
                                xanchor='left',
                                xref="paper",
                                yref="paper"))

        fig.add_annotation(dict(font=dict(color='yellow', size=15),
                                x=0.7,
                                y=-0.22,
                                showarrow=False,
                                text='Avg Exit: ' + str(avg_exit),
                                textangle=0,
                                xanchor='left',
                                xref="paper",
                                yref="paper"))

        fig.add_annotation(dict(font=dict(color='yellow', size=15),
                                x=0.1,
                                y=-0.16,
                                showarrow=False,
                                text='Entry Time: ' + str(entry_time),
                                textangle=0,
                                xanchor='left',
                                xref="paper",
                                yref="paper"))

        fig.add_annotation(dict(font=dict(color='yellow', size=15),
                                x=0.7,
                                y=-0.16,
                                showarrow=False,
                                text='Exit Time: ' + str(exit_time),
                                textangle=0,
                                xanchor='left',
                                xref="paper",
                                yref="paper"))

        fig.add_annotation(dict(font=dict(color='Green', size=8),
                                x=0.2,
                                y=1.2,
                                showarrow=False,
                                text="Right: " + right,
                                textangle=0,
                                xanchor='left',
                                xref="paper",
                                yref="paper"))

        fig.add_annotation(dict(font=dict(color='Red', size=8),
                                x=0.2,
                                y=1.15,
                                showarrow=False,
                                text="Wrong: " + wrong,
                                textangle=0,
                                xanchor='left',
                                xref="paper",
                                yref="paper"))

        fig.add_annotation(dict(font=dict(color='Orange', size=8),
                                x=0.2,
                                y=1.1,
                                showarrow=False,
                                text="Continue: " + cont,
                                textangle=0,
                                xanchor='left',
                                xref="paper",
                                yref="paper"))

    fig.update_layout(title=go.layout.Title(
        text=ticker + f"<br><sup>Strat: {strategy_name}</sup>", font=dict(size=50)),
        yaxis=dict(tickfont=dict(size=30)),
        yaxis2=dict(tickfont=dict(size=30)),
        xaxis=dict(showticklabels=False),
        xaxis2=dict(tickfont=dict(size=30)),
        legend=dict(font=dict(size=25)),
    )

    #fig.show() # for debugging only
    if strategy_name is not None:
        image_name = ticker + '_' + strategy_name + "_" + date.strftime("%Y-%m-%d") + '_' + 'intraday' + '.png'
    else:
        image_name = ticker + "_" + date.strftime("%Y-%m-%d") + '_' + 'intraday' + '.png'

    # fig.write_image(image_path, format='png', scale=15)
    fig.write_image(IMAGE_PATH+image_name, format='png', height=2000, width=4000, scale=2)
    return image_name


def plot_daily(frame, ticker, date, strategy_name=None):
    stock_df = frame.copy()
    stock_df['datetime'] = stock_df.t.apply(
        lambda x: datetime.datetime.fromtimestamp(x / 1000).astimezone(pytz.timezone('UTC')))
    stock_df['datetime'] = stock_df['datetime'].dt.tz_convert('US/Eastern')
    time = stock_df['datetime'].tolist()

    # Find high and low points
    # d = .02
    # stock_df["marker"] = np.where(stock_df["open"] < stock_df["close"], stock_df["high"] + d, stock_df["low"] - d)
    # stock_df["symbol"] = np.where(stock_df["open"] < stock_df["close"], "triangle-down", "triangle-up")
    # stock_df["color"] = np.where(stock_df["open"] < stock_df["close"], "green", "red")
    high_point = [stock_df['datetime'][stock_df['h'].idxmax()], stock_df['h'].max()]
    low_point = [stock_df['datetime'][stock_df['l'].idxmin()], stock_df['l'].min()]

    fig = make_subplots(rows=2, cols=1, row_heights=[0.9, 0.1])
    fig.add_trace(go.Candlestick(x=stock_df['datetime'],
                                 open=stock_df['o'],
                                 high=stock_df['h'],
                                 low=stock_df['l'],
                                 close=stock_df['c'],
                                 showlegend=False), row=1, col=1)

    fig.add_trace(go.Bar(x=stock_df['datetime'], y=stock_df['v'], marker=dict(color="pink"), showlegend=False), row=2,
                  col=1)

    fig.add_trace(go.Scatter(x=[low_point[0], high_point[0]], y=[low_point[1], high_point[1]], mode='markers+text',
                             text=['low', 'high'], textposition='top center', showlegend=False,
                             marker=go.scatter.Marker(size=18, symbol=['triangle-up', 'triangle-down'], color='Blue')),
                  row=1, col=1)

    # fig.add_vline(x=time[ticker_index_width=0.6, line_color='white')
    # fig.add_trace(go.Scatter(x=stock_df['datetime'], y=stock_df['vw'], mode='lines', name='VWAP'), secondary_y=True)
    # fig.add_trace(go.Scatter(x=stock_df['datetime'], y=stock_df['marker'], mode='markers', name='markers',
    #                         marker=go.scatter.Marker(size=5, symbol=stock_df['symbol'], color=stock_df['color'])), secondary_y=True)

    fig.layout.yaxis2.showgrid = False

    fig.update_layout(xaxis_rangeslider_visible=False, template='plotly_dark')
    fig.update_xaxes(rangebreaks=[dict(bounds=["sat", "mon"])])  # hide weekends, eg. hide sat to before mon

    pm_ext_open_hours = ["09:30:00", "19:59:00", "16:00:00"]
    for x in time:
        time_str = x.strftime('%H:%M:%S')
        if not any(x in time_str for x in pm_ext_open_hours):
            # if "16:00:00" not in time_str:
            continue
        fig.add_vline(x=x, line_width=0.6, line_color='white', line_dash='dash')

    fig.update_yaxes(title='Price', title_font=dict(size=40), row=1)
    fig.update_yaxes(title='Volume', title_font=dict(size=40), row=2)

    fig.update_layout(title=go.layout.Title(
        text=ticker + f"<br><sup>Strat: {strategy_name}</sup>", font=dict(size=50)),
        yaxis=dict(tickfont=dict(size=30)),
        yaxis2=dict(tickfont=dict(size=30)),
        xaxis=dict(showticklabels=False),
        xaxis2=dict(tickfont=dict(size=30)),
    )

    # fig.show() # for debugging only
    if strategy_name is not None:
        image_name = ticker + '_' + strategy_name + "_" + date.strftime("%Y-%m-%d") + '_' + 'daily' + '.png'
    else:
        image_name = ticker + "_" + date.strftime("%Y-%m-%d") + '_' + 'daily' + '.png'

    fig.write_image(IMAGE_PATH+image_name, format='png', height=2000, width=4000, scale=2)
    return image_name


def graph_stock(ticker, start_date, end_date, strategy, buys=None, sells=None, risk=None,
                avg_entry=None, avg_exit=None, entry_time=None, exit_time=None, trade_side=None,
                right=None, wrong=None, cont=None):
    intraday_frame = hloc_utilities.get_intraday_ticks(ticker, start_date, end_date)
    daily_frame = hloc_utilities.get_daily_ticks(ticker, 5, start_date)

    intraday_image = plot_intraday(intraday_frame, ticker, start_date, buys, sells, strategy_name=strategy,
                                   avg_entry=avg_entry, avg_exit=avg_exit, entry_time=entry_time, exit_time=exit_time,
                                   trade_side=trade_side,
                                   risk=risk, right=right, wrong=wrong, cont=cont)
    daily_image = plot_daily(daily_frame, ticker, start_date, strategy_name=strategy)

    image_list = [intraday_image,daily_image]


    if isinstance(start_date, datetime.datetime):
        start_date = start_date.strftime("%Y-%m-%d")
    if isinstance(end_date, datetime.datetime):
        end_date = end_date.strftime("%Y-%m-%d")

    # only upload files that don't exist
    folder_str = "'{}' in parents and trashed=false".format(folder_ids[strategy])
    file_list = drive.ListFile({'q': folder_str}).GetList()
    os.chdir(IMAGE_PATH)
    for file in file_list:
        for img in image_list:
            if file['title'] == img:
                file.Trash()

    for img in image_list:
        gfile = drive.CreateFile({'parents': [{'id': folder_ids[strategy]}]})
        gfile.SetContentFile(img)
        gfile.Upload()  # Upload the file.
    os.chdir('../')


    result = [gfile.get('alternateLink')]

    # gspread_worksheet.append_row(values=result, table_range=empty_start_column + str((ticker[2])))
    # gspread_worksheet.append_row(values=result)
    return result


worksheet_test = util.get_gspread_worksheet(config_object['main']['GSPREAD_SPREADSHEET'], 'ttest')
#graph_stock('ENSC', datetime.datetime(year=2024, month=1, day=31), datetime.datetime(year=2024, month=1, day=31),
#            'test', sells=None, buys=None)
