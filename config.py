# -- Dhan API Credentials --
# Please enter your Dhan Client ID and Access Token below.
# The Access Token can be generated from web.dhan.co
DHAN_CLIENT_ID = "1108533436"
DHAN_ACCESS_TOKEN = "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzUxMiJ9.eyJpc3MiOiJkaGFuIiwicGFydG5lcklkIjoiIiwiZXhwIjoxNzU4NTY1MjM2LCJpYXQiOjE3NTg0Nzg4MzYsInRva2VuQ29uc3VtZXJUeXBlIjoiU0VMRiIsIndlYmhvb2tVcmwiOiIiLCJkaGFuQ2xpZW50SWQiOiIxMTA4NTMzNDM2In0.NfWRgKQUswM0c2xbOPnvgSSUNjmu3WfXabhX3yRof2y-0l1RsuJeNuL_PdecF2CieIF9qEKMSBDWXTSFwpB6sg"

# -- Strategy Parameters --
TRADING_SYMBOL = "BANKNIFTY"
SHORT_OTM_DISTANCE = 300  # OTM distance for short legs (in points)
HEDGE_DISTANCE = 500      # Distance from short strikes to hedge strikes

# -- Manual Inputs for Live Trade --
# IMPORTANT: You must manually set these values before running the script.
MANUAL_EXPIRY_DATE = "2025-09-25"  # Format: YYYY-MM-DD
MANUAL_SPOT_PRICE = 48000.0       # Spot price at the time of entry

# -- Output --
EXCEL_FILE_NAME = "live_trade_log.xlsx"
