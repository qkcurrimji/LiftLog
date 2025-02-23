import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime
import io
from utils import load_data, save_workout, delete_workout, get_exercise_list, import_excel_workouts, replicate_day_workouts

# Page configuration
st.set_page_config(
    page_title="Workout Logger",
    page_icon="💪",
    layout="wide"
)

# Initialize session state for selected workout date
if 'workout_date' not in st.session_state:
    st.session_state.workout_date = datetime.now().date()

# Load data from Supabase
workouts_df = load_data()
exercises = get_exercise_list()

if not workouts_df.empty:
    min_date = workouts_df['workout_date'].min()
    max_date = workouts_df['workout_date'].max()
    st.write("Minimum workout date:", min_date)
    st.write("Maximum workout date:", max_date)
else:
    st.write("No workout data loaded.")


st.title("💪 Workout Logger")

# Sidebar navigation for different pages
st.sidebar.header("Navigation")
page = st.sidebar.radio("Go to", ["Log Workout", "History", "Progress"])

if page == "Log Workout":
    st.header("Log Workout")
    
    # Common date selector for both tabs
    selected_date = st.date_input("Workout Date", st.session_state.workout_date)
    
    # Create two tabs: one for viewing and one for logging workouts
    tab_view, tab_log = st.tabs(["View Workouts", "Log Workout"])
    
    with tab_view:
        st.subheader("Today's Workouts")
        # Filter workouts by the selected date
        todays_workouts = workouts_df[workouts_df['workout_date'].dt.date == selected_date]
        
        if not todays_workouts.empty:
            # Group workouts by exercise so that multiple sets appear together
            grouped = todays_workouts.groupby('exercise')
            for exercise_name, group_df in grouped:
                with st.expander(exercise_name):
                    for _, row in group_df.iterrows():
                        col1, col2, col3 = st.columns([3, 1, 1])
                        with col1:
                            st.write(f"{row['reps']} reps @ {row['weight']} kg")
                        with col2:
                            if st.button("Edit", key=f"edit_{row['id']}"):
                                st.session_state.edit_workout = {
                                    "id": row['id'],
                                    "exercise": row['exercise'],
                                    "reps": row['reps'],
                                    "weight": row['weight']
                                }
                                st.rerun()
                        with col3:
                            if st.button("Delete", key=f"delete_{row['id']}"):
                                delete_workout(row['id'])
                                st.success("Workout deleted!")
                                st.rerun()
        else:
            st.info("No workouts found for the selected date.")
    
    with tab_log:
        # Determine if we're editing an existing workout
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
            default_index = exercises.index(default_exercise) if default_exercise in exercises else 0
            exercise = st.selectbox("Select Exercise", exercises, index=default_index)
            col1, col2 = st.columns(2)
            with col1:
                reps = st.number_input("Reps", min_value=1, max_value=100, value=default_reps)
            with col2:
                weight = st.number_input("Weight (kg)", min_value=0.0, max_value=500.0, value=default_weight)
            submit = st.form_submit_button("Save Workout")
            if submit:
                if "edit_workout" in st.session_state:
                    delete_workout(st.session_state.edit_workout["id"])
                    save_workout(selected_date, exercise, 1, reps, weight)
                    st.success("Workout updated successfully!")
                    del st.session_state.edit_workout
                else:
                    save_workout(selected_date, exercise, 1, reps, weight)
                    st.success("Workout logged successfully!")
                st.rerun()
        
        if "edit_workout" in st.session_state:
            if st.button("Cancel Edit"):
                del st.session_state.edit_workout
                st.rerun()

elif page == "History":
    st.header("Workout History")
    
    # Option to choose between last 45 days vs. all data
    show_all = st.checkbox("Show all data", value=False)
    # Load data based on the checkbox: if show_all is True, load all; otherwise, last 45 days only.
    workouts_df = load_data(last_45_days=not show_all)
    
    col1, col2 = st.columns(2)
    with col1:
        exercise_filter = st.selectbox("Filter by Exercise", ["All"] + get_exercise_list())
    with col2:
        # Set the date range picker based on the loaded data
        if not workouts_df.empty:
            min_date = workouts_df['workout_date'].min().date()
        else:
            min_date = datetime.now().date()
        date_range = st.date_input(
            "Date Range",
            [min_date, datetime.now().date()]
        )
    
    filtered_df = workouts_df.copy()
    if exercise_filter != "All":
        filtered_df = filtered_df[filtered_df['exercise'] == exercise_filter]
    if not filtered_df.empty:
        filtered_df = filtered_df[
            (filtered_df['workout_date'].dt.date >= date_range[0]) &
            (filtered_df['workout_date'].dt.date <= date_range[1])
        ]
    
    if not filtered_df.empty:
        dates = filtered_df['workout_date'].dt.date.unique()
        for date in sorted(dates, reverse=True):
            day_workouts = filtered_df[filtered_df['workout_date'].dt.date == date]
            with st.expander(f"Workouts on {date}"):
                if st.button(f"Replicate All Workouts from {date}", key=f"replicate_day_{date}"):
                    success, message = replicate_day_workouts(date)
                    if success:
                        st.success(message)
                        st.rerun()
                    else:
                        st.error(message)
                for _, row in day_workouts.iterrows():
                    st.write(f"**{row['exercise']}**: {row['sets']} sets × {row['reps']} reps @ {row['weight']} kg")
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
    exercise_progress = st.selectbox("Select Exercise to Track", exercises)
    exercise_data = workouts_df[workouts_df['exercise'] == exercise_progress]
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
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Max Weight", f"{exercise_data['weight'].max():.1f} kg")
        with col2:
            st.metric("Average Weight", f"{exercise_data['weight'].mean():.1f} kg")
        with col3:
            st.metric("Total Workouts", len(exercise_data))
    else:
        st.info("No data available for the selected exercise.")
