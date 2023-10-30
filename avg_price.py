import sys
import pandas as pd

trades_file = sys.argv[1]
df = pd.read_csv(trades_file)
# Add dollar value to each entry/exit
df['dollar_val'] = df['Price'] * df['Qty']
# Get dollar value sum
df_sum = df.groupby(['Symbol', 'Side'])['dollar_val'].sum()
# Get weight
df_weight = df.groupby(['Symbol', 'Side'])['Qty'].sum()
# Compute Average Price
df_avg_prices = df_sum / df_weight
print(df_avg_prices.to_string())
