import streamlit as st
import pandas as pd
import plotly.express as px

async def metrics_page():
    st.title("Learning Metrics")
    
    # Sample metrics data (replace with actual data)
    metrics_data = {
        "Courses Completed": 5,
        "Total Learning Hours": 25,
        "Average Score": 85,
        "Courses in Progress": 2
    }
    
    # Display key metrics
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Courses Completed", metrics_data["Courses Completed"])
    col2.metric("Learning Hours", metrics_data["Total Learning Hours"])
    col3.metric("Average Score", f"{metrics_data['Average Score']}%")
    col4.metric("In Progress", metrics_data["Courses in Progress"])
    
    # Progress over time chart
    st.subheader("Learning Progress Over Time")
    progress_data = pd.DataFrame({
        'Date': pd.date_range(start='2024-01-01', periods=10, freq='W'),
        'Completed Courses': range(1, 11),
        'Learning Hours': [5, 8, 12, 15, 20, 22, 25, 28, 30, 35]
    })
    
    fig = px.line(progress_data, x='Date', y=['Completed Courses', 'Learning Hours'])
    st.plotly_chart(fig)
    
    # Recent activity
    st.subheader("Recent Activity")
    activities = [
        "Completed 'Python Basics' course",
        "Started 'Advanced ML' course",
        "Earned 'Python Developer' certificate",
        "Completed assessment with 90% score"
    ]
    
    for activity in activities:
        st.write(f"• {activity}") 