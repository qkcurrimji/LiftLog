import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime
import numpy as np
from utils import load_data, save_workout, delete_workout, get_exercise_list, import_excel_workouts, replicate_day_workouts
import io

# Page config
st.set_page_config (
    page_title="Workout Logger",
    page_icon="💪",
    layout="wide"
)

# Initialize session state
if 'workout_date' not in st.session_state:
    st.session_state.workout_date = datetime.now().date()

# Load data
workouts_df = load_data('data/workouts.csv')
exercises = get_exercise_list()

# Main title
st.title("💪 Workout Logger")

# Sidebar
st.sidebar.header("Navigation")
page = st.sidebar.radio("Go to", ["Log Workout", "History", "Progress"])

if page == "Log Workout":
    st.header("Log Workout")
    
    # Date selector
    selected_date = st.date_input("Workout Date", st.session_state.workout_date)
    
    # Create tabs
    tab_view, tab_log = st.tabs(["View Workouts", "Log Workout"])
    
    with tab_view:
        st.subheader("Today's Workouts")
        # Filter workouts for the selected date
        todays_workouts = workouts_df[workouts_df['date'].dt.date == selected_date]
        
        if not todays_workouts.empty:
            # Group by exercise so multiple sets of the same exercise are shown together
            grouped = todays_workouts.groupby('exercise')
            
            for exercise_name, group_df in grouped:
                # Each exercise gets its own expander
                with st.expander(exercise_name):
                    # Display each set (row) for this exercise
                    for idx, row in group_df.iterrows():
                        # Create columns for set info + edit/delete buttons
                        col1, col2, col3 = st.columns([3, 1, 1])
                        with col1:
                            st.write(f"{row['reps']} reps @ {row['weight']} kg")
                        with col2:
                            if st.button("Edit", key=f"edit_{idx}"):
                                st.session_state.edit_workout = {
                                    "index": idx,
                                    "exercise": row['exercise'],
                                    "reps": row['reps'],
                                    "weight": row['weight']
                                }
                                st.rerun()
                        with col3:
                            if st.button("Delete", key=f"delete_{idx}"):
                                delete_workout(idx)
                                st.success("Workout deleted!")
                                st.rerun()
        else:
            st.info("No workouts found for the selected date.")
    
    with tab_log:
        # Check if editing an existing workout
        if "edit_workout" in st.session_state:
            edit_data = st.session_state.edit_workout
            default_exercise = edit_data["exercise"]
            default_reps = int(edit_data["reps"])
            default_weight = float(edit_data["weight"])
            form_title = "Edit Workout"
        else:
            default_exercise = exercises[0] if exercises else ""
            default_reps = 10
            default_weight = 20.0
            form_title = "Log New Workout"
        
        with st.form("workout_form"):
            st.subheader(form_title)
            if default_exercise in exercises:
                default_index = exercises.index(default_exercise)
            else:
                default_index = 0
            
            exercise = st.selectbox("Select Exercise", exercises, index=default_index)
            col1, col2 = st.columns(2)
            with col1:
                reps = st.number_input("Reps", min_value=1, max_value=100, value=default_reps)
            with col2:
                weight = st.number_input("Weight (kg)", min_value=0.0, max_value=500.0, value=default_weight)
            
            submit = st.form_submit_button("Save Workout")
            if submit:
                if "edit_workout" in st.session_state:
                    # Update existing workout (delete + re-save)
                    index_to_edit = st.session_state.edit_workout["index"]
                    delete_workout(index_to_edit)
                    save_workout(selected_date, exercise, 1, reps, weight)
                    st.success("Workout updated successfully!")
                    del st.session_state.edit_workout
                else:
                    # Log new workout
                    save_workout(selected_date, exercise, 1, reps, weight)
                    st.success("Workout logged successfully!")
                st.rerun()
        
        if "edit_workout" in st.session_state:
            if st.button("Cancel Edit"):
                del st.session_state.edit_workout
                st.rerun()

elif page == "History":
    st.header("Workout History")

    # Filters
    col1, col2 = st.columns(2)
    with col1:
        exercise_filter = st.selectbox("Filter by Exercise", ["All"] + exercises)
    with col2:
        date_range = st.date_input(
            "Date Range",
            [workouts_df['date'].min().date() if not workouts_df.empty else datetime.now().date(),
             datetime.now().date()]
        )

    # Filter data
    filtered_df = workouts_df.copy()
    if exercise_filter != "All":
        filtered_df = filtered_df[filtered_df['exercise'] == exercise_filter]
    filtered_df = filtered_df[
        (filtered_df['date'].dt.date >= date_range[0]) &
        (filtered_df['date'].dt.date <= date_range[1])
    ]

    # Group workouts by date
    if not filtered_df.empty:
        dates = filtered_df['date'].dt.date.unique()
        for date in sorted(dates, reverse=True):
            day_workouts = filtered_df[filtered_df['date'].dt.date == date]

            with st.expander(f"Workouts on {date}"):
                # Add replicate day button
                if st.button(f"Replicate All Workouts from {date}", key=f"replicate_day_{date}"):
                    success, message = replicate_day_workouts(date)
                    if success:
                        st.success(message)
                        st.rerun()
                    else:
                        st.error(message)

                # Display workouts for this day
                for idx, row in day_workouts.iterrows():
                    st.write(f"**{row['exercise']}**: {row['sets']} sets × {row['reps']} reps @ {row['weight']} kg")
                    # if st.button(f"Delete #{idx}", key=f"delete_{idx}"):
                    #     delete_workout(idx)
                    #     st.success("Workout deleted!")
                    #     st.rerun()

        # Export functionality
        st.download_button(
            "Download History as CSV",
            filtered_df.to_csv(index=False).encode('utf-8'),
            "workout_history.csv",
            "text/csv",
            key='download-csv'
        )
    else:
        st.info("No workouts found for the selected filters.")

elif page == "Progress":
    st.header("Progress Tracking")

    # Exercise selector for progress
    exercise_progress = st.selectbox("Select Exercise to Track", exercises)

    # Filter data for selected exercise
    exercise_data = workouts_df[workouts_df['exercise'] == exercise_progress]

    if not exercise_data.empty:
        # Create progress chart
        fig = px.line(
            exercise_data,
            x='date',
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

        # Statistics
        st.subheader("Statistics")
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric(
                "Max Weight",
                f"{exercise_data['weight'].max():.1f} kg"
            )
        with col2:
            st.metric(
                "Average Weight",
                f"{exercise_data['weight'].mean():.1f} kg"
            )
        with col3:
            st.metric(
                "Total Workouts",
                len(exercise_data)
            )
    else:
        st.info("No data available for the selected exercise.")