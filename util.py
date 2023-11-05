import os
import re
from datetime import datetime
import pandas as pd
import csv
import sys
import gspread
from configparser import ConfigParser


config_object = ConfigParser()
config_object.read("config/config.ini")
DEBUG_PRINT = config_object['main']['DEBUG_PRINT']

def dbg_print(string):
    if DEBUG_PRINT:
        print(string)

def get_gspread_worksheet(spreadsheet_name):
    # Setup Google Sheets Connection
    gc = gspread.service_account()
    sh = gc.open(spreadsheet_name)
    # Params
    return sh.worksheet(spreadsheet_name)


def get_gspread_worksheet_values(worksheet):
    # Get all values from the worksheet and store in a dictionary and search for data that way. This reduces the amount
    # of API calls since there is a limit of 300 requests per minute per project and 60 requests per minute per user
    return worksheet.get_all_records()


# These functions use the csv naming convention of <broker>-<date>_<optional_description>.csv
def get_broker(trades_file):
    return os.path.basename(trades_file).split('-')[0]


def get_date(trades_file):
    broker = get_broker(trades_file)

    csv_file_date = re.split('_|\.', os.path.basename(trades_file).split(broker + '-')[1])[0]
    return datetime.strptime(csv_file_date, '%m-%d-%y')


# Read csv file into pandas dataframe
def trades_csv_to_df(trades_file):
    broker = get_broker(trades_file)
    if broker == 'etrade':
        csv_df = pd.DataFrame(columns=["Date", "Time", "Side", "Qty", "Symb", "Price"])

        with open(trades_file, "r") as f:
            # reader = csv.reader(f, delimiter="\t")
            reader = csv.reader(f)
            for i, line in enumerate(reader):
                # line list
                ll = line[0].replace('\t\t', ',').replace(' ', ',').split(",")
                # don't read cancelled or pending entries
                if ll[0].isspace() or ll[-3] != 'Executed':
                    continue
                # join time and AM/PM
                ll[1:3] = [' '.join(ll[1:3])]
                # convert to military to be consistent with cobra
                ll[1] = convert24(ll[1])
                # remove tabs from copy and pasted line
                ll[0] = ll[0].replace('\t', '')
                # remove the dollar sign and tabs
                ll[-1] = ll[-1].replace('$', '').replace('\t', '')
                # ll[0] -> Date
                # ll[1] -> Time
                # ll[3] -> Type
                # ll[4] -> Qty
                # ll[5] -> Symb
                # ll[-1] -> Price
                # csv_df_list[0] -> Date
                # csv_df_list[1] -> Time
                # csv_df_list[2] -> Type
                # csv_df_list[3] -> Qty
                # csv_df_list[4] -> Symb
                # csv_df_list[5] -> Price
                if 'Buy' == ll[3]: ll[3] = 'B'  # So it's consistent with Cobra's naming convention
                if 'Sell' == ll[3]: ll[3] = 'S'  # So it's consistent with Cobra's naming convention

                # For option trades
                if 'Call' in ll or 'Put' in ll:
                    ll[4] = 100 * int(ll[4])
                csv_df_list = [ll[0], ll[1], ll[3], int(ll[4]), ll[5], float(ll[-1])]
                csv_df.loc[len(csv_df)] = csv_df_list

    elif broker == 'cobra':
        csv_df = pd.read_csv(trades_file)
    else:
        print("wrong csv file name format")
        sys.exit()

    return csv_df


def export_trades_df_to_csv(df, trades_file, description):
    csv_idx = trades_file.index(".csv")
    df.to_csv(trades_file[:csv_idx] + '_' + description + '.csv', index=False)


def convert24(str1):
    # Checking if last two elements of time
    # is AM and first two elements are 12
    if str1[-2:] == "AM" and str1[:2] == "12":
        return "00" + str1[2:-3]

    # remove the AM
    elif str1[-2:] == "AM":
        return str1[:-3]

    # Checking if last two elements of time
    # is PM and first two elements are 12
    elif str1[-2:] == "PM" and str1[:2] == "12":
        return str1[:-3]

    else:

        # add 12 to hours and remove PM
        return str(int(str1[:2]) + 12) + str1[2:5]

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