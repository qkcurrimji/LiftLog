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
    # Convert date strings to datetime objects with flexible parsing
    df['date'] = pd.to_datetime(df['date'], format='mixed')
    return df

def save_workout(date, exercise, sets, reps, weight):
    """Save workout data to CSV file."""
    df = load_data('data/workouts.csv')
    new_workout = pd.DataFrame({
        'date': [pd.Timestamp(date)],
        'exercise': [exercise],
        'sets': [sets],
        'reps': [reps],
        'weight': [weight]
    })
    df = pd.concat([df, new_workout], ignore_index=True)
    df.to_csv('data/workouts.csv', index=False)

def import_excel_workouts(excel_file):
    """Import workouts from Excel file."""
    try:
        # Read Excel file
        df = pd.read_excel(excel_file)

        # Validate columns
        required_columns = ['date', 'exercise', 'sets', 'reps', 'weight']
        if not all(col in df.columns for col in required_columns):
            missing_cols = [col for col in required_columns if col not in df.columns]
            return False, f"Missing columns: {', '.join(missing_cols)}"

        # Convert date column
        df['date'] = pd.to_datetime(df['date'], format='mixed')

        # Load existing data
        existing_df = load_data('data/workouts.csv')

        # Combine data
        combined_df = pd.concat([existing_df, df], ignore_index=True)

        # Save combined data
        combined_df.to_csv('data/workouts.csv', index=False)

        return True, f"Successfully imported {len(df)} workouts"
    except Exception as e:
        return False, f"Error importing Excel file: {str(e)}"

def replicate_day_workouts(source_date):
    """Replicate all workouts from a specific date to today."""
    df = load_data('data/workouts.csv')

    # Get workouts from source date
    source_workouts = df[df['date'].dt.date == source_date]

    if source_workouts.empty:
        return False, "No workouts found for the selected date"

    # Create new workouts with today's date
    today = datetime.now().date()
    for _, workout in source_workouts.iterrows():
        save_workout(
            today,
            workout['exercise'],
            workout['sets'],
            workout['reps'],
            workout['weight']
        )

    return True, f"Successfully replicated {len(source_workouts)} workouts"

def delete_workout(index):
    """Delete workout entry by index."""
    df = load_data('data/workouts.csv')
    df = df.drop(index)
    df.to_csv('data/workouts.csv', index=False)

def get_exercise_list():
    """Return list of available exercises."""
    if os.path.exists('data/exercises.csv'):
        df = pd.read_csv('data/exercises.csv')
        return sorted(df['name'].tolist())
    return []

# Create data directory if it doesn't exist
os.makedirs('data', exist_ok=True)