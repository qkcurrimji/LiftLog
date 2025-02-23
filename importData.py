import pandas as pd
from dateutil.parser import parse, ParserError
import streamlit as st
from supabase import create_client, Client
from datetime import datetime

# Initialize Supabase client using credentials from st.secrets
SUPABASE_URL = st.secrets["supabase"]["url"]
SUPABASE_KEY = st.secrets["supabase"]["key"]
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

def replace_data_from_excel(excel_path):
    """
    Fully replace the data in the Supabase 'workouts' and 'exercises' tables using the data
    from the provided Excel file.

    Expected Excel columns:
      - WorkoutID (ignored except for forward-filling)
      - WorkoutDate (can include valid dates and notes)
      - ExerciseName
      - Reps
      - WeightKG
      
    Each row is treated as a single set (sets = 1).
    Rows with missing or non-numeric Reps/WeightKG or no valid date are skipped.
    """
    # 1. Read the Excel file
    df = pd.read_excel(excel_path)

    # 2. Forward-fill WorkoutID and ExerciseName normally
    df["WorkoutID"] = df["WorkoutID"].ffill()
    df["ExerciseName"] = df["ExerciseName"].ffill()

    # 3. Custom forward-fill for the WorkoutDate column:
    cleaned_dates = []
    last_valid_date = None
    for idx, row in df.iterrows():
        raw_date = row["WorkoutDate"]
        try:
            # Attempt to parse the date using dayfirst=True (for DD/MM/YYYY formats)
            parsed_date = parse(str(raw_date), dayfirst=True).date()
            last_valid_date = parsed_date
        except (ParserError, ValueError, TypeError):
            # If parsing fails (e.g., "Chest + Back" or blank), do not update last_valid_date.
            pass
        cleaned_dates.append(last_valid_date)
    df["CleanedDate"] = cleaned_dates

    # 4. Drop rows with no valid date
    df.dropna(subset=["CleanedDate"], inplace=True)

    # 5. Drop rows where Reps or WeightKG is missing
    df.dropna(subset=["Reps", "WeightKG"], inplace=True)

    # 6. Ensure Reps and WeightKG are numeric; drop rows where conversion fails
    df["Reps"] = pd.to_numeric(df["Reps"], errors="coerce")
    df["WeightKG"] = pd.to_numeric(df["WeightKG"], errors="coerce")
    df.dropna(subset=["Reps", "WeightKG"], inplace=True)

    # Optionally, cast Reps to int so that values like 12.0 become 12
    df["Reps"] = df["Reps"].astype(int)
    # Sets is always 1, so we don't need to convert, but for consistency:
    df["Sets"] = 1

    # 7. Build a DataFrame with the cleaned data for insertion
    new_workouts = pd.DataFrame({
        "workout_date": df["CleanedDate"],
        "exercise": df["ExerciseName"],
        "sets": df["Sets"],
        "reps": df["Reps"],
        "weight": df["WeightKG"]
    })

    # 8. Replace data in Supabase:
    # Delete all existing rows in the workouts table.
    supabase.table("workouts").delete().neq("id", -1).execute()

    # Insert each row from new_workouts into the workouts table.
    for _, row in new_workouts.iterrows():
        data = {
            "workout_date": str(row["workout_date"]),
            "exercise": row["exercise"],
            "sets": int(row["sets"]),
            "reps": int(row["reps"]),
            "weight": row["weight"]
        }
        supabase.table("workouts").insert(data).execute()

    # Delete all existing rows in the exercises table.
    supabase.table("exercises").delete().neq("id", -1).execute()

    # Insert unique exercise names into the exercises table.
    unique_exercises = sorted(new_workouts["exercise"].unique())
    for exercise in unique_exercises:
        supabase.table("exercises").insert({"name": exercise}).execute()

    print("Data successfully imported from Excel at:", excel_path)

# Example usage:
if __name__ == "__main__":
    excel_file_path = "/Users/qkcur/Downloads/Workout_Log.xlsx"  # Adjust if needed
    replace_data_from_excel(excel_file_path)