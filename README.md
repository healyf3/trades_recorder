**This repository is in charge of recording entry and exit points of trades made with
Cobra and Etrade brokers and placing them in a google spreadsheet for analysis.**

### File Description

#### avg_price.py

This script has been used for testing purposes. 
Input a trade file and print out the average execution for each side of the trade.
This file could probably be removed from the repository

#### etrade_recorder.py

This file could also be removed from the repository as it was just for testing the 
initial setup for etrade trade recording

#### file_utilities.py

This file includes all the functions needed to decipher between etrade and cobra
csv file format

*get_broker()*:
Gets broker ID according to file name

*get_date()*:
Gets date of trades from csv file name. Note that this could be optimized down
the road for etrade trades as the file comes with the actual dates. For now, the 
recorder will just have the same format as we record with cobra trades as those don't have
the date (only time) in the csv files.

*trades_csv_to_df()*:
This function translates the csv info to a dataframe. If the broker is Etrade then
the csv information is parsed to match Cobra csv file formatting, so there aren't any
discrepancies with the data frame data

*export_trades_df_to_csv()*:
When a csv sort is needed (usually when two separate trades have been made on the
same ticker in the same csv file because Cobra's csv file doesn't sort the time
already), this function will make a new csv file that is sorted by time. Trades can
then be easily separated

*convert24()*:
Used for etrade csv files, and translates to military time to match Cobra csv
formatting

#### grab_holiday_dates.py
WIP: This may not be needed, but the idea is to grab correct data from the previous
market day. If the date is a holiday, the script needs to know to grab the data from
the last open day

#### hloc_utilities.py
WIP: This file will be incharge of grabbing the high, low, open, close of different
parts of the trade's day as well as it's previous day and next day

#### scrape_utilies.py
This file will be incharge of scraping the float, market cap, and sector of each
ticker

#### service_account.json
This is the information needed to work with the gspread api. Credentials will need
to be generated on of Google Cloud Console. The following steps are provided on
this gspread authentication page:
https://docs.gspread.org/en/latest/oauth2.html#enable-api-access-for-a-project

#### sort_trade_times_and_export_csv.py
This file has just been used for testing the df to csv export. Can probably be
removed.

#### trades_recorder.py
In charge of computing the following information and placing in google spreadsheet
for each trade.

* Current Spreadsheet Info
*   Date
*   Ticker
*   Strategy
*   Feeling	Confidence(1-10)
*   Frustration(1-10)
*   Notes
*   News Day After
*   Dilution Risk
*   Run Reason
*   Try No.	Adds
*   Risk
*   Side
*   Entry Shares
*   Exit Shares
*   Reward
*   RR
*   Avg Entry
*   Price
*   Avg Exit Price
*   First Entry Time
*   Last Entry Time
*   Ideal Entry Time
*   Ideal Entry Price
*   First Exit Time
*   Last Exit Time
*   Ideal Exit Time
*   Ideal Exit Price
*   $ Volume
*   Max 3 Year $ Volume
*   % Gain/Loss
*   $ Gain
*   Float
*   Market Cap
*   Sector
*   % Open Gain

#### trading_charts_folder_ids.py
WIP: For each trade, gather data in polygon to form a 3 year chart, and a 2 day 
chart into one picture and place in a folder so the trader can go back and review
trades.

#### util.py
*dbg_print()*:
Checks static flag to decide whether or not to print to the console