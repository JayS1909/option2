# -- Dhan API Credentials --
# IMPORTANT: For security, please set your credentials as environment variables.
# Do not hardcode them here.
#
# How to set environment variables:
# - Linux/macOS: export DHAN_CLIENT_ID='your_client_id'
# - Windows:     set DHAN_CLIENT_ID='your_client_id'
#
# The script will read these variables automatically.
# DHAN_CLIENT_ID = "YOUR_CLIENT_ID_HERE"
# DHAN_ACCESS_TOKEN = "YOUR_ACCESS_TOKEN_HERE"

# -- Mode --
# Set to True to skip time-based waits (for testing).
# Set to False for live simulation in market hours.
DEV_MODE = False

# -- Manual Inputs for main.py --
# These are required for the original main.py script to run.
MANUAL_EXPIRY_DATE = "2025-09-25"  # Format: YYYY-MM-DD
MANUAL_SPOT_PRICE = 48000.0       # Spot price for manual run

# -- Strategy Parameters --
TRADING_SYMBOL = "BANKNIFTY"
SHORT_OTM_DISTANCE = 300  # OTM distance for short legs (in points)
HEDGE_DISTANCE = 500      # Distance from short strikes to hedge strikes
SL_PERCENTAGE = 25.0      # Stop-loss percentage for short legs (e.g., 25.0 for 25%)
LOT_SIZE = 15             # Lot size for Bank Nifty

# -- Output Files --
# The original script (main.py) will log to this file.
LIVE_TRADE_EXCEL_FILE = "live_trade_log.xlsx"
# The new simulation script (simulation.py) will log to this file.
SIMULATION_EXCEL_FILE = "simulation_log.xlsx"
