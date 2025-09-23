# 9:20 Hedged OTM Option Selling Strategy Simulation
import config
import pandas as pd
from datetime import datetime, date, time, timedelta
import os
import time as os_time

try:
    from dhanhq import dhanhq
except ImportError:
    print("FATAL ERROR: The 'dhanhq' library is not installed. Please run 'pip install dhanhq'.")
    exit()

# --- Helper Functions ---

def get_instrument_file():
    """
    Downloads or reads the master list of all tradable instruments from Dhan.
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
            return instrument_df
        except Exception as e:
            print(f"FATAL: Error downloading instrument file: {e}")
            return None

def get_security_id_from_symbol(instrument_df, trading_symbol):
    """
    Finds the security ID for a given trading symbol.
    """
    try:
        filtered_df = instrument_df[
            (instrument_df['SEM_TRADING_SYMBOL'] == trading_symbol) &
            (instrument_df['SEM_EXM_EXCH_ID'] == 'NSE_FNO') &
            (instrument_df['SEM_EXCH_INSTRUMENT_TYPE'] == 'OPTIDX')
        ]
        if not filtered_df.empty:
            return str(filtered_df.iloc[0]['SEM_SMST_SECURITY_ID'])
    except Exception as e:
        print(f"Error finding security ID for {trading_symbol}: {e}")
    print(f"Warning: Could not find security ID for symbol: {trading_symbol}")
    return None

def construct_trading_symbol(underlying, expiry_date, strike, option_type):
    """
    Constructs the Dhan-compatible trading symbol string.
    """
    dt_expiry = datetime.strptime(expiry_date, '%Y-%m-%d')
    # Format required by Dhan is DDMMMYYYY, e.g., '25SEP2025'
    expiry_str_dhan = dt_expiry.strftime('%d%b%Y').upper()
    return f"{underlying}{expiry_str_dhan}{strike}{option_type}"

def find_weekly_expiry(instrument_df):
    """
    Finds the nearest weekly expiry date for Bank Nifty options.
    """
    today = date.today()
    # Filter for BANKNIFTY index options using the correct column names
    bn_options = instrument_df[
        (instrument_df['SM_SYMBOL_NAME'] == 'BANKNIFTY') &
        (instrument_df['SEM_EXCH_INSTRUMENT_TYPE'] == 'OPTIDX') &
        (instrument_df['SEM_EXM_EXCH_ID'] == 'NSE_FNO')
    ].copy()
    bn_options['EXPIRY_DT'] = pd.to_datetime(bn_options['SEM_EXPIRY_DATE'], format='%Y-%m-%d').dt.date
    future_expiries = bn_options[bn_options['EXPIRY_DT'] >= today]
    nearest_expiry = future_expiries['EXPIRY_DT'].min()
    print(f"Found nearest weekly expiry: {nearest_expiry.strftime('%Y-%m-%d')}")
    return nearest_expiry.strftime('%Y-%m-%d')

def get_live_price(dhan, security_id):
    """
    Fetches the live Last Traded Price (LTP) for a given security ID.
    """
    if not security_id: return 0.0
    try:
        # The quote_data method expects a dictionary payload.
        payload = {'NSE_FNO': [security_id]}
        response = dhan.quote_data(securities=payload)

        if response and response.get('status') == 'success':
            # The response nests the data under the security ID
            return response['data'][security_id]['ltp']
    except Exception as e:
        print(f"Error fetching live price for security ID {security_id}: {e}")
    return 0.0

def get_bank_nifty_spot_price(dhan, instrument_df):
    """
    Fetches the live spot price for the Bank Nifty index by finding its security ID dynamically.
    """
    try:
        # Find the security ID for the NIFTY BANK index from the instrument file
        # Note: The symbol name for the index is 'BANKNIFTY' not 'NIFTY BANK'
        # Using .str.strip() and .str.lower() for a robust, case-insensitive search.
        bn_index = instrument_df[
            (instrument_df['SM_SYMBOL_NAME'].str.strip().str.lower() == config.TRADING_SYMBOL.lower()) &
            (instrument_df['SEM_EXM_EXCH_ID'].str.strip() == 'NSE')
        ]
        if bn_index.empty:
            print(f"Error: Could not find '{config.TRADING_SYMBOL}' index in the instrument file.")
            return 0.0

        security_id = str(bn_index.iloc[0]['SEM_SMST_SECURITY_ID'])

        payload = {'NSE_INDEX': [security_id]}
        response = dhan.quote_data(securities=payload)
        if response and response.get('status') == 'success':
            return response['data'][security_id]['ltp']

    except Exception as e:
        print(f"Error fetching Bank Nifty spot price: {e}")
    return 0.0

# --- Main Simulation Logic ---

def run_simulation(dhan):
    """
    The main function to run the entire trading simulation for a day.
    """
    print("--- Starting 9:20 Hedged OTM Strategy Simulation ---")

    # --- Wait for 9:20 AM ---
    entry_time = time(9, 20)
    now = datetime.now().time()

    # --- Wait for 9:20 AM ---
    if not config.DEV_MODE:
        entry_time = time(9, 20)
        while datetime.now().time() < entry_time:
            print(f"Waiting for 9:20 AM. Current time: {datetime.now().strftime('%H:%M:%S')}", end="\r")
            os_time.sleep(5)
    else:
        print("--- DEV MODE: Skipping wait for 9:20 AM ---")

    print(f"\n--- Entry Time Reached! ---")

    # --- Get Instruments and Initial Data ---
    instrument_df = get_instrument_file()
    if instrument_df is None: return

    spot_price = get_bank_nifty_spot_price(dhan, instrument_df)
    if spot_price == 0.0:
        print("Could not fetch spot price. Exiting.")
        return

    expiry_date = find_weekly_expiry(instrument_df)

    print(f"Executing trade with Spot Price: {spot_price} and Expiry: {expiry_date}")

    # --- Calculate Strikes ---
    strike_base = int(round(spot_price / 100) * 100)
    short_ce_strike = strike_base + config.SHORT_OTM_DISTANCE
    short_pe_strike = strike_base - config.SHORT_OTM_DISTANCE
    hedge_ce_strike = short_ce_strike + config.HEDGE_DISTANCE
    hedge_pe_strike = short_pe_strike - config.HEDGE_DISTANCE

    # --- Create a dictionary to hold all trade leg data ---
    trade_legs = {
        'Short_CE': {'type': 'CE', 'strike': short_ce_strike, 'action': 'SELL'},
        'Hedge_CE': {'type': 'CE', 'strike': hedge_ce_strike, 'action': 'BUY'},
        'Short_PE': {'type': 'PE', 'strike': short_pe_strike, 'action': 'SELL'},
        'Hedge_PE': {'type': 'PE', 'strike': hedge_pe_strike, 'action': 'BUY'}
    }

    # --- Find Security IDs and Entry Prices ---
    print("\nFetching entry premiums at 9:20 AM...")
    for leg_name, leg_data in trade_legs.items():
        symbol = construct_trading_symbol(
            config.TRADING_SYMBOL, expiry_date, leg_data['strike'], leg_data['type']
        )
        sec_id = get_security_id_from_symbol(instrument_df, symbol)

        leg_data['symbol'] = symbol
        leg_data['sec_id'] = sec_id
        leg_data['entry_price'] = get_live_price(dhan, sec_id)
        leg_data['status'] = 'OPEN'
        leg_data['exit_price'] = 0.0
        leg_data['pnl'] = 0.0

        if 'Short' in leg_name:
            sl_price = leg_data['entry_price'] * (1 + config.SL_PERCENTAGE / 100)
            leg_data['sl'] = round(sl_price, 1)

        print(f"  -> {leg_name} ({leg_data['symbol']}): Fetched Premium = {leg_data['entry_price']}" + (f", SL = {leg_data['sl']}" if 'sl' in leg_data else ""))

    # --- Store all data in a master dictionary ---
    simulation_data = {
        'Date': date.today().strftime('%Y-%m-%d'),
        'Timestamp': datetime.now().strftime('%H:%M:%S'),
        'Spot_Price_Entry': spot_price,
        'Legs': trade_legs,
        'Net_Credit': (trade_legs['Short_CE']['entry_price'] + trade_legs['Short_PE']['entry_price']) - \
                      (trade_legs['Hedge_CE']['entry_price'] + trade_legs['Hedge_PE']['entry_price']),
        'Total_PL': 0.0
    }

    print(f"\nInitial Net Credit: {simulation_data['Net_Credit']:.2f}")
    print("\n--- Core Engine Setup Complete. Now Monitoring for SL or EOD Exit. ---")

    # --- Monitoring Loop ---
    exit_time = time(15, 0) # 3:00 PM
    now = datetime.now()

    # --- Monitoring Loop ---
    if not config.DEV_MODE:
        exit_time = time(15, 0) # 3:00 PM
        while datetime.now().time() < exit_time:
            now = datetime.now()
            print(f"\nChecking prices at {now.strftime('%H:%M:%S')}...")

            for leg_name, leg_data in trade_legs.items():
                if 'Short' in leg_name and leg_data['status'] == 'OPEN':
                    current_price = get_live_price(dhan, leg_data['sec_id'])
                    print(f"  -> {leg_name}: Current Price = {current_price}, SL = {leg_data['sl']}")

                    if current_price >= leg_data['sl']:
                        print(f"!!! STOP-LOSS HIT for {leg_name} at {current_price} !!!")
                        leg_data['status'] = 'CLOSED_SL'
                        leg_data['exit_price'] = current_price
                        leg_data['exit_time'] = now.strftime('%H:%M:%S')

            # Check if both short positions are closed
            if trade_legs['Short_CE']['status'] != 'OPEN' and trade_legs['Short_PE']['status'] != 'OPEN':
                print("Both short positions have been stopped out. Ending monitoring.")
                break

            os_time.sleep(60) # Check every 60 seconds
    else:
        print("--- DEV MODE: Skipping SL monitoring loop. Proceeding to EOD exit. ---")

    # --- Square Off at 3:00 PM ---
    print(f"\n--- End of Day ({exit_time.strftime('%H:%M:%S')}) Reached. Exiting all open positions. ---")
    for leg_name, leg_data in trade_legs.items():
        if leg_data['status'] == 'OPEN':
            exit_price = get_live_price(dhan, leg_data['sec_id'])
            leg_data['status'] = 'CLOSED_EOD'
            leg_data['exit_price'] = exit_price
            leg_data['exit_time'] = datetime.now().strftime('%H:%M:%S')
            print(f"  -> Exiting {leg_name} at {exit_price}")

    # --- Final P/L Calculation ---
    total_pnl = 0
    for leg_name, leg_data in trade_legs.items():
        pnl = 0
        if leg_data['action'] == 'SELL':
            pnl = (leg_data['entry_price'] - leg_data['exit_price']) * config.LOT_SIZE
        else: # BUY
            pnl = (leg_data['exit_price'] - leg_data['entry_price']) * config.LOT_SIZE
        leg_data['pnl'] = round(pnl, 2)
        total_pnl += pnl

    simulation_data['Total_PL'] = round(total_pnl, 2)

    print("\n--- Final Results ---")
    print(f"Total P/L: {simulation_data['Total_PL']:.2f}")
    for leg_name, leg_data in trade_legs.items():
        print(f"  -> {leg_name}: P/L = {leg_data['pnl']:.2f}")

    export_simulation_results(simulation_data)
    return simulation_data

def export_simulation_results(data):
    """Formats the simulation data and saves it to an Excel file."""
    if not data: return

    legs = data['Legs']
    flat_data = {
        'Timestamp / Date': data['Date'],
        'Spot Price': data['Spot_Price_Entry'],
        'Short CE Strike': legs['Short_CE']['strike'],
        'Short CE Premium': legs['Short_CE']['entry_price'],
        'Short CE SL': legs['Short_CE'].get('sl', 0.0),
        'Short CE Exit Price': legs['Short_CE']['exit_price'],
        'Short CE P/L': legs['Short_CE']['pnl'],
        'Hedge CE Strike': legs['Hedge_CE']['strike'],
        'Hedge CE Premium': legs['Hedge_CE']['entry_price'],
        'Hedge CE Exit Price': legs['Hedge_CE']['exit_price'],
        'Short PE Strike': legs['Short_PE']['strike'],
        'Short PE Premium': legs['Short_PE']['entry_price'],
        'Short PE SL': legs['Short_PE'].get('sl', 0.0),
        'Short PE Exit Price': legs['Short_PE']['exit_price'],
        'Short PE P/L': legs['Short_PE']['pnl'],
        'Hedge PE Strike': legs['Hedge_PE']['strike'],
        'Hedge PE Premium': legs['Hedge_PE']['entry_price'],
        'Hedge PE Exit Price': legs['Hedge_PE']['exit_price'],
        'Net Credit': data['Net_Credit'],
        'Total P/L': data['Total_PL']
    }

    new_df = pd.DataFrame([flat_data])
    filename = config.SIMULATION_EXCEL_FILE

    try:
        if os.path.isfile(filename):
            existing_df = pd.read_excel(filename)
            combined_df = pd.concat([existing_df, new_df], ignore_index=True)
        else:
            combined_df = new_df

        combined_df.to_excel(filename, index=False, sheet_name='SimulationLog')
        print(f"\nSuccessfully exported simulation results to {filename}")
    except Exception as e:
        print(f"Error exporting to Excel: {e}")


if __name__ == "__main__":
    # --- Securely Initialize Dhan API Client ---
    CLIENT_ID = os.getenv('DHAN_CLIENT_ID')
    ACCESS_TOKEN = os.getenv('DHAN_ACCESS_TOKEN')

    if not CLIENT_ID or not ACCESS_TOKEN:
        print("FATAL ERROR: Environment variables DHAN_CLIENT_ID and DHAN_ACCESS_TOKEN are not set.")
        print("Please set them before running the script.")
        exit()

    try:
        dhan = dhanhq(CLIENT_ID, ACCESS_TOKEN)
        print("Dhan API client initialized successfully.")

        # Run the main simulation
        simulation_result = run_simulation(dhan)

    except Exception as e:
        print(f"An error occurred during script execution: {e}")
