import pandas as pd
import os
from datetime import datetime

def load_data(file_path):
    """Load workout data from CSV file."""
    if not os.path.exists(file_path):
        # Create empty DataFrame with specified columns
        df = pd.DataFrame(columns=['date', 'exercise', 'sets', 'reps', 'weight'])
        df.to_csv(file_path, index=False)
        return df

    df = pd.read_csv(file_path)
    # Convert date strings to datetime objects
    df['date'] = pd.to_datetime(df['date'])
    return df

def save_workout(date, exercise, sets, reps, weight):
    """Save workout data to CSV file."""
    df = load_data('data/workouts.csv')
    new_workout = pd.DataFrame({
        'date': [date],
        'exercise': [exercise],
        'sets': [sets],
        'reps': [reps],
        'weight': [weight]
    })
    df = pd.concat([df, new_workout], ignore_index=True)
    df.to_csv('data/workouts.csv', index=False)

def delete_workout(index):
    """Delete workout entry by index."""
    df = load_data('data/workouts.csv')
    df = df.drop(index)
    df.to_csv('data/workouts.csv', index=False)

def get_exercise_list():
    """Return list of available exercises."""
    exercises = [
        "Bench Press",
        "Squat",
        "Deadlift",
        "Shoulder Press",
        "Bent Over Row",
        "Pull-ups",
        "Push-ups",
        "Bicep Curls",
        "Tricep Extensions",
        "Leg Press"
    ]
    return sorted(exercises)

# Create data directory if it doesn't exist
os.makedirs('data', exist_ok=True)