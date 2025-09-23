import pandas as pd
import os

def find_banknifty_entries():
    """
    This script reads the local instrument file and prints all entries
    related to Bank Nifty to help debug which one is the correct index.
    """
    dir_name = "Dependencies"
    try:
        # Find the instrument file
        instrument_file = None
        # Find a file in the directory that starts with 'all_instrument'
        for item in os.listdir(dir_name):
            if item.lower().startswith('all_instrument'):
                instrument_file = os.path.join(dir_name, item)
                break

        if not instrument_file:
            print(f"Could not find an instrument file in the '{dir_name}' folder.")
            print("Please ensure you have run one of the other scripts first to download it.")
            return

        print(f"--- Reading data from: {instrument_file} ---")
        df = pd.read_csv(instrument_file, low_memory=False)

        # Filter for all possible Bank Nifty entries using a case-insensitive search
        bn_df = df[df['SM_SYMBOL_NAME'].str.contains('BANKNIFTY', case=False, na=False)].copy()

        print("\n--- All Found Bank Nifty Entries ---")
        if bn_df.empty:
            print("No entries containing 'BANKNIFTY' were found in the SM_SYMBOL_NAME column.")
        else:
            # Define the columns we are interested in for debugging
            relevant_cols = ['SM_SYMBOL_NAME', 'SEM_EXM_EXCH_ID', 'SEM_SMST_SECURITY_ID', 'SEM_SERIES']
            # Filter down to only the columns that actually exist in the DataFrame
            existing_cols = [col for col in relevant_cols if col in df.columns]

            # Re-index the dataframe to only show the relevant columns
            bn_df_display = bn_df[existing_cols]

            print("Found the following entries. The correct one for the spot price is likely an 'INDEX'.")
            print(bn_df_display.to_string())

    except FileNotFoundError:
        print(f"Error: The directory '{dir_name}' was not found. Please run one of the other scripts first.")
    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    find_banknifty_entries()
