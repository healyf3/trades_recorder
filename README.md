**This repository is in charge of recording entry and exit points of trades made with
Cobra and E-trade brokers and placing them in a Google spreadsheet for analysis.**

### Current Gspread data

Raw data filled out by the user
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

Data Computed in Google Spread after trades_recorder.py runs
* % Gain/Loss
* $ Gain
* RR
* Trade Duration

Data computed from *trades_recorder.py*

### File Description

#### avg_price.py

This script has been used for testing purposes.
Input a trade file and print out the average execution for each side of the trade.
This file could probably be removed from the repository

#### util.py

This file includes all the functions needed to decipher between E-trade and cobra csv file format

*get_broker()*:
Gets broker ID according to file name

*get_date()*:
Gets date of trades from csv file name. Note that this could be optimized down
the road for E-trade trades as the file comes with the actual dates. For now, the
recorder will just have the same format as we record with cobra trades as those don't have
the date (only time) in the csv files.

*trades_csv_to_df()*:
This function translates the csv info to a dataframe. If the broker is E-trade then
the csv information is parsed to match Cobra csv file formatting, so there aren't any
discrepancies with the data frame data

*export_trades_df_to_csv()*:
When a csv sort is needed (usually when two separate trades have been made on the
same ticker in the same csv file because Cobra's csv file does not sort the time
already), this function will make a new csv file that is sorted by time. Trades can
then be easily separated

*convert24()*:
Used for E-trade csv files, and translates to military time to match Cobra csv
formatting

#### grab_holiday_dates.py
WIP: This may not be needed, but the idea is to grab correct data from the previous
market day. If the date is a holiday, the script needs to know to grab the data from
the last open day

#### hloc_utilities.py
WIP: This file will be incharge of grabbing the high, low, open, close of different
parts of the trade's day as well as its previous day and next day

#### scrape_utilities.py
This file will be incharge of scraping the float, market cap, and sector of each
ticker

#### service_account.json (This file isn't provided in the remote repo. You must add it locally)
This is the information needed to work with the gspread api. Credentials will need
to be generated on of Google Cloud Console. The following steps are provided on
this gspread authentication page:
https://docs.gspread.org/en/latest/oauth2.html#enable-api-access-for-a-project
Service account file formatting:
You must add a service_account.json for your gspread credentials
-{
  "type": "",
  "project_id": "<>",
  "private_key_id": "<>",
  "private_key": "-----BEGIN PRIVATE KEY-----<>",
  "client_email": "<>",
  "client_id": "<>",
  "auth_uri": "<>",
  "token_uri": "<>",
  "auth_provider_x509_cert_url": "<>",
  "client_x509_cert_url": "<>"

#### sort_trade_times_and_export_csv.py
Runs the following function from the file_utilities module:
file_utilities.export_trades_df_to_csv(csv_df, trades_file, description='sorted')

#### trades_recorder.py
In charge of computing the following information and placing in google spreadsheet
for each trade.

*   Broker
*   Side
*   Entry Shares
*   Exit Shares
*   Avg Entry Price
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
*   Float
*   Market Cap
*   Sector
*   % Open Gain

#### trading_charts_folder_ids.py
WIP: For each trade, gather data in polygon to form a three-year chart, and a two-day
chart into one picture and place in a folder so the trader can go back and review
trades.

#### util.py
*dbg_print()*:
Checks static flag to enable print statements

#### config/config.ini
You will need to add this file into your repo

Format:

````
[main]
POLYGON_API_KEY=
GSPREAD_WORKSHEET=
````


#### hloc_recorder.py
Grabs all hloc information from the day of the trades to the next day

* High
* Low
* Open
* Close
* Next High
* Next Low
* Next Open
* Next Close
* High Time
* Low Time
* Next High Time
* Next Low Time
* Morn High
* Morn Low
* Aft High
* Aft Low
* Morn High Time
* Morn Low Time
* Aft High Time
* Aft Low Time
