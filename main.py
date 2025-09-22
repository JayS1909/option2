import config
import pandas as pd
from datetime import datetime, date
import os
import time

try:
    from dhanhq import dhanhq
except ImportError:
    print("FATAL ERROR: The 'dhanhq' library is not installed. Please run 'pip install dhanhq'.")
    exit()

# --- Main Functions ---

def get_instrument_file():
    """
    Downloads or reads the master list of all tradable instruments from Dhan.
    Saves it locally for the day to avoid re-downloading.
    """
    current_date_str = date.today().strftime("%Y-%m-%d")
    dir_name = "Dependencies"
    expected_file = os.path.join(dir_name, f"all_instrument {current_date_str}.csv")

    if not os.path.exists(dir_name):
        os.makedirs(dir_name)

    if os.path.exists(expected_file):
        print(f"Reading existing instrument file for today.")
        return pd.read_csv(expected_file, low_memory=False)
    else:
        for item in os.listdir(dir_name):
            if item.startswith('all_instrument'):
                os.remove(os.path.join(dir_name, item))
        
        print("Downloading new instrument file from Dhan...")
        try:
            instrument_df = pd.read_csv("https://images.dhan.co/api-data/api-scrip-master.csv", low_memory=False)
            instrument_df.to_csv(expected_file, index=False)
            print("New instrument file downloaded successfully.")
            return instrument_df
        except Exception as e:
            print(f"FATAL: Error downloading instrument file: {e}")
            return None

def get_security_id_from_symbol(instrument_df, trading_symbol, exchange='NSE'):
    """
    Finds the security ID for a given trading symbol from the master instrument DataFrame.
    """
    try:
        filtered_df = instrument_df[
            (instrument_df['SEM_TRADING_SYMBOL'] == trading_symbol) &
            (instrument_df['SEM_EXM_EXCH_ID'] == exchange)
        ]
        if not filtered_df.empty:
            return str(filtered_df.iloc[0]['SEM_SMST_SECURITY_ID'])
    except Exception as e:
        print(f"Error finding security ID for {trading_symbol}: {e}")
    
    print(f"Warning: Could not find security ID for symbol: {trading_symbol}")
    return None

def get_live_price(dhan, security_id):
    """
    Fetches the live Last Traded Price (LTP) for a given security ID.
    """
    if not security_id:
        return 0.0
    try:
        # The function expects the keyword 'securities' and a dictionary payload.
        securities_payload = {'NSE_FNO': [security_id]}
        response = dhan.quote_data(securities=securities_payload)
        
        if response.get('status') == 'success':
            # The response nests the data under the security ID
            return response['data'][security_id]['ltp']
    except Exception as e:
        print(f"Error fetching live price for security ID {security_id}: {e}")
    return 0.0

def construct_trading_symbol(underlying, expiry_date, strike, option_type):
    """
    Constructs the trading symbol string in the correct format.
    Example: 'BANKNIFTY-Sep2025-48300-CE'
    """
    dt_expiry = datetime.strptime(expiry_date, '%Y-%m-%d')
    month_year_str = dt_expiry.strftime('%b%Y').capitalize()
    return f"{underlying}-{month_year_str}-{strike}-{option_type}"

def run_live_paper_trade(dhan):
    """
    Fetches live data for the strategy and logs it.
    This is a LIVE PAPER TRADING tool.
    """
    print(f"\n--- Running Live Paper Trade for {date.today().strftime('%Y-%m-%d')} ---")
    
    instrument_df = get_instrument_file()
    if instrument_df is None:
        return

    # --- Use Manual Inputs from Config ---
    expiry_str = config.MANUAL_EXPIRY_DATE
    spot_price = config.MANUAL_SPOT_PRICE
    print(f"Using Manual Expiry: {expiry_str}, Manual Spot: {spot_price}")

    if not expiry_str or not spot_price:
        print("Please set MANUAL_EXPIRY_DATE and MANUAL_SPOT_PRICE in config.py")
        return

    # --- Calculate Strikes ---
    short_ce_strike = int(round((spot_price + config.SHORT_OTM_DISTANCE) / 100) * 100)
    short_pe_strike = int(round((spot_price - config.SHORT_OTM_DISTANCE) / 100) * 100)
    hedge_ce_strike = short_ce_strike + config.HEDGE_DISTANCE
    hedge_pe_strike = short_pe_strike - config.HEDGE_DISTANCE

    print(f"Strikes -> Short CE: {short_ce_strike}, Hedge CE: {hedge_ce_strike}")
    print(f"Strikes -> Short PE: {short_pe_strike}, Hedge PE: {hedge_pe_strike}")

    # --- Construct Trading Symbols ---
    symbols = {
        "Short CE": construct_trading_symbol(config.TRADING_SYMBOL, expiry_str, short_ce_strike, 'CE'),
        "Hedge CE": construct_trading_symbol(config.TRADING_SYMBOL, expiry_str, hedge_ce_strike, 'CE'),
        "Short PE": construct_trading_symbol(config.TRADING_SYMBOL, expiry_str, short_pe_strike, 'PE'),
        "Hedge PE": construct_trading_symbol(config.TRADING_SYMBOL, expiry_str, hedge_pe_strike, 'PE')
    }
    
    print("\nConstructed Trading Symbols:")
    for name, symbol in symbols.items():
        print(f"- {name}: {symbol}")

    # --- Find Security IDs ---
    ids = {name: get_security_id_from_symbol(instrument_df, symbol) for name, symbol in symbols.items()}

    if not all(ids.values()):
        print("\nCould not find all security IDs. Please check symbols and master file.")
        return

    # --- Fetch Live Prices ---
    print("\nFetching live prices...")
    prices = {name: get_live_price(dhan, security_id) for name, security_id in ids.items()}

    # --- Log the Data ---
    trade_log = {
        'Date': date.today().strftime('%Y-%m-%d'),
        'Timestamp': datetime.now().strftime('%H:%M:%S'),
        'Spot Price': spot_price,
        'Short CE Strike': short_ce_strike, 'Short CE Premium': prices["Short CE"],
        'Hedge CE Strike': hedge_ce_strike, 'Hedge CE Premium': prices["Hedge CE"],
        'Short PE Strike': short_pe_strike, 'Short PE Premium': prices["Short PE"],
        'Hedge PE Strike': hedge_pe_strike, 'Hedge PE Premium': prices["Hedge PE"],
        'Net Credit': (prices["Short CE"] + prices["Short PE"]) - (prices["Hedge CE"] + prices["Hedge PE"])
    }
    
    print("\n--- Live Trade Data Captured ---")
    print(pd.Series(trade_log))
    export_to_excel(trade_log)

def export_to_excel(trade_log):
    """Exports the trade log dictionary to an Excel file."""
    if not trade_log: return
    new_df = pd.DataFrame([trade_log])
    filename = config.EXCEL_FILE_NAME
    columns = list(trade_log.keys())
    new_df = new_df[columns]

    try:
        if os.path.isfile(filename):
            existing_df = pd.read_excel(filename)
            combined_df = pd.concat([existing_df, new_df], ignore_index=True)
        else:
            combined_df = new_df
        combined_df.to_excel(filename, index=False, sheet_name='LiveTrades')
        print(f"\nSuccessfully exported trade data to {filename}")
    except Exception as e:
        print(f"Error exporting to Excel: {e}")

if __name__ == "__main__":
    try:
        dhan = dhanhq(config.DHAN_CLIENT_ID, config.DHAN_ACCESS_TOKEN)
        print("Dhan API client initialized successfully.")
        run_live_paper_trade(dhan)
    except Exception as e:
        print(f"An error occurred during script execution: {e}")
