import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime
import numpy as np
from utils import load_data, save_workout, delete_workout, get_exercise_list, import_excel_workouts, replicate_day_workouts
import io

# Page config
st.set_page_config(
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
    st.header("Log Your Workout")

    # Date selector
    selected_date = st.date_input("Workout Date", st.session_state.workout_date)

    # Exercise input form
    with st.form("workout_form"):
        exercise = st.selectbox("Select Exercise", exercises)
        col1, col2, col3 = st.columns(3)

        with col1:
            sets = st.number_input("Sets", min_value=1, max_value=10, value=3)
        with col2:
            reps = st.number_input("Reps", min_value=1, max_value=100, value=10)
        with col3:
            weight = st.number_input("Weight (kg)", min_value=0.0, max_value=500.0, value=20.0)

        submit = st.form_submit_button("Log Exercise")

        if submit:
            save_workout(selected_date, exercise, sets, reps, weight)
            st.success("Workout logged successfully!")
            st.rerun()

elif page == "History":
    st.header("Workout History")

    # Excel Import
    st.subheader("Import Workouts")
    st.markdown("""
    Please format your Excel file with these columns:
    - **date**: YYYY-MM-DD (e.g., 2025-02-20)
    - **exercise**: Must match our exercise list
    - **sets**: Number of sets
    - **reps**: Number of reps
    - **weight**: Weight in kg
    """)

    # Create example DataFrame
    example_data = pd.DataFrame({
        'date': ['2025-02-20', '2025-02-20'],
        'exercise': ['Bench Press', 'Squat'],
        'sets': [3, 4],
        'reps': [10, 8],
        'weight': [20.0, 40.0]
    })

    # Create Excel file in memory
    excel_buffer = io.BytesIO()
    example_data.to_excel(excel_buffer, index=False, engine='openpyxl')
    excel_buffer.seek(0)

    st.download_button(
        "Download Template Excel File",
        excel_buffer,
        "workout_template.xlsx",
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        key='download-template'
    )

    uploaded_file = st.file_uploader("Upload Excel File", type=['xlsx', 'xls'])
    if uploaded_file is not None:
        success, message = import_excel_workouts(uploaded_file)
        if success:
            st.success(message)
            st.rerun()
        else:
            st.error(message)

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
                    if st.button(f"Delete #{idx}", key=f"delete_{idx}"):
                        delete_workout(idx)
                        st.success("Workout deleted!")
                        st.rerun()

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