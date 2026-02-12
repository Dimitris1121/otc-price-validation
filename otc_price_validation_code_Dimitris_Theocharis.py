# Importing libraries
import pandas as pd
import numpy as np

# Manually opened the files to understand their structure

# Loading the CSV files
OTC_trades = pd.read_csv(r"C:\Users\mypc\Desktop\OTC_trades.csv", sep=";", decimal="," # tradeprice has , instead  of . thats why decimal=","
    )

standard_trades = std = pd.read_csv(r"C:\Users\mypc\Desktop\standard_trades.csv", sep=";", decimal="," # tradeprice has , instead  of . thats why decimal=","
                        , skiprows=[1]  # skip the  +----- line 
                        )








# Quick Checks for OTC_trades table
OTC_trades.head()
OTC_trades.shape # 2175 rows  , 13 cols
OTC_trades.info() # Dates need to be fixed

# Data Cleaning of OTC_trades table

# Standardizing column names in case there are typos
OTC_trades.columns = [c.strip() for c in OTC_trades.columns] 

# Converting tsreceive to datetime
OTC_trades["tsreceive"] = pd.to_datetime(OTC_trades["tsreceive"])  
OTC_trades["tsreceive"].isna().sum()
OTC_trades.head()
OTC_trades.info() 

# Reconstructing full TradingTime timestamp (Assumption: TradingTime refers to the same day as tsreceive).
# Creaing trade_date from tsreceive
OTC_trades["trade_date"] = OTC_trades["tsreceive"].dt.date

# Combining date + time into full timestamp
OTC_trades["TradingTime"] = pd.to_datetime(OTC_trades["trade_date"].astype(str) + " " + OTC_trades["TradingTime"].astype(str))
OTC_trades.head()
OTC_trades["TradingTime"].isna().sum()
OTC_trades.info() 

OTC_trades["trade_date"].drop() #  Dropping trade_date column
OTC_trades = OTC_trades.drop("trade_date", axis=1)

OTC_trades["TradingTime"] = OTC_trades["TradingTime"].dt.tz_localize("Europe/Paris") # Localizing TradingTime to Paris time because exchange open is defined in Paris time)
OTC_trades.head()



# Some quick data quality checks to make sure everything works fine with  OTC_trades table

# Tolerance should be >= 0
bad_tol = OTC_trades[OTC_trades["tolerance"] < 0]
print("Negative tolerance rows:", len(bad_tol))

# Prices should be > 0
bad_price = OTC_trades[OTC_trades["tradeprice"] <= 0]
print("Non-positive price rows:", len(bad_price))

# Missing keys
missing_keys = OTC_trades[OTC_trades["cisin"].isna() | OTC_trades["symbol_index"].isna()]
print("Missing cisin/symbol_index rows:", len(missing_keys))








# Quick Checks for standard_trades table
standard_trades.head()
standard_trades.shape # 196708 rows, 6 cols
standard_trades.info() # cols 0 and 6 need to be removed.

# Data Cleaning of OTC_trades table
standard_trades = standard_trades.drop(columns=["col_0", "col_6"]) # cols 0 and 6
standard_trades.head()

# Fixing column names to be consistent with OTC_trades table.
standard_trades = standard_trades.rename(columns={
    "symbolindex": "symbol_index",
    "instrumenttradingcode": "cisin"
})
standard_trades.head()

# Dropping rows where symbol_index is null
standard_trades = standard_trades.dropna(subset=["symbol_index"])
standard_trades = standard_trades.dropna(subset=["ProduceTime"])
standard_trades.isna().sum() # No null values anymore

# Fixing symbol_index type to be consistent with OTC_trades table.
standard_trades["symbol_index"] = standard_trades["symbol_index"].astype("int64")
standard_trades.head()

# Converting ProduceTime to the appropriate format
standard_trades["ProduceTime"] = pd.to_numeric(standard_trades["ProduceTime"]).astype("Int64")
standard_trades["ProduceTime"] = pd.to_datetime(standard_trades["ProduceTime"], unit="ns",  # The size of the number (1.60741E+18) tells us the unit is in nanoseconds.
                                                                                utc=True) # Produce time is the exact trade time in Unix epoch universal time
standard_trades["ProduceTime"] = standard_trades["ProduceTime"].dt.tz_convert("Europe/Paris")
standard_trades["ProduceTime"] = standard_trades["ProduceTime"].astype("datetime64[us, Europe/Paris]") # matching the exact format with OTC_trades
standard_trades.head()






# Checking for duplicate rows -> No duplicates
num_duplicates = OTC_trades.duplicated().sum()
print(num_duplicates)
duplicate_rows = standard_trades.duplicated().sum()
print(num_duplicates)





# Counting category values OTC_trades
OTC_trades.head()
OTC_trades["symbol_index"].value_counts().head()
OTC_trades["cisin"].value_counts().head()

# Counting category values standard_trades
standard_trades.head()
standard_trades["symbol_index"].value_counts().head()
standard_trades["cisin"].value_counts().head()












# Exercise solution
# I used an a join per symbol to grab the latest exchange price before each OTC trade, falling back to the next one if none existed.
# Then checked if the OTC price was within %tolerance of that exchange price.

# To complete the  exercise I need to choose on which key to perform the join. They need to share an instrument identifier. So symbol_index or cisin.
sym_overlap = set(OTC_trades["symbol_index"]).intersection(set(standard_trades["symbol_index"]))
cisin_overlap = set(OTC_trades["cisin"]).intersection(set(standard_trades["cisin"]))
len(sym_overlap), len(cisin_overlap) # They both overrlap in 42 situations. 
# I decided to join on symbol_index since it is the common instrument identifier across both datasets for 42 overlapping values.



# Preparing the dfs for the joins.
otc = OTC_trades.copy()
std = standard_trades.copy()

# I was getting an error here. This line checks whether the TradingTime column is timezone-aware. 
# If it is, I convert it to UTC so that all timestamps are in a consistent timezone before performing time-based matching. 
if getattr(otc["TradingTime"].dt, "tz", None) is not None:
    otc["TradingTime"] = otc["TradingTime"].dt.tz_convert("UTC")
if getattr(std["ProduceTime"].dt, "tz", None) is not None:
    std["ProduceTime"] = std["ProduceTime"].dt.tz_convert("UTC")

# Sorting 
otc = otc.sort_values(["TradingTime", "symbol_index"]).reset_index(drop=True)
std = std.sort_values(["ProduceTime", "symbol_index"]).reset_index(drop=True)



# Two asof matches (I used an as-of time join because I needed to match each OTC trade with the closest relevant exchange price based on time sequence, not exact timestamp equality.)

# backward (latest before) 
backward = pd.merge_asof(
    otc,
    std,
    left_on="TradingTime",
    right_on="ProduceTime",
    by="symbol_index",
    direction="backward"
)

# forward (next after)
forward = pd.merge_asof(
    otc,
    std[["symbol_index", "ProduceTime", "LastTradedPrice"]],
    left_on="TradingTime",
    right_on="ProduceTime",
    by="symbol_index",
    direction="forward",
)

#  Choose backward if it exists, otherwise forward.
otc["LastTradedPrice"] = np.where(backward["LastTradedPrice"].notna(), backward["LastTradedPrice"], forward["LastTradedPrice"])

final_df = otc.copy()
final_df.head()





# Build trade_date from TradingTime.
final_df["trade_date"] = final_df["TradingTime"].dt.date

# Build trade_date and isOK. tolerance is a percentage deviation from the exchange price
pct_diff = ((final_df["tradeprice"] - final_df["LastTradedPrice"]) / final_df["LastTradedPrice"]) * 100

final_df["isOK"] = (pct_diff.abs() <= final_df["tolerance"])




final_df[(final_df["tradeprice"] - final_df["LastTradedPrice"]).abs() > 10].head() # Manually checking

# Creating the final df requested
final_df = final_df[
    [
        "status", "symbol_index", "cisin", "venue", "CDEVNM", "tradeid", "traderef", "tid",
        "tsreceive", "volume", "tradeprice", "tolerance", "trade_date",
        "LastTradedPrice", "isOK"
    ]
].copy()
final_df.head()


# Save results to CSV
final_df.to_csv(r"C:\Users\mypc\Desktop\otc_price_validation.csv", index=False)