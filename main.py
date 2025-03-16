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
if 'current_exercise' not in st.session_state:
    st.session_state.current_exercise = ""
if 'current_reps' not in st.session_state:
    st.session_state.current_reps = 10
if 'current_weight' not in st.session_state:
    st.session_state.current_weight = 20.0

# 1. Optimize caching strategy
@st.cache_data(ttl=600)  # Increased cache time to 10 minutes
def get_cached_exercise_list():
    return get_exercise_list()

@st.cache_data(ttl=600)  # Increased cache time
def get_cached_workouts(last_45_days=False):
    """Cache the entire workout dataset"""
    return load_data(last_45_days=last_45_days)

# 2. Optimize filtering function
@st.cache_data(ttl=600)
def get_filtered_workouts(df, exercise_filter, start_date, end_date):
    """Optimized filtering with better pandas operations"""
    if df.empty:
        return df
        
    mask = pd.Series(True, index=df.index)
    
    if exercise_filter != "All":
        mask &= df['exercise'] == exercise_filter
    
    if start_date and end_date:
        mask &= (df['workout_date'].dt.date >= start_date) & \
                (df['workout_date'].dt.date <= end_date)
    
    return df[mask]

# 3. Load data more efficiently
def load_page_data(page):
    """Efficiently load data based on page requirements"""
    if page == "Progress":
        return get_cached_workouts(last_45_days=False)
    return get_cached_workouts(last_45_days=not st.session_state.show_all_data)

st.title("Workout Logger")

# Sidebar navigation
st.sidebar.header("Navigation")
page = st.sidebar.radio("Navigation", ["Log Workout", "History", "Progress"], label_visibility="collapsed")

# 4. Load data once and cache
workouts_df = load_page_data(page)
exercises = get_cached_exercise_list()

if page == "Log Workout":
    st.header("Log Workout")
    
    selected_date = st.date_input("Workout Date", st.session_state.workout_date)
    
    # Replace tabs with a session state–controlled radio button
    active_view = st.radio(
        "Select View",
        options=["View Workouts", "Log Workout"],
        index=1 if st.session_state.get("active_view", "Log Workout") == "Log Workout" else 0,
        label_visibility="collapsed"
    )
    st.session_state.active_view = active_view

    if active_view == "View Workouts":
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

    elif active_view == "Log Workout":
        if "edit_workout" in st.session_state:
            edit_data = st.session_state.edit_workout
            default_exercise = edit_data["exercise"]
            default_reps = int(edit_data["reps"])
            default_weight = float(edit_data["weight"])
            form_title = "Edit Workout"
        else:
            default_exercise = st.session_state.current_exercise
            default_reps = st.session_state.current_reps
            default_weight = st.session_state.current_weight
            form_title = "Log New Workout"
        
        st.subheader(form_title)
        
        exercise = custom_autocomplete(
            "Exercise Name",
            exercises,
            key="workout_exercise",
            default=default_exercise
        )
        
        with st.form("workout_form", clear_on_submit=False):
            st.write("Selected Exercise:", exercise)
            col1, col2 = st.columns(2)
            
            # For reps: only provide the default value on first render
            if "reps_input" not in st.session_state:
                reps = st.number_input("Reps", min_value=1, max_value=100, value=default_reps, key="reps_input")
            else:
                reps = st.number_input("Reps", min_value=1, max_value=100, key="reps_input")
            
            # For weight: only provide the default value on first render
            if "weight_input" not in st.session_state:
                weight = st.number_input("Weight (kg)", min_value=0.0, max_value=500.0, value=default_weight, step=0.5, key="weight_input")
            else:
                weight = st.number_input("Weight (kg)", min_value=0.0, max_value=500.0, step=0.5, key="weight_input")
            
            submitted = st.form_submit_button("Save Workout")
            if submitted:
                exercise_clean = exercise.strip()
                if not exercise_clean:
                    st.error("Please enter an exercise name")
                    st.stop()
                
                exercise_clean = exercise_clean.title()
                
                if "edit_workout" in st.session_state:
                    delete_workout(st.session_state.edit_workout["id"])
                    del st.session_state.edit_workout
                
                # Update session state with the current widget values
                st.session_state.current_exercise = exercise_clean
                st.session_state.current_reps = reps
                st.session_state.current_weight = weight
                
                # Save the workout with the current input values
                save_workout(selected_date, exercise_clean, 1, reps, weight)
                st.cache_data.clear()
                st.success(f"Set logged for {exercise_clean}")

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
    
    # Get all-time exercise data and sort by date
    exercise_data = get_filtered_workouts(
        workouts_df, 
        exercise_progress,
        None,  # Removed date filtering to show lifetime data
        None
    ).sort_values('workout_date')
    
    if not exercise_data.empty:
        # Create the progress chart
        fig = px.line(
            exercise_data,
            x='workout_date',
            y='weight',
            title=f'Lifetime Progress for {exercise_progress}',
            markers=True,
            height=600
        )
        
        # Update layout with improved x-axis formatting
        fig.update_layout(
            title_x=0.5,
            title_font_size=24,
            plot_bgcolor='white',
            paper_bgcolor='white',
            xaxis=dict(
                showgrid=True,
                gridwidth=1,
                gridcolor='#f1f5f9',
                tickfont=dict(size=14),
                type='date',
                tickformat='%Y-%m-%d',  # Show full date
                dtick='D1',  # Show daily ticks
                tickangle=45  # Angle the dates for better readability
            ),
            yaxis=dict(
                showgrid=True,
                gridwidth=1,
                gridcolor='#f1f5f9',
                tickfont=dict(size=14)
            ),
            xaxis_title="Date",
            yaxis_title="Weight (kg)",
            showlegend=False,
            hovermode='x unified',
            margin=dict(l=50, r=50, t=80, b=70)  # Increased bottom margin for date labels
        )
        
        # Update traces with improved hover information
        fig.update_traces(
            line_color='#3b82f6',
            line_width=3,
            marker=dict(
                size=10,
                color='#0f172a'
            ),
            hovertemplate="<br>".join([
                "Date: %{x|%Y-%m-%d}",
                "Weight: %{y:.1f} kg",
                "Day: %{x|%A}<extra></extra>"  # Added day of week
            ])
        )
        
        st.plotly_chart(fig, use_container_width=True)
        
        # Show lifetime statistics
        st.subheader("Lifetime Statistics")
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Max Weight", f"{exercise_data['weight'].max():.1f} kg")
        col2.metric("Average Weight", f"{exercise_data['weight'].mean():.1f} kg")
        col3.metric("Total Workouts", len(exercise_data))
        
        # Calculate lifetime progress
        if len(exercise_data) >= 2:
            first_weight = exercise_data.iloc[0]['weight']
            last_weight = exercise_data.iloc[-1]['weight']
            progress = last_weight - first_weight
            col4.metric("Overall Progress", f"{progress:+.1f} kg", 
                       delta=f"{(progress/first_weight)*100:+.1f}%")
        
        # Show detailed history
        with st.expander("Show Detailed History"):
            history_df = exercise_data[['workout_date', 'weight', 'reps']].copy()
            history_df['workout_date'] = history_df['workout_date'].dt.date
            st.dataframe(
                history_df.sort_values('workout_date', ascending=False),
                use_container_width=True,
                hide_index=True
            )
    else:
        st.info("No data available for the selected exercise.")