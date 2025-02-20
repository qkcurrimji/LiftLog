import pandas as pd
from dateutil.parser import parse, ParserError

def replace_data_from_excel(excel_path):
    """
    Fully replace workouts.csv and exercises.csv using the data in `excel_path`.
    This function implements a custom forward-fill for the WorkoutDate column:
      - It only updates the date when the value is parseable.
      - Non-date entries (e.g., "Chest + Back") are ignored so that the last valid date is used.
    
    Expected Excel columns:
      - WorkoutID (ignored except for forward-filling)
      - WorkoutDate (can include valid dates and notes)
      - ExerciseName
      - Reps
      - WeightKG
      
    Each row in the final CSV represents a single set (sets=1).
    Rows with missing or non-numeric Reps/WeightKG or no valid date are skipped.
    """
    # 1. Read the Excel file
    df = pd.read_excel(excel_path)

    # 2. Forward-fill WorkoutID and ExerciseName normally
    df["WorkoutID"] = df["WorkoutID"].ffill()
    df["ExerciseName"] = df["ExerciseName"].ffill()

    # 3. CUSTOM forward-fill for the date column
    #    We iterate row by row, updating last_valid_date only when the value is a parseable date.
    cleaned_dates = []
    last_valid_date = None

    for idx, row in df.iterrows():
        raw_date = row["WorkoutDate"]
        # Attempt to parse the date string
        try:
            # Using dayfirst=True for DD/MM/YYYY formats
            parsed_date = parse(str(raw_date), dayfirst=True).date()
            last_valid_date = parsed_date
        except (ParserError, ValueError, TypeError):
            # If parsing fails (e.g., "Chest + Back" or blank), do not update last_valid_date.
            pass
        # Append the last valid date (could be None if not found yet)
        cleaned_dates.append(last_valid_date)

    # Add the custom cleaned date column
    df["CleanedDate"] = cleaned_dates

    # 4. Drop rows with no valid date in CleanedDate
    df.dropna(subset=["CleanedDate"], inplace=True)

    # 5. Drop rows where Reps or WeightKG is missing
    df.dropna(subset=["Reps", "WeightKG"], inplace=True)

    # 6. Ensure Reps and WeightKG are numeric; drop any rows where conversion fails
    df["Reps"] = pd.to_numeric(df["Reps"], errors="coerce")
    df["WeightKG"] = pd.to_numeric(df["WeightKG"], errors="coerce")
    df.dropna(subset=["Reps", "WeightKG"], inplace=True)

    # 7. Build the final DataFrame for workouts.csv
    #    Each row is treated as a single set (sets=1)
    new_workouts = pd.DataFrame({
        "date": df["CleanedDate"],
        "exercise": df["ExerciseName"],
        "sets": 1,
        "reps": df["Reps"],
        "weight": df["WeightKG"]
    })

    # 8. Overwrite workouts.csv with the new data
    new_workouts.to_csv("data/workouts.csv", index=False)

    # 9. Create a fresh exercises.csv with the unique exercise names from the new data
    unique_exercises = sorted(new_workouts["exercise"].unique())
    exercises_df = pd.DataFrame({"name": unique_exercises})
    exercises_df.to_csv("data/exercises.csv", index=False)

    print("Data successfully replaced from Excel at:", excel_path)

# Example usage:
if __name__ == "__main__":
    excel_file_path = "/Users/qkcur/Downloads/Workout_Log.xlsx"  # Adjust if needed
    replace_data_from_excel(excel_file_path)
