import pandas as pd
import numpy as np
import csv
import pytz
try: 
    from mappings import exercise_mappings
except ImportError:
    print("Warning: Could not import 'exercise_mappings' from mappings.py.")
    print("Using an empty mapping dictionary.")
    exercise_mappings = {}

def apply_exercise_mappings(df, mapping_dict, exercise_col='Exercise Name'):
    """
    Applies exercise name mappings to the DataFrame's exercise column.

    Args:
        df (pd.DataFrame): The DataFrame containing exercise data.
        mapping_dict (dict): Dictionary where keys are old names and values are new names.
        exercise_col (str): The name of the column containing exercise names.

    Returns:
        pd.DataFrame: DataFrame with updated exercise names.
    """
    if exercise_col in df.columns:
        # Ensure mapping_dict keys/values are strings if needed, handle potential NaNs
        valid_mappings = {str(k): str(v) for k, v in mapping_dict.items() if pd.notna(k)}
        df[exercise_col] = df[exercise_col].astype(str).replace(valid_mappings)
        print(f"Applied {len(valid_mappings)} exercise mappings.")
    else:
        print(f"Warning: Exercise column '{exercise_col}' not found. No mappings applied.")
    return df

def convert_gymrun_to_strong(gymrun_file='gymrun.csv', strong_example_file='strong.csv', output_file='converted.csv', initial_mapping=None):
    """
    Converts a Gymrun CSV export to a format compatible with Strong app import,
    handling Norwegian timezone conversion to UTC and mapping cardio data based on presence of Duration/Distance.

    Args:
        gymrun_file (str): Path to the Gymrun CSV export file.
        strong_example_file (str): Path to an example Strong CSV file to get headers.
        output_file (str): Path to save the converted CSV file.
        initial_mapping (dict): A dictionary for initial exercise name mappings.
                                Example: {'Barbell Flat Bench Press': 'Bench Press (Barbell)'}
    """
    if initial_mapping is None:
        initial_mapping = {}

    try:
        # Load the Gymrun data using semicolon delimiter
        gymrun_df = pd.read_csv(gymrun_file, sep=';')
        # Load Strong example to get exact headers, also semicolon delimited
        strong_headers_df = pd.read_csv(strong_example_file, sep=';', nrows=0) # Read only headers
        strong_headers = strong_headers_df.columns.tolist()
        print(f"Successfully loaded '{gymrun_file}' and headers from '{strong_example_file}'.")
        print(f"Gymrun columns: {gymrun_df.columns.tolist()}")
        print(f"Target Strong columns: {strong_headers}")

    except FileNotFoundError as e:
        print(f"Error loading file: {e}. Make sure '{gymrun_file}' and '{strong_example_file}' exist in the correct directory.")
        return
    except Exception as e:
        print(f"Error reading CSV files: {e}")
        return

    # --- Data Preprocessing ---
    # Check for essential columns (Added Type, Duration, Distance)
    required_gymrun_cols = ['Date', 'Time', 'Exercise', 'Set', 'Weight', 'Reps', 'Type', 'Duration', 'Distance']
    missing_cols = [col for col in required_gymrun_cols if col not in gymrun_df.columns]
    if missing_cols:
        # Don't exit completely, just warn if Type/Duration/Distance are missing
        print(f"Warning: Missing optional columns in '{gymrun_file}': {missing_cols}. Cardio/timed data might not be processed.")
        # Check for absolutely essential columns
        essential_cols = ['Date', 'Time', 'Exercise', 'Set', 'Weight', 'Reps']
        missing_essential = [col for col in essential_cols if col not in gymrun_df.columns]
        if missing_essential:
             print(f"Error: Missing essential columns in '{gymrun_file}': {missing_essential}")
             return


    # Combine Date and Time, handling potential errors
    try:
        # 1. Create naive timestamp
        gymrun_df['NaiveTimestamp'] = pd.to_datetime(gymrun_df['Date'] + ' ' + gymrun_df['Time'], format='%d.%m.%Y %H:%M:%S', errors='coerce')
        gymrun_df.dropna(subset=['NaiveTimestamp'], inplace=True) # Drop rows where timestamp couldn't be parsed

        # 2. Localize to Norway time
        norway_tz = pytz.timezone('Europe/Oslo')
        gymrun_df['LocalizedTimestamp'] = gymrun_df['NaiveTimestamp'].apply(lambda dt: norway_tz.localize(dt, is_dst=None)) # is_dst=None handles ambiguity/non-existent times

        # 3. Convert to UTC
        gymrun_df['Timestamp'] = gymrun_df['LocalizedTimestamp'].dt.tz_convert('UTC')

        print(f"Parsed 'Date' and 'Time', localized to 'Europe/Oslo', and converted to UTC 'Timestamp'. Found {len(gymrun_df)} valid rows.")

    except pytz.exceptions.AmbiguousTimeError as e:
         print(f"Error: Ambiguous time detected during DST changeover: {e}. Check data around DST transitions.")
         return
    except pytz.exceptions.NonExistentTimeError as e:
         print(f"Error: Non-existent time detected during DST changeover: {e}. Check data around DST transitions.")
         return
    except Exception as e:
        print(f"Error processing Date/Time columns: {e}")
        return

    # Sort by UTC timestamp to process workouts chronologically
    gymrun_df.sort_values('Timestamp', inplace=True)

    # --- Workout Grouping and Calculations (using UTC Timestamps) ---
    gymrun_df['WorkoutUTCDate'] = gymrun_df['Timestamp'].dt.date
    gymrun_df['WorkoutStartTimeUTC'] = gymrun_df.groupby('WorkoutUTCDate')['Timestamp'].transform('min')
    gymrun_df['WorkoutEndTimeUTC'] = gymrun_df.groupby('WorkoutUTCDate')['Timestamp'].transform('max')
    # Calculate overall workout duration in seconds
    gymrun_df['Duration (sec)'] = (gymrun_df['WorkoutEndTimeUTC'] - gymrun_df['WorkoutStartTimeUTC']).dt.total_seconds().astype(int)

    unique_utc_dates = gymrun_df['WorkoutUTCDate'].unique()
    utc_date_to_workout_num = {date: i + 1 for i, date in enumerate(unique_utc_dates)}
    gymrun_df['Workout #'] = gymrun_df['WorkoutUTCDate'].map(utc_date_to_workout_num)
    gymrun_df['Date'] = gymrun_df['WorkoutStartTimeUTC'].dt.strftime('%Y-%m-%d %H:%M:%S')

    # --- Handle Cardio/Timed Data ---
    # Initialize Strong columns
    gymrun_df['Seconds'] = 0
    gymrun_df['Distance (meters)'] = 0.0 # Initialize as float

    # Process Duration -> Seconds
    if 'Duration' in gymrun_df.columns:
        # Ensure 'Duration' is numeric, coercing errors, fill NaN with 0
        duration_numeric = pd.to_numeric(gymrun_df['Duration'], errors='coerce').fillna(0)
        # Populate 'Seconds' where Duration > 0 (assuming Duration is in minutes)
        gymrun_df['Seconds'] = np.where(
            duration_numeric > 0,
            (duration_numeric * 60).astype(int), # Convert minutes to seconds
            0 # Default if Duration is 0 or NaN
        )
        print("Processed Gymrun 'Duration' into Strong 'Seconds'.")
    else:
        print("Warning: 'Duration' column missing in Gymrun data. Cannot process timed exercise duration.")

    # Process Distance -> Distance (meters)
    if 'Distance' in gymrun_df.columns:
        # Ensure 'Distance' is numeric, coercing errors, fill NaN with 0
        distance_numeric = pd.to_numeric(gymrun_df['Distance'], errors='coerce').fillna(0)
        # Populate 'Distance (meters)' where Distance > 0 (assuming Distance is in km)
        gymrun_df['Distance (meters)'] = np.where(
            distance_numeric > 0,
            (distance_numeric * 1000).astype(float), # Convert km to meters
            0.0 # Default if Distance is 0 or NaN
        )
        print("Processed Gymrun 'Distance' into Strong 'Distance (meters)'.")
    else:
         print("Warning: 'Distance' column missing in Gymrun data. Cannot process exercise distance.")


    # --- Column Renaming and Mapping ---
    rename_map = {
        'Routine': 'Workout Name',
        'Exercise': 'Exercise Name',
        'Set': 'Set Order', # Use 'Set' from Gymrun for Set Order
        'Weight': 'Weight (kg)',
        # 'Reps': 'Reps', # Already correct name
        'Note': 'Notes'
        # 'Seconds' and 'Distance (meters)' are handled above
        # 'Duration (sec)' is the overall workout duration calculated earlier
    }
    gymrun_df.rename(columns=rename_map, inplace=True)

    # Apply initial exercise name mappings
    gymrun_df = apply_exercise_mappings(gymrun_df, initial_mapping, exercise_col='Exercise Name')

    # --- Add Missing Strong Columns ---
    for col in strong_headers:
        if col not in gymrun_df.columns:
            # Initialize based on expected type if possible
            if col in ['RPE', 'Notes', 'Workout Notes']:
                 gymrun_df[col] = ''
            elif col in ['Weight (kg)', 'Distance (meters)']:
                 gymrun_df[col] = 0.0
            elif col in ['Reps', 'Set Order', 'Seconds', 'Duration (sec)']:
                 gymrun_df[col] = 0
            else: # Default for any others like 'Workout #' or 'Date' (though they should exist)
                 gymrun_df[col] = ''


    # Fill NaN/Defaults and Ensure Correct Types
    # Note: 'Seconds' and 'Distance (meters)' are already initialized or calculated
    fill_defaults = {
        'Workout Name': 'Workout',
        'Notes': '',
        'Workout Notes': '',
        'RPE': '',
        'Weight (kg)': 0.0, 
        'Reps': 0,
        'Set Order': 1,
        'Seconds': 0, 
        'Distance (meters)': 0.0
    }

    for col, default in fill_defaults.items():
        if col in gymrun_df.columns:
            if col in ['Set Order', 'Reps', 'Seconds']:
                 # Convert to numeric first, coercing errors, then fillna, then int
                 gymrun_df[col] = pd.to_numeric(gymrun_df[col], errors='coerce').fillna(default).astype(int)
            elif col in ['Weight (kg)', 'Distance (meters)']:
                 # Convert to numeric first, coercing errors, then fillna, then float
                 gymrun_df[col] = pd.to_numeric(gymrun_df[col], errors='coerce').fillna(default).astype(float)
            else: # Handle string columns like Workout Name, Notes etc.
                 gymrun_df[col].fillna(default, inplace=True)
        # If a default column wasn't even present (e.g., RPE), it was added earlier

    # Final check on types after filling
    gymrun_df['Set Order'] = gymrun_df['Set Order'].astype(int)
    gymrun_df['Reps'] = gymrun_df['Reps'].astype(int)
    gymrun_df['Seconds'] = gymrun_df['Seconds'].astype(int)
    gymrun_df['Weight (kg)'] = gymrun_df['Weight (kg)'].astype(float)
    gymrun_df['Distance (meters)'] = gymrun_df['Distance (meters)'].astype(float)
    gymrun_df['Duration (sec)'] = gymrun_df['Duration (sec)'].astype(int)


    # --- Final Touches ---
    # Select and reorder columns to exactly match the Strong format
    try:
        # Ensure all target columns exist before selecting
        missing_final_cols = [col for col in strong_headers if col not in gymrun_df.columns]
        if missing_final_cols:
             print(f"Error: Final DataFrame is missing required Strong columns: {missing_final_cols}")
             print(f"Available columns before final selection: {gymrun_df.columns.tolist()}")
             return

        converted_df = gymrun_df[strong_headers]
    except KeyError as e:
        print(f"Error: Could not find all required Strong columns after processing: {e}")
        print(f"Available columns: {gymrun_df.columns.tolist()}")
        return

    # --- Save Output ---
    try:
        # Ensure correct quoting for potentially empty strings in numeric columns if needed
        converted_df.to_csv(output_file, sep=';', index=False, quoting=csv.QUOTE_NONNUMERIC)
        print(f"Conversion complete. Output saved to '{output_file}'")
    except Exception as e:
        print(f"Error saving output file '{output_file}': {e}")

# --- Main method ---
if __name__ == "__main__":

    # Run the conversion using mappings from mappings.py
    convert_gymrun_to_strong(
        gymrun_file='gymrun.csv',
        strong_example_file='strong.csv',
        output_file='converted.csv',
        initial_mapping=exercise_mappings 
    )