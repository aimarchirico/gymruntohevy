import pandas as pd
# Assuming your mappings are in mappings.py in the same directory
try:
    from mappings import exercise_mappings
except ImportError:
    print("Error: Could not import 'exercise_mappings' from mappings.py.")
    print("Please ensure mappings.py exists and contains the dictionary.")
    exercise_mappings = {} # Use empty dict to avoid crashing later

def extract_unmapped_exercises(gymrun_file='gymrun.csv', mapping_dict=None, output_file='unmapped.csv', exercise_col='Exercise'):
    """
    Reads a Gymrun CSV, counts unique unmapped exercises, and outputs a new CSV
    containing only rows with exercises not present as keys in the mapping dictionary.

    Args:
        gymrun_file (str): Path to the Gymrun CSV export file.
        mapping_dict (dict): Dictionary of exercise mappings (Gymrun name -> Strong name).
        output_file (str): Path to save the CSV with unmapped exercises.
        exercise_col (str): The name of the column containing exercise names in gymrun_file.
    """
    if mapping_dict is None:
        print("Warning: No mapping dictionary provided.")
        mapping_dict = {}

    try:
        # Load the Gymrun data using semicolon delimiter
        gymrun_df = pd.read_csv(gymrun_file, sep=';')
        print(f"Successfully loaded '{gymrun_file}'. Found {len(gymrun_df)} rows.")

    except FileNotFoundError:
        print(f"Error: File not found '{gymrun_file}'.")
        return
    except Exception as e:
        print(f"Error reading CSV file '{gymrun_file}': {e}")
        return

    # Check if the exercise column exists
    if exercise_col not in gymrun_df.columns:
        print(f"Error: Exercise column '{exercise_col}' not found in '{gymrun_file}'.")
        print(f"Available columns: {gymrun_df.columns.tolist()}")
        return

    # Get the list of exercise names that ARE in the mapping dictionary keys
    mapped_exercises = list(mapping_dict.keys())
    print(f"Found {len(mapped_exercises)} exercises in the mapping dictionary.")

    # Filter the DataFrame: keep rows where 'Exercise' is NOT in mapped_exercises
    unmapped_df = gymrun_df[~gymrun_df[exercise_col].astype(str).isin(mapped_exercises)]
    print(f"Found {len(unmapped_df)} rows with unmapped exercises.")

    # Count unique unmapped exercises
    if not unmapped_df.empty:
        unique_unmapped_count = unmapped_df[exercise_col].nunique()
        print(f"Found {unique_unmapped_count} unique unmapped exercises.")
    else:
        print("No unmapped exercises found.")


    # Save the unmapped rows to the output file
    try:
        unmapped_df.to_csv(output_file, sep=';', index=False)
        print(f"Unmapped exercises saved to '{output_file}'")
    except Exception as e:
        print(f"Error saving output file '{output_file}': {e}")

# --- Main method ---
if __name__ == "__main__":
    if not exercise_mappings:
        print("\nCannot run extraction because exercise_mappings dictionary is empty or failed to load.")
    else:
        extract_unmapped_exercises(
            gymrun_file='gymrun.csv',
            mapping_dict=exercise_mappings,
            output_file='unmapped.csv'
        )
