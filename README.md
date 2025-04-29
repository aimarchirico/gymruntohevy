# GymRun to Hevy

## Purpose

This project provides Python scripts to convert workout data exported from the **[GymRun](https://www.gymrun.app/)** app (in CSV format) into the format used by the **[Strong](https://www.strong.app/)** app. This is primarily useful for users who want to import their historical GymRun data into the **[Hevy](https://www.hevyapp.com/)** app, as Hevy currently supports importing data directly from Strong's CSV format but not from GymRun's.

By converting your `gymrun.csv` export to a Strong-compatible format, you can then use Hevy's import feature to bring your workout history across.

## Files

*   **`convert.py`**:
    *   This is the main script for performing the conversion.
    *   It reads the `gymrun.csv` file.
    *   It reads an example `strong.csv` file to fetch the required headers and format.
    *   It processes the GymRun data:
        *   Parses dates and times, converting them from the local timezone (assumed Europe/Oslo in the script, adjust if needed) to UTC.
        *   Groups exercises into workouts based on date.
        *   Calculates the start time, end time, and total duration for each workout.
        *   Assigns a sequential workout number.
        *   Maps GymRun column names (e.g., `Routine`, `Set`, `Weight`) to Strong column names (e.g., `Workout Name`, `Set Order`, `Weight (kg)`).
        *   Handles cardio/timed exercises by mapping GymRun's `Duration` (assumed minutes) to Strong's `Seconds` column and GymRun's `Distance` (assumed km) to Strong's `Distance (meters)` column.
        *   Uses the `exercise_mappings` dictionary from `mappings.py` to rename exercises to match Hevy naming conventions to limit how many custom exercises are created when imported into Hevy.
        *   Ensures all necessary Strong columns are present and have correct data types.
    *   Outputs the converted data to a new CSV file (`converted.csv`) in the Strong format, ready for import into Hevy.

*   **`mappings.py`**:
    *   This file contains the `exercise_mappings` Python dictionary.
    *   **Crucial:** You need to edit this file to define how exercise names from your GymRun export should be translated to the names used in Hevy.
    *   The keys of the dictionary should be the exact exercise names from your `gymrun.csv`.
    *   The values should be the corresponding exercise names you want in the final output (matching Hevy's exercise names is recommended to prevent custom exercises from being created).

*   **`exercises.py`**:
    *   This is a helper script.
    *   It reads your `gymrun.csv` and your `mappings.py`.
    *   It identifies which exercises listed in `gymrun.csv` are *not* yet included as keys in your `exercise_mappings` dictionary in `mappings.py`.
    *   It outputs a new CSV file (`unmapped.csv`) containing only the rows with unmapped exercises.
    *   This helps you easily see which exercises you still need to add to your `mappings.py` file.

*   **`gymrun.csv`**:
    *   An example CSV file exported from the GymRun app. Place your own export here and rename it or update the script accordingly.

*   **`strong.csv`**:
    *   An example CSV file showing the target format required when importing to Hevy. The `convert.py` script uses this file to get the correct header names and order.

*   **`converted.csv`** (Generated):
    *   The output file created by `convert.py`. This file should be suitable for importing into the Hevy app.

*   **`unmapped.csv`** (Generated):
    *   The output file created by `exercises.py`, listing exercises you still need to map.

## How to Use

1.  **Export Data**: Export your workout history from the GymRun app as a CSV file. Save it in this project directory as `gymrun.csv` (or update the filename in the scripts).
2.  **Install Libraries**: Make sure you have Python 3 installed and install all required libraries: 
    ```bash
    pip install -r requirements.txt
    ```
3.  **Map Exercises**:
    *   Run the helper script to find unmapped exercises:
        ```bash
        python exercises.py
        ```
    *   Open the generated `unmapped.csv` to see which exercises need mapping.
    *   Edit the `mappings.py` file. Add entries to the `exercise_mappings` dictionary for each exercise listed in the unmapped file. The key is the GymRun name, and the value is the desired Hevy name.
    *   Repeat this step until `exercises.py` reports 0 unique unmapped exercises or you have mapped all exercises you care about.
4.  **Run Conversion**: Execute the main conversion script:
    ```bash
    python convert.py
    ```
5.  **Import to Hevy**: The script will create `converted.csv`. Use the import function within the Hevy app and select this generated file.

**Note**: Verify the timezone (`Europe/Oslo`) in `convert.py` matches your local timezone where the GymRun data was recorded. Adjust if necessary. Also, double-check the assumptions about units (minutes for Duration, km for Distance) match your GymRun export. Also double-check assumptions made about some of the exercise mappings in `mappings.py`. 
