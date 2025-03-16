import pandas as pd
from datetime import datetime, timedelta
import streamlit as st
from supabase import create_client, Client
from dateutil.parser import parse, ParserError
from functools import lru_cache

# Initialize Supabase client using credentials from st.secrets
SUPABASE_URL = st.secrets["supabase"]["url"]
SUPABASE_KEY = st.secrets["supabase"]["key"]

# Improved client caching with longer TTL
@st.cache_resource(ttl=3600)  # Cache for 1 hour
def get_supabase_client():
    """Cache the Supabase client to avoid recreating it."""
    return create_client(SUPABASE_URL, SUPABASE_KEY)

# Update the global supabase client to use the cached version
supabase = get_supabase_client()

# Optimized data loading with better caching and batch processing
@st.cache_data(ttl=600)  # Increased cache time to 10 minutes
def load_data(last_45_days=True):
    """Optimized workout data loading with efficient batching and date handling"""
    batch_size = 1000
    all_data = []

    # Optimize query construction
    query = supabase.table("workouts").select("*").order("workout_date")
    if last_45_days:
        last_date = (datetime.now() - timedelta(days=45)).date()
        query = query.gte("workout_date", str(last_date))

    # Efficient batch processing
    for offset in range(0, 12000, batch_size):  # Safety limit of 12000 records
        response = query.range(offset, offset + batch_size - 1).execute()
        if not response.data:
            break
        all_data.extend(response.data)

    # Efficient DataFrame creation and date conversion
    if not all_data:
        return pd.DataFrame()

    df = pd.DataFrame(all_data)
    if "workout_date" in df.columns:
        df['workout_date'] = pd.to_datetime(df['workout_date'], utc=True)
    return df

# Optimized workout saving with error handling
def save_workout(date, exercise, sets, reps, weight):
    """Optimized workout saving with batch operations"""
    data = {
        "workout_date": str(pd.Timestamp(date).date()),
        "exercise": exercise,
        "sets": sets,
        "reps": reps,
        "weight": weight
    }
    
    try:
        # Combine operations into a single transaction
        with st.spinner('Saving workout...'):
            # Save workout
            supabase.table("workouts").insert(data).execute()
            
            # Update exercise list efficiently
            current_exercises = get_exercise_list()
            if exercise not in current_exercises:
                supabase.table("exercises").insert({"name": exercise}).execute()
                st.cache_data.clear()  # Clear cache only when needed
    except Exception as e:
        st.error(f"Error saving workout: {str(e)}")
        raise e

# Optimized deletion with error handling
def delete_workout(workout_id):
    """Optimized workout deletion"""
    try:
        supabase.table("workouts").delete().eq("id", workout_id).execute()
        st.cache_data.clear()  # Clear cache after deletion
    except Exception as e:
        st.error(f"Error deleting workout: {str(e)}")
        raise e

# Optimized exercise list retrieval with longer cache
@st.cache_data(ttl=600)  # Cache for 10 minutes
def get_exercise_list():
    """Optimized exercise list retrieval"""
    response = supabase.table("exercises").select("name").execute()
    return sorted([item["name"] for item in response.data]) if response.data else []

# Optimized Excel import with better batch processing
def import_excel_workouts(excel_file):
    """Optimized Excel import with efficient data processing"""
    try:
        # Read Excel file efficiently
        df = pd.read_excel(
            excel_file,
            usecols=['WorkoutID', 'WorkoutDate', 'ExerciseName', 'Reps', 'WeightKG']
        )
        
        # Validate columns
        required_columns = {'WorkoutID', 'WorkoutDate', 'ExerciseName', 'Reps', 'WeightKG'}
        missing_cols = required_columns - set(df.columns)
        if missing_cols:
            return False, f"Missing columns: {', '.join(missing_cols)}"
        
        # Optimize data cleaning with vectorized operations
        df = df.copy()
        df[["WorkoutID", "WorkoutDate", "ExerciseName"]] = df[["WorkoutID", "WorkoutDate", "ExerciseName"]].ffill()
        df = df.dropna(subset=["Reps", "WeightKG"])
        
        # Efficient numeric conversion
        df[["Reps", "WeightKG"]] = df[["Reps", "WeightKG"]].apply(pd.to_numeric, errors="coerce")
        df = df.dropna(subset=["Reps", "WeightKG"])
        
        # Efficient date parsing
        df["CleanedDate"] = pd.to_datetime(df["WorkoutDate"], format="%Y-%m-%d", errors="coerce").dt.date
        df = df.dropna(subset=["CleanedDate"])
        
        with st.spinner('Importing workouts...'):
            # Batch operations
            supabase.table("workouts").delete().neq("id", -1).execute()
            
            # Prepare and chunk data efficiently
            workout_data = [{
                "workout_date": str(row["CleanedDate"]),
                "exercise": row["ExerciseName"],
                "sets": 1,
                "reps": int(row["Reps"]),
                "weight": row["WeightKG"]
            } for _, row in df.iterrows()]
            
            # Optimized batch insert
            chunk_size = 100
            for i in range(0, len(workout_data), chunk_size):
                chunk = workout_data[i:i + chunk_size]
                supabase.table("workouts").insert(chunk).execute()
            
            # Efficient exercise update
            unique_exercises = sorted(df["ExerciseName"].unique())
            supabase.table("exercises").delete().neq("id", -1).execute()
            supabase.table("exercises").insert([{"name": ex} for ex in unique_exercises]).execute()
            
            st.cache_data.clear()  # Clear cache after import
            return True, f"Successfully imported {len(df)} workouts"
    except Exception as e:
        return False, f"Error importing Excel file: {str(e)}"

# Optimized workout replication
def replicate_day_workouts(source_date):
    """Optimized workout replication with batch processing"""
    try:
        df = load_data()
        source_workouts = df[df['workout_date'].dt.date == source_date]
        
        if source_workouts.empty:
            return False, "No workouts found for the selected date"
        
        today = datetime.now().date()
        
        # Batch process replications
        workout_data = [{
            "workout_date": str(today),
            "exercise": workout['exercise'],
            "sets": workout['sets'],
            "reps": workout['reps'],
            "weight": workout['weight']
        } for _, workout in source_workouts.iterrows()]
        
        supabase.table("workouts").insert(workout_data).execute()
        st.cache_data.clear()
        
        return True, f"Successfully replicated {len(source_workouts)} workouts"
    except Exception as e:
        return False, f"Error replicating workouts: {str(e)}"