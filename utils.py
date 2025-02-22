import pandas as pd
from datetime import datetime
import streamlit as st
from supabase import create_client, Client
from dateutil.parser import parse, ParserError

# Initialize Supabase client using credentials from st.secrets
SUPABASE_URL = st.secrets["supabase"]["url"]
SUPABASE_KEY = st.secrets["supabase"]["key"]
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

def load_data():
    """Load all workout data from the Supabase 'workouts' table as a pandas DataFrame."""
    response = supabase.table("workouts").select("*").execute()
    data = response.data
    if data is None:
        data = []
    df = pd.DataFrame(data)
    if not df.empty:
        df['workout_date'] = pd.to_datetime(df['workout_date'])
    return df

def save_workout(date, exercise, sets, reps, weight):
    """
    Insert a new workout into the Supabase 'workouts' table.
    Also, ensure that the exercise is present in the 'exercises' table.
    """
    data = {
        "workout_date": str(pd.Timestamp(date).date()),
        "exercise": exercise,
        "sets": sets,
        "reps": reps,
        "weight": weight
    }
    supabase.table("workouts").insert(data).execute()
    # Ensure the exercise exists in the exercises table
    current_exercises = get_exercise_list()
    if exercise not in current_exercises:
        supabase.table("exercises").insert({"name": exercise}).execute()

def delete_workout(workout_id):
    """Delete a workout entry from the Supabase 'workouts' table by its id."""
    supabase.table("workouts").delete().eq("id", workout_id).execute()

def get_exercise_list():
    """Retrieve the list of exercise names from the Supabase 'exercises' table."""
    response = supabase.table("exercises").select("name").execute()
    data = response.data
    if data is None:
        return []
    exercises = sorted([item["name"] for item in data])
    return exercises

def import_excel_workouts(excel_file):
    """
    Import workouts from an Excel file, clean the data, and replace all data in Supabase.
    Expected Excel columns: WorkoutID, WorkoutDate, ExerciseName, Reps, WeightKG.
    """
    try:
        df = pd.read_excel(excel_file)
        required_columns = ['WorkoutID', 'WorkoutDate', 'ExerciseName', 'Reps', 'WeightKG']
        if not all(col in df.columns for col in required_columns):
            missing_cols = [col for col in required_columns if col not in df.columns]
            return False, f"Missing columns: {', '.join(missing_cols)}. Ensure Excel has: {', '.join(required_columns)}"
        
        # Custom forward-fill for date and exercise name
        df["WorkoutID"] = df["WorkoutID"].ffill()
        df["WorkoutDate"] = df["WorkoutDate"].ffill()
        df["ExerciseName"] = df["ExerciseName"].ffill()
        
        # Drop rows with non-numeric Reps or WeightKG
        df.dropna(subset=["Reps", "WeightKG"], inplace=True)
        df["Reps"] = pd.to_numeric(df["Reps"], errors="coerce")
        df["WeightKG"] = pd.to_numeric(df["WeightKG"], errors="coerce")
        df.dropna(subset=["Reps", "WeightKG"], inplace=True)
        
        # Custom date cleaning: update date only when parseable
        cleaned_dates = []
        last_valid_date = None
        for idx, row in df.iterrows():
            raw_date = row["WorkoutDate"]
            try:
                parsed_date = parse(str(raw_date), dayfirst=True).date()
                last_valid_date = parsed_date
            except (ParserError, ValueError, TypeError):
                pass
            cleaned_dates.append(last_valid_date)
        df["CleanedDate"] = cleaned_dates
        df.dropna(subset=["CleanedDate"], inplace=True)
        
        # Replace workouts data in Supabase: delete all existing rows first
        supabase.table("workouts").delete().neq("id", -1).execute()  # deletes all rows
        
        # Insert new workouts
        for _, row in df.iterrows():
            data = {
                "workout_date": str(row["CleanedDate"]),
                "exercise": row["ExerciseName"],
                "sets": 1,  # Each row is one set
                "reps": int(row["Reps"]),
                "weight": row["WeightKG"]
            }
            supabase.table("workouts").insert(data).execute()
        
        # Replace exercises data: delete all and then insert unique exercises
        supabase.table("exercises").delete().neq("id", -1).execute()
        unique_exercises = sorted(df["ExerciseName"].unique())
        for exercise in unique_exercises:
            supabase.table("exercises").insert({"name": exercise}).execute()
        
        return True, f"Successfully imported {len(df)} workouts"
    except Exception as e:
        return False, f"Error importing Excel file: {str(e)}"

def replicate_day_workouts(source_date):
    """Replicate all workouts from a given source date to today's date."""
    df = load_data()
    source_workouts = df[df['workout_date'].dt.date == source_date]
    if source_workouts.empty:
        return False, "No workouts found for the selected date"
    today = datetime.now().date()
    for _, workout in source_workouts.iterrows():
        save_workout(today, workout['exercise'], workout['sets'], workout['reps'], workout['weight'])
    return True, f"Successfully replicated {len(source_workouts)} workouts"