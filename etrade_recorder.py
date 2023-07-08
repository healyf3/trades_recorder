import sys
import csv
import pandas as pd

trades_file = sys.argv[1]
print(trades_file)

# Read csv file into pandas dataframe
df = pd.read_csv('..\etrade_csv\\' + trades_file)

# Add dollar value to each entry/exit
df['dollar_val'] = df['Executed Price'] * df['Quantity']
# Get dollar value sum
df_sum = df.groupby(['Security', 'Order Type'])['dollar_val'].sum()
# Get weight
df_weight = df.groupby(['Security', 'Order Type'])['Quantity'].sum()
# Compute Average Price
df_avg_prices = df_sum / df_weight
print(df_avg_prices.to_string())

print('end')
