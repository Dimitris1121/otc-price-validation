# OTC Price Validation — Euronext Amsterdam

## Overview
Technical exercise completed for an Index Data Analyst position at Euronext Amsterdam.
The task involved validating OTC (Over-The-Counter) trade prices against standard 
exchange prices using time-based matching.

## Problem
Given two datasets:
- **OTC_trades** — 2,175 OTC trades reported outside the exchange
- **standard_trades** — 196,708 standard exchange trades

Validate whether each OTC trade price falls within its allowed tolerance 
percentage of the closest exchange price at the time of the trade.

## Approach

### 1. Data Cleaning & Preparation
- Standardized column names across both datasets
- Reconstructed full timestamps from date + time components
- Localized all timestamps to Europe/Paris timezone
- Converted Unix nanosecond timestamps to human readable datetime
- Removed invalid rows (null keys, missing timestamps)
- Data quality checks (negative tolerances, non-positive prices, missing identifiers)

### 2. Instrument Matching
Identified the common instrument identifier between the two datasets by 
comparing both `symbol_index` and `cisin` overlaps — both had 42 matching 
instruments. Chose `symbol_index` as the join key.

### 3. Time-Based Price Matching (As-Of Join)
Used `pd.merge_asof` — a time-based join that matches each OTC trade 
with the closest exchange price by time, not exact timestamp equality:
- **Backward match** — finds the latest exchange price **before** the OTC trade
- **Forward match** — finds the next exchange price **after** the OTC trade
- Priority given to backward match, falling back to forward if none exists

### 4. Price Validation
Calculated percentage difference between OTC price and matched exchange price:

pct_diff = |OTC price - Exchange price| / Exchange price × 100

Flagged each trade as isOK = True/False based on whether the difference 
fell within the trade's allowed tolerance percentage.

## Output
Final validation table with 15 columns including:
- Trade identifiers (symbol_index, cisin, tradeid)
- Trade details (venue, volume, tradeprice, tolerance)
- Matched exchange price (LastTradedPrice)
- Validation result (isOK)

## Key Technical Decisions
- Used merge_asof over exact joins because OTC and exchange timestamps 
  never match exactly — time-based proximity matching is the correct approach
- Converted all timestamps to UTC before joining to avoid timezone mismatch errors
- Chose backward-first matching because the most recent prior price is the 
  most relevant reference for validating a trade

## Tools
Python, pandas, numpy
