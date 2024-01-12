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

def plot_intraday(frame, ticker, date, buys, sells, strategy_name=None, risk=None, avg_entry=None, avg_exit=None,
                  right=None, wrong=None, cont=None):
    stock_df = frame.copy()
    stock_df['datetime'] = stock_df.t.apply(lambda x: datetime.datetime.fromtimestamp(x / 1000).astimezone(pytz.timezone('UTC')))
    stock_df['datetime'] = stock_df['datetime'].dt.tz_convert('US/Eastern')
    time = stock_df['datetime'].tolist()

    #determine vwap
    stock_df = hloc_utilities.compute_vwap(stock_df)

    # Find high and low points
    #d = .02
    #stock_df["marker"] = np.where(stock_df["open"] < stock_df["close"], stock_df["high"] + d, stock_df["low"] - d)
    #stock_df["symbol"] = np.where(stock_df["open"] < stock_df["close"], "triangle-down", "triangle-up")
    #stock_df["color"] = np.where(stock_df["open"] < stock_df["close"], "green", "red")
    high_point = [stock_df['datetime'][stock_df['h'].idxmax()],stock_df['h'].max()]
    low_point = [stock_df['datetime'][stock_df['l'].idxmin()],stock_df['l'].min()]

    fig = make_subplots(specs=[[{"secondary_y": True}]])
    fig.add_trace(go.Candlestick(x=stock_df['datetime'],
                    open=stock_df['o'],
                    high=stock_df['h'],
                    low=stock_df['l'],
                    close=stock_df['c'],
                    showlegend=False),
                  secondary_y=True)
    fig.add_trace(go.Scatter(x=stock_df['datetime'], y=stock_df['v'], marker=dict(color="pink"), showlegend=False), secondary_y=False)
    #fig.add_trace(go.Bar(x=stock_df['datetime'], y=stock_df['v'], marker=dict(color="pink"), showlegend=False), secondary_y=False)
    #fig.update_layout(bargap=0.9, autosize=True, barmode='group')
    #fig.update_traces(width=1000*3600*24*0.8)

    if buys != None:
            for i in buys:
                dt_str = i[0] + ' ' + i[1]
                dt = datetime.datetime.strptime(dt_str, "%m/%d/%y %H:%M")
                fig.add_trace(
                    go.Scatter(x=[dt], y=[i[5]], showlegend=False,
                               marker=go.scatter.Marker(size=12, symbol=['triangle-up'], color='#74F478')),
                    secondary_y=True)
    if sells != None:
        for i in sells:
            dt_str = i[0] + ' ' + i[1]
            dt = datetime.datetime.strptime(dt_str, "%m/%d/%y %H:%M")
            fig.add_trace(
                go.Scatter(x=[dt], y=[i[5]], showlegend=False,
                           marker=go.scatter.Marker(size=12, symbol=['triangle-down'], color='#791004')),
                secondary_y=True)

    fig.add_trace(go.Scatter(x=[low_point[0],high_point[0]],y=[low_point[1],high_point[1]], mode='markers+text',
                             text=['low','high'],textposition='top center', showlegend=False,
                             marker=go.scatter.Marker(size=8, symbol=['triangle-up', 'triangle-down'], color='Blue')),
                        secondary_y=True)

    # fig.add_vline(x=time[ticker_index_width=0.6, line_color='white')
    fig.add_trace(go.Scatter(x=stock_df['datetime'], y=stock_df['vwap'], mode='lines', name='VWAP',
                             marker=go.scatter.Marker(color='Purple')),
                            secondary_y=True)

    #fig.add_trace(go.Scatter(x=stock_df['datetime'], y=stock_df['marker'], mode='markers', name='markers',
    #                         marker=go.scatter.Marker(size=5, symbol=stock_df['symbol'], color=stock_df['color'])), secondary_y=True)

    fig.layout.yaxis2.showgrid=False

    fig.update_layout(xaxis_rangeslider_visible=False, template='plotly_dark')
    #fig.update_layout(xaxis_rangeslider_visible=False)
    fig.update_xaxes(rangebreaks=[dict(bounds=["sat", "mon"]),  # hide weekends, eg. hide sat to before mon
                               dict(bounds=[20, 4], pattern="hour")])


    pm_ext_open_hours = ["09:30:00", "19:59:00","16:00:00"]
    for x in time:
        time_str = x.strftime('%H:%M:%S')
        if not any(x in time_str for x in pm_ext_open_hours):
        #if "16:00:00" not in time_str:
                continue
        fig.add_vline(x=x, line_width=0.6, line_color='white', line_dash='dash')



    fig.update_yaxes(title='Volume', secondary_y=False)
    fig.update_yaxes(title='Price', secondary_y=True)

 #   fig.add_annotation(
 #       x=5, y=35,  # Text annotation position
 #       xref="x", yref="y",  # Coordinate reference system
 #       text='Test',  # Text content
 #       showarrow=False  # Hide arrow
 #   )

    if risk != None or avg_entry != None or avg_exit != None or right != None or wrong != None or cont != None:
        fig.add_annotation(dict(font=dict(color='yellow', size=15),
                                x=-0.1,
                                y=-0.22,
                                showarrow=False,
                                text='Risk: ' + str(risk),
                                textangle=0,
                                xanchor='left',
                                xref="paper",
                                yref="paper"))

        fig.add_annotation(dict(font=dict(color='yellow', size=15),
                                x=0.2,
                                y=-0.22,
                                showarrow=False,
                                text='Avg Entry: ' + str(avg_entry),
                                textangle=0,
                                xanchor='left',
                                xref="paper",
                                yref="paper"))

        fig.add_annotation(dict(font=dict(color='yellow', size=15),
                                x=0.6,
                                y=-0.22,
                                showarrow=False,
                                text='Avg Exit: ' + str(avg_exit),
                                textangle=0,
                                xanchor='left',
                                xref="paper",
                                yref="paper"))

        fig.add_annotation(dict(font=dict(color='Green', size=15),
                                x=0.2,
                                y=1.2,
                                showarrow=False,
                                text="Right: " + right,
                                textangle=0,
                                xanchor='left',
                                xref="paper",
                                yref="paper"))

        fig.add_annotation(dict(font=dict(color='Red', size=15),
                                x=0.2,
                                y=1.15,
                                showarrow=False,
                                text="Wrong: " + wrong,
                                textangle=0,
                                xanchor='left',
                                xref="paper",
                                yref="paper"))

        fig.add_annotation(dict(font=dict(color='Orange', size=15),
                                x=0.2,
                                y=1.1,
                                showarrow=False,
                                text="Continue: " + cont,
                                textangle=0,
                                xanchor='left',
                                xref="paper",
                                yref="paper"))


    fig.update_layout(title=go.layout.Title(
        text=ticker + f"<br><sup>Strat: {strategy_name}</sup>"
    ))

    #fig.show()
    if strategy_name is not None:
        image_name = ticker + '_' + strategy_name + "_" + date.strftime("%Y-%m-%d") + '_' + 'intraday' + '.png'
    else:
        image_name = ticker + "_" + date.strftime("%Y-%m-%d") + '_' + 'intraday' + '.png'

    image_path = 'graphs/' + image_name
    fig.write_image(image_path, format='png', scale=15)
    return image_path


def plot_daily(frame, ticker, date, strategy_name=None):
    stock_df = frame.copy()
    stock_df['datetime'] = stock_df.t.apply(lambda x: datetime.datetime.fromtimestamp(x / 1000).astimezone(pytz.timezone('UTC')))
    stock_df['datetime'] = stock_df['datetime'].dt.tz_convert('US/Eastern')
    time = stock_df['datetime'].tolist()

    # Find high and low points
    #d = .02
    #stock_df["marker"] = np.where(stock_df["open"] < stock_df["close"], stock_df["high"] + d, stock_df["low"] - d)
    #stock_df["symbol"] = np.where(stock_df["open"] < stock_df["close"], "triangle-down", "triangle-up")
    #stock_df["color"] = np.where(stock_df["open"] < stock_df["close"], "green", "red")
    high_point = [stock_df['datetime'][stock_df['h'].idxmax()],stock_df['h'].max()]
    low_point = [stock_df['datetime'][stock_df['l'].idxmin()],stock_df['l'].min()]

    fig = make_subplots(specs=[[{"secondary_y": True}]])
    fig.add_trace(go.Candlestick(x=stock_df['datetime'],
                                 open=stock_df['o'],
                                 high=stock_df['h'],
                                 low=stock_df['l'],
                                 close=stock_df['c'],
                                 showlegend=False),
                  secondary_y=True)
    fig.add_trace(go.Bar(x=stock_df['datetime'], y=stock_df['v'], marker=dict(color="pink"), showlegend=False), secondary_y=False)

    fig.add_trace(go.Scatter(x=[low_point[0],high_point[0]],y=[low_point[1],high_point[1]], mode='markers+text',
                             text=['low','high'],textposition='top center', showlegend=False,
                             marker=go.scatter.Marker(size=8, symbol=['triangle-up', 'triangle-down'], color='Blue')),
                  secondary_y=True)

    # fig.add_vline(x=time[ticker_index_width=0.6, line_color='white')
    #fig.add_trace(go.Scatter(x=stock_df['datetime'], y=stock_df['vw'], mode='lines', name='VWAP'), secondary_y=True)
    #fig.add_trace(go.Scatter(x=stock_df['datetime'], y=stock_df['marker'], mode='markers', name='markers',
    #                         marker=go.scatter.Marker(size=5, symbol=stock_df['symbol'], color=stock_df['color'])), secondary_y=True)

    fig.layout.yaxis2.showgrid=False

    fig.update_layout(xaxis_rangeslider_visible=False, template='plotly_dark')
    fig.update_xaxes(rangebreaks=[dict(bounds=["sat", "mon"])])  # hide weekends, eg. hide sat to before mon


    pm_ext_open_hours = ["09:30:00", "19:59:00","16:00:00"]
    for x in time:
        time_str = x.strftime('%H:%M:%S')
        if not any(x in time_str for x in pm_ext_open_hours):
            #if "16:00:00" not in time_str:
            continue
        fig.add_vline(x=x, line_width=0.6, line_color='white', line_dash='dash')

    fig.update_yaxes(title='Volume', secondary_y=False)
    fig.update_yaxes(title='Price', secondary_y=True)
    fig.update_layout(title=ticker)
    #fig.show()
    if strategy_name is not None:
        image_name = ticker + '_' + strategy_name + "_" + date.strftime("%Y-%m-%d") + '_' + 'daily' + '.png'
    else:
        image_name = ticker + "_" + date.strftime("%Y-%m-%d") + '_' + 'daily' + '.png'

    image_path = 'graphs/' + image_name

    fig.write_image(image_path, format='png', scale=15)
    return image_path

def graph_stock(ticker, start_date, end_date, strategy, gspread_worksheet, buys, sells, risk=None,
                avg_entry=None, avg_exit=None, right=None, wrong=None, cont=None):
    intraday_frame = hloc_utilities.get_intraday_ticks(ticker, start_date, end_date)
    daily_frame = hloc_utilities.get_daily_ticks(ticker, 5, start_date)

    intraday_image = plot_intraday(intraday_frame, ticker, start_date, buys, sells, strategy_name=strategy,
                                   risk=risk, right=right, wrong=wrong, cont=cont)
    daily_image = plot_daily(daily_frame, ticker, start_date, strategy_name=strategy)

    image_list = [daily_image, intraday_image]
    images = [Image.open(x) for x in image_list]
    widths, heights = zip(*(i.size for i in images))

    total_width = sum(widths)
    max_height = max(heights)

    new_im = Image.new('RGB', (total_width, max_height))

    x_offset = 0
    for im in images:
        new_im.paste(im, (x_offset, 0))
        x_offset += im.size[0]

    image_name = ticker + '_' + start_date + '_' + end_date + '.png'
    new_im.save('graphs/' + image_name)

    # only upload files that don't exist
    folder_str = "'{}' in parents and trashed=false".format(folder_ids[strategy])
    file_list = drive.ListFile({'q': folder_str}).GetList()
    file_exists = False
    os.chdir('graphs/')
    for file in file_list:
        if file['title'] == image_name:
            file_exists = True
            gfile = drive.CreateFile({'parents': [{'id': folder_ids[strategy]}], 'id': file['id']})
            gfile.FetchContent()
            break

    # If file doesn't exist, read file and set it as the content of this instance.
    if not file_exists:
        gfile = drive.CreateFile({'parents': [{'id': folder_ids[strategy]}]})
        gfile.SetContentFile(image_name)
        gfile.Upload()  # Upload the file.

    os.chdir('../')

    result = [gfile.get('alternateLink')]

    #gspread_worksheet.append_row(values=result, table_range=empty_start_column + str((ticker[2])))
    gspread_worksheet.append_row(values=result)


#worksheet_test = util.get_gspread_worksheet(config_object['main']['GSPREAD_SPREADSHEET'], 'ttest')
#graph_stock('VVOS', '2023-11-29', '2023-11-29', 'test',worksheet_test, sells=None, buys=None)
