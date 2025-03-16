import streamlit as st

st.set_page_config(
    page_title="Workout Logger",
    page_icon="💪",
    layout="wide"
)

with open('.streamlit/style.css') as f:
    st.markdown(f'<style>{f.read()}</style>', unsafe_allow_html=True)

import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta
import io
from utils import load_data, save_workout, delete_workout, get_exercise_list, import_excel_workouts, replicate_day_workouts


def custom_autocomplete(label, options, key=None, default=""):
    """
    Custom autocomplete component with improved layout and styling.
    """
    # Ensure options is not empty and is a list
    options = sorted(list(set(options))) if options else ["No exercises found"]

    # Create a container with custom styling
    with st.container():
        # Input type selection with better layout
        input_type = st.radio(
            "Choose input type:",
            options=["New Exercise", "Select Existing"],
            key=f"{key}_type",
            horizontal=True,
            label_visibility="collapsed"  # Hides the label for cleaner layout
        )
        
        # Add some spacing
        st.write("")
        
        # Main input area
        if input_type == "Select Existing":
            value = st.selectbox(
                label,
                options=options,
                key=f"{key}_select",
                index=options.index(default) if default in options else 0
            )
        else:
            value = st.text_input(
                label,
                value=default if default not in options else "",
                key=f"{key}_input",
                placeholder="Type new exercise name"
            )
    
    return value

# Initialize session state variables
if 'workout_date' not in st.session_state:
    st.session_state.workout_date = datetime.now().date()
if 'show_all_data' not in st.session_state:
    st.session_state.show_all_data = False
if 'current_exercise_filter' not in st.session_state:
    st.session_state.current_exercise_filter = "All"

@st.cache_data(ttl=300)
def get_filtered_workouts(df, exercise_filter, start_date, end_date):
    """Cache filtered workout data to avoid recomputation"""
    filtered = df.copy()
    if exercise_filter != "All":
        filtered = filtered[filtered['exercise'] == exercise_filter]
    if start_date and end_date:
        filtered = filtered[
            (filtered['workout_date'].dt.date >= start_date) &
            (filtered['workout_date'].dt.date <= end_date)
        ]
    return filtered

# Load data once at the start
workouts_df = load_data(last_45_days=not st.session_state.show_all_data)
exercises = get_exercise_list()

st.title("Workout Logger")

# Sidebar navigation
st.sidebar.header("Navigation")
page = st.sidebar.radio("Go to", ["Log Workout", "History", "Progress"])

if page == "Log Workout":
    st.header("Log Workout")
    
    selected_date = st.date_input("Workout Date", st.session_state.workout_date)
    
    tab_view, tab_log = st.tabs(["View Workouts", "Log Workout"])
    
    with tab_view:
        st.subheader("Today's Workouts")
        todays_workouts = get_filtered_workouts(workouts_df, "All", selected_date, selected_date)
        
        if not todays_workouts.empty:
            for exercise_name, group_df in todays_workouts.groupby('exercise'):
                with st.expander(exercise_name):
                    for _, row in group_df.iterrows():
                        cols = st.columns([3, 1, 1])
                        cols[0].write(f"{row['reps']} reps @ {row['weight']} kg")
                        if cols[1].button("Edit", key=f"edit_{row['id']}"):
                            st.session_state.edit_workout = {
                                "id": row['id'],
                                "exercise": row['exercise'],
                                "reps": row['reps'],
                                "weight": row['weight']
                            }
                            st.rerun()
                        if cols[2].button("Delete", key=f"delete_{row['id']}"):
                            delete_workout(row['id'])
                            st.cache_data.clear()
                            st.rerun()
        else:
            st.info("No workouts found for the selected date.")
    
    with tab_log:
            if "edit_workout" in st.session_state:
                edit_data = st.session_state.edit_workout
                default_exercise = edit_data["exercise"]
                default_reps = int(edit_data["reps"])
                default_weight = float(edit_data["weight"])
                form_title = "Edit Workout"
            else:
                default_exercise = ""
                default_reps = 10
                default_weight = 20.0
                form_title = "Log New Workout"
            
            st.subheader(form_title)
            
            exercise = custom_autocomplete(
                "Exercise Name",
                exercises,
                key="workout_exercise",
                default=default_exercise
            )
            with st.form("workout_form", clear_on_submit=True):
                st.write("Selected Exercise:", exercise)
                col1, col2 = st.columns(2)
                with col1:
                    reps = st.number_input("Reps", min_value=1, max_value=100, value=default_reps)
                with col2:
                    weight = st.number_input("Weight (kg)", min_value=0.0, max_value=500.0, value=default_weight)
                
                submitted = st.form_submit_button("Save Workout")
                if submitted:
                    # Validate and clean exercise name
                    exercise_clean = exercise.strip()
                    if not exercise_clean:
                        st.error("Please enter an exercise name")
                        st.stop()
                    
                    # Title case the exercise name for consistency
                    exercise_clean = exercise_clean.title()
                    
                    if "edit_workout" in st.session_state:
                        delete_workout(st.session_state.edit_workout["id"])
                    save_workout(selected_date, exercise_clean, 1, reps, weight)
                    st.cache_data.clear()
                    if "edit_workout" in st.session_state:
                        del st.session_state.edit_workout
                    st.success("Workout saved successfully!")
                    st.rerun()  

elif page == "History":
    st.header("Workout History")
    
    show_all = st.checkbox("Show all data", value=st.session_state.show_all_data)
    if show_all != st.session_state.show_all_data:
        st.session_state.show_all_data = show_all
        st.rerun()
    
    col1, col2 = st.columns(2)
    with col1:
        exercise_filter = st.selectbox("Filter by Exercise", ["All"] + exercises)
    with col2:
        if not workouts_df.empty:
            min_date = workouts_df['workout_date'].min().date()
            max_date = workouts_df['workout_date'].max().date()
        else:
            min_date = max_date = datetime.now().date()
        date_range = st.date_input("Date Range", [min_date, max_date])
    
    filtered_df = get_filtered_workouts(
        workouts_df,
        exercise_filter,
        date_range[0] if len(date_range) > 0 else None,
        date_range[1] if len(date_range) > 1 else None
    )
    
    if not filtered_df.empty:
        dates = filtered_df['workout_date'].dt.date.unique()
        for date in sorted(dates, reverse=True):
            day_workouts = filtered_df[filtered_df['workout_date'].dt.date == date]
            with st.expander(f"Workouts on {date}"):
                if st.button(f"Replicate All Workouts from {date}", key=f"replicate_day_{date}"):
                    success, message = replicate_day_workouts(date)
                    if success:
                        st.cache_data.clear()
                        st.success(message)
                        st.rerun()
                    else:
                        st.error(message)
                for _, row in day_workouts.iterrows():
                    st.write(f"**{row['exercise']}**: {row['sets']} sets × {row['reps']} reps @ {row['weight']} kg")
        
        csv = filtered_df.to_csv(index=False).encode('utf-8')
        st.download_button(
            "Download History as CSV",
            csv,
            "workout_history.csv",
            "text/csv",
            key='download-csv'
        )
    else:
        st.info("No workouts found for the selected filters.")

elif page == "Progress":
    st.header("Progress Tracking")
    
    exercise_progress = st.selectbox("Select Exercise to Track", exercises)
    exercise_data = get_filtered_workouts(workouts_df, exercise_progress, None, None)
    
    if not exercise_data.empty:
        fig = px.line(
            exercise_data,
            x='workout_date',
            y='weight',
            title=f'Progress for {exercise_progress}',
            markers=True
        )
        fig.update_layout(
            xaxis_title="Date",
            yaxis_title="Weight (kg)",
            showlegend=False
        )
        st.plotly_chart(fig, use_container_width=True)
        
        st.subheader("Statistics")
        metrics = st.columns(3)
        metrics[0].metric("Max Weight", f"{exercise_data['weight'].max():.1f} kg")
        metrics[1].metric("Average Weight", f"{exercise_data['weight'].mean():.1f} kg")
        metrics[2].metric("Total Workouts", len(exercise_data))
    else:
        st.info("No data available for the selected exercise.")