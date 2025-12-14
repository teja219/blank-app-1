import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
import pandas as pd
from datetime import datetime, date, timedelta
import json

# Page configuration
st.set_page_config(
    page_title="Our Adventure Together",
    page_icon="💕",
    layout="wide"
)

# Custom CSS — cute pink / girly theme
st.markdown("""
<style>
  :root{
    --pink-1: #fff0f6;
    --pink-2: #ffd6e7;
    --accent: #f472b6;
    --muted: #6b7280;
  }

  /* Page background */
  section[data-testid="stAppViewContainer"] {
    background: linear-gradient(180deg, var(--pink-1) 0%, var(--pink-2) 100%);
    background-attachment: fixed;
    padding: 2rem 1rem;
  }

  /* Main content container — slightly translucent to show pink hue */
  .block-container {
    background: rgba(255,245,250,0.9) !important;
    border-radius: 16px;
    padding: 1.25rem 1.5rem;
    box-shadow: 0 8px 30px rgba(244,114,182,0.08);
  }

  /* Header with cute styling */
  .main-header {
    background: linear-gradient(90deg, rgba(244,114,182,0.95), rgba(236,72,153,0.95));
    padding: 1rem 1.25rem;
    border-radius: 14px;
    color: white;
    margin-bottom: 1.25rem;
    display:flex;
    align-items:center;
    gap:1rem;
  }

  .main-header h1{ font-size: 1.75rem; margin:0; letter-spacing:0.6px }
  .main-header p{ margin:0; opacity:0.95 }

  /* Cards */
  .stat-card{ background: rgba(255,255,255,0.95); border-radius: 12px; padding:1rem }
  .trip-card{ background: rgba(255,255,255,0.98); border-radius: 12px; padding:1rem; margin-bottom:0.75rem }

  /* Category badges */
  .category-badge{ border-radius: 999px; padding:0.25rem 0.6rem; font-weight:700; background: rgba(255,255,255,0.6) }

  /* Make buttons a little rounder and pink */
  button[title]{ border-radius:8px }

</style>
""", unsafe_allow_html=True)

# Google Sheets Setup
SCOPES = [
    'https://www.googleapis.com/auth/spreadsheets',
    'https://www.googleapis.com/auth/drive'
]


def _sanitize_value(value):
    """Convert common pandas/numpy types to native JSON-serializable Python types."""
    if value is None:
        return ""
    try:
        # pandas NA handling
        if pd.isna(value):
            return ""
    except Exception:
        pass

    # datetime/date formatting
    try:
        if hasattr(value, 'strftime'):
            return value.strftime("%Y-%m-%d %H:%M:%S")
    except Exception:
        pass

    # Try integer, then float, else fallback to string
    try:
        return int(value)
    except Exception:
        try:
            return float(value)
        except Exception:
            return str(value)


def connect_to_gsheet():
    """Connect to Google Sheets using service account credentials"""
    try:
        # Load credentials from Streamlit secrets
        creds_dict = st.secrets["gcp_service_account"]
        # Allow secrets to be provided either as a parsed TOML table (dict)
        # or as a JSON string (common when pasting the whole JSON into
        # `.streamlit/secrets.toml`). If it's a string, parse it.
        # Custom CSS (no local pictures used)
        st.markdown("""
        <style>
            .block-container {
                background: rgba(255,255,255,0.9) !important;
                padding-top: 1rem;
                border-radius: 0.5rem;
            }

            .main-header {
                background: linear-gradient(135deg, rgba(236,72,153,0.85) 0%, rgba(139,92,246,0.85) 100%);
                padding: 2rem;
                border-radius: 1rem;
                color: white;
                margin-bottom: 2rem;
                display: flex;
                align-items: center;
                gap: 1rem;
            }

            .stat-card {
                background: rgba(255,255,255,0.9);
                padding: 1.5rem;
                border-radius: 1rem;
                box-shadow: 0 2px 8px rgba(0,0,0,0.1);
                text-align: center;
            }

            .trip-card {
                background: rgba(255,255,255,0.95);
                padding: 1.5rem;
                border-radius: 1rem;
                margin-bottom: 1rem;
                border-left: 4px solid #ec4899;
                box-shadow: 0 2px 8px rgba(0,0,0,0.06);
            }

            .category-badge {
                display: inline-block;
                padding: 0.25rem 0.75rem;
                border-radius: 1rem;
                font-size: 0.875rem;
                font-weight: 600;
                margin-right: 0.5rem;
            }
        </style>
        """, unsafe_allow_html=True)

def delete_trip(worksheet, row_num):
    """Delete trip from Google Sheets"""
    try:
        worksheet.delete_rows(row_num + 2)  # +2 for header and 1-indexing
        return True
    except Exception as e:
        st.error(f"Error deleting trip: {e}")
        return False

# Categories with colors and emojis
CATEGORIES = {
    'Dining': {'color': '#f97316', 'emoji': '🍽️'},
    'Activity': {'color': '#3b82f6', 'emoji': '📸'},
    'Café': {'color': '#d97706', 'emoji': '☕'},
    'Travel': {'color': '#8b5cf6', 'emoji': '✈️'},
    'Stay': {'color': '#10b981', 'emoji': '🏠'},
    'Special': {'color': '#ec4899', 'emoji': '💕'},
    'Shopping': {'color': '#f59e0b', 'emoji': '🛍️'}
}

# Trip dates
TRIP_START = date(2025, 12, 17)
TRIP_END = date(2026, 1, 1)

def get_days_between():
    """Get list of all days in the trip"""
    days = []
    current = TRIP_START
    while current <= TRIP_END:
        days.append(current)
        current += timedelta(days=1)
    return days

def main():
    # Header
    # Animated GIF shown in header (external URL)
    gif_url = "https://media.giphy.com/media/l0MYt5jPR6QX5pnqM/giphy.gif"
    st.markdown(f"""
    <div class="main-header">
        <img src="{gif_url}" alt="cute couple" style="width:120px;height:120px;border-radius:12px;object-fit:cover;"/>
        <div>
            <h1>💕 Our Adventure Together</h1>
            <p style="font-size: 1.2rem; margin-top: 0.5rem;">Dec 17, 2025 - Jan 1, 2026 • 16 magical days</p>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    # Connect to Google Sheets
    client = connect_to_gsheet()
    
    if not client:
        st.warning("⚠️ Google Sheets connection not configured. Please add your service account credentials to Streamlit secrets.")
        st.info("""
        **Setup Instructions:**
        1. Create a Google Cloud Project
        2. Enable Google Sheets API and Google Drive API
        3. Create a Service Account and download the JSON key
        4. Add the JSON content to Streamlit secrets as 'gcp_service_account'
        5. Share your Google Sheet with the service account email
        """)
        return
    
    worksheet = get_or_create_sheet(client)
    if not worksheet:
        st.error("Could not obtain a Google Sheet. See the instructions above to resolve Drive quota or share an existing sheet with the service account.")
        return

    # Load data
    df = load_data(worksheet)
    
    # Stats (compact)
    col1, col2, col3 = st.columns(3)

    with col1:
        st.markdown(f"""
        <div class="stat-card">
            <h2 style="color: #ec4899; margin: 0;">📅 {len(df)}</h2>
            <p style="margin: 0.5rem 0 0 0; color: #6b7280;">Total Plans</p>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        days = (TRIP_END - TRIP_START).days + 1
        st.markdown(f"""
        <div class="stat-card">
            <h2 style="color: #ec4899; margin: 0;">❤️ {days}</h2>
            <p style="margin: 0.5rem 0 0 0; color: #6b7280;">Days Together</p>
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        days_planned = len(df['Date'].unique()) if len(df) > 0 else 0
        st.markdown(f"""
        <div class="stat-card">
            <h2 style="color: #10b981; margin: 0;">✅ {days_planned}/{days}</h2>
            <p style="margin: 0.5rem 0 0 0; color: #6b7280;">Days Planned</p>
        </div>
        """, unsafe_allow_html=True)
    
    st.markdown("<br>", unsafe_allow_html=True)
    
    # Main tabs
    tab1, tab2, tab3 = st.tabs(["📅 Timeline View", "📋 List View", "➕ Add/Manage Plans"])
    
    with tab1:
        # Timeline view - simple top-to-bottom list (linear)
        st.subheader("Timeline — Linear View")

        # Category filter
        filter_col1, _ = st.columns([3, 1])
        with filter_col1:
            selected_categories = st.multiselect(
                "Filter by category",
                options=list(CATEGORIES.keys()),
                default=list(CATEGORIES.keys())
            )

        days = get_days_between()

        for day in days:
            day_trips = df[df['Date'] == day]
            if len(selected_categories) > 0:
                day_trips = day_trips[day_trips['Category'].isin(selected_categories)]

            # Day header
            st.markdown(f"<div style='margin: 0.5rem 0; padding: 0.5rem 0;'>"
                        f"<strong>{day.strftime('%A, %B %d, %Y')}</strong> — Day {(day - TRIP_START).days + 1}"
                        f"</div>", unsafe_allow_html=True)

            if len(day_trips) == 0:
                st.info("No plans for this day yet")
            else:
                day_trips = day_trips.sort_values('Time')
                for idx, trip in day_trips.iterrows():
                    cat = CATEGORIES.get(trip['Category'], CATEGORIES['Dining'])
                    note_html = ''
                    if trip.get('Notes'):
                        note_html = f"<p style='margin: 0.5rem 0 0 0; color: #4b5563; font-style: italic;'>{trip['Notes']}</p>"
                    location_html = f" | 📍 {trip['Location']}" if trip.get('Location') else ''

                    col_main, col_action = st.columns([10, 1])
                    with col_main:
                        html = (
                            f"<div class=\"trip-card\" style=\"border-left-color: {cat['color']};\">"
                            f"<h3 style=\"margin: 0 0 0.25rem 0; color: #1f2937;\">{cat['emoji']} {trip['Title']}</h3>"
                            f"<p style=\"margin: 0; color: #6b7280;\">🕐 {trip['Time']}{location_html}</p>"
                            f"{note_html}"
                            f"</div>"
                        )
                        st.markdown(html, unsafe_allow_html=True)

                    with col_action:
                        if st.button("🗑️", key=f"tl_del_{idx}"):
                            if delete_trip(worksheet, idx):
                                st.success("Deleted!")
                                st.rerun()
    
    with tab2:
        # List view - show all plans in table
        st.subheader("All Plans")
        
        if len(df) == 0:
            st.info("No plans added yet. Go to 'Add/Manage Plans' tab to create your first plan!")
        else:
            # Filter
            filter_category = st.selectbox(
                "Filter by category",
                options=['All'] + list(CATEGORIES.keys())
            )
            
            display_df = df if filter_category == 'All' else df[df['Category'] == filter_category]
            display_df = display_df.sort_values(['Date', 'Time'])
            
            # Display
            for idx, trip in display_df.iterrows():
                cat = CATEGORIES.get(trip['Category'], CATEGORIES['Dining'])
                col1, col2 = st.columns([5, 1])
                
                with col1:
                    location_html = f" | 📍 {trip['Location']}" if trip.get('Location') else ''
                    note_html = f"<p style='margin: 0.5rem 0 0 0; color: #4b5563; font-style: italic;'>{trip['Notes']}</p>" if trip.get('Notes') else ''
                    html = (
                        f"<div class=\"trip-card\" style=\"border-left-color: {cat['color']};\">"
                        f"<h3 style=\"margin: 0 0 0.5rem 0; color: #1f2937;\">{cat['emoji']} {trip['Title']}</h3>"
                        f"<p style=\"margin: 0.25rem 0; color: #6b7280;\">📅 {trip['Date'].strftime('%b %d, %Y')} | 🕐 {trip['Time']}{location_html}</p>"
                        f"{note_html}"
                        f"</div>"
                    )
                    st.markdown(html, unsafe_allow_html=True)
                
                with col2:
                    if st.button("🗑️ Delete", key=f"del_{idx}"):
                        if delete_trip(worksheet, idx):
                            st.success("Deleted!")
                            st.rerun()
    
    with tab3:
        st.subheader("Add New Plan")
        
        with st.form("add_trip_form"):
            col1, col2 = st.columns(2)
            
            with col1:
                title = st.text_input("Title *", placeholder="Dinner at Italian restaurant")
                trip_date = st.date_input(
                    "Date *",
                    min_value=TRIP_START,
                    max_value=TRIP_END,
                    value=TRIP_START
                )
                time = st.time_input("Time", value=datetime.strptime("19:00", "%H:%M").time())
                location = st.text_input("Location", placeholder="Restaurant name or address")
            
            with col2:
                category = st.selectbox("Category *", options=list(CATEGORIES.keys()))
                notes = st.text_area("Notes", placeholder="Special details or reminders...")
            
            submitted = st.form_submit_button("✨ Add Plan", use_container_width=True)
            
            if submitted:
                if title and trip_date:
                    trip_id = str(int(datetime.now().timestamp()))
                    trip_data = [
                        trip_id,
                        title,
                        trip_date.strftime("%Y-%m-%d"),
                        time.strftime("%H:%M"),
                        location,
                        category,
                        notes,
                        datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    ]
                    
                    if add_trip(worksheet, trip_data):
                        st.success("🎉 Plan added successfully!")
                        st.rerun()
                else:
                    st.error("Please fill in Title and Date")
        
        st.markdown("---")
        st.subheader("Manage Existing Plans")
        
        if len(df) > 0:
            # Select plan to edit
            plan_options = [f"{row['Title']} - {row['Date'].strftime('%b %d')}" for idx, row in df.iterrows()]
            selected_plan = st.selectbox("Select a plan to edit", options=range(len(plan_options)), format_func=lambda x: plan_options[x])
            
            if selected_plan is not None:
                trip = df.iloc[selected_plan]
                
                with st.form("edit_trip_form"):
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        edit_title = st.text_input("Title *", value=trip['Title'])
                        edit_date = st.date_input(
                            "Date *",
                            value=trip['Date'],
                            min_value=TRIP_START,
                            max_value=TRIP_END
                        )
                        edit_time = st.time_input("Time", value=datetime.strptime(trip['Time'], "%H:%M").time())
                        edit_location = st.text_input("Location", value=trip['Location'])
                    
                    with col2:
                        edit_category = st.selectbox("Category *", options=list(CATEGORIES.keys()), index=list(CATEGORIES.keys()).index(trip['Category']))
                        edit_notes = st.text_area("Notes", value=trip['Notes'])
                    
                    update_submitted = st.form_submit_button("💾 Update Plan", use_container_width=True)
                    
                    if update_submitted:
                        updated_data = [
                            trip['ID'],
                            edit_title,
                            edit_date.strftime("%Y-%m-%d"),
                            edit_time.strftime("%H:%M"),
                            edit_location,
                            edit_category,
                            edit_notes,
                            trip['Created']
                        ]
                        
                        if update_trip(worksheet, selected_plan, updated_data):
                            st.success("✅ Plan updated successfully!")
                            st.rerun()
        else:
            st.info("No plans to edit yet.")

if __name__ == "__main__":
    main()