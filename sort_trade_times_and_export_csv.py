import sys
import csv

import util

trades_file = sys.argv[1]

csv_df = file_utilities.trades_csv_to_df(trades_file)
csv_df = csv_df.sort_values(['Symb', 'Time'])
file_utilities.export_trades_df_to_csv(csv_df, trades_file, description='sorted')
