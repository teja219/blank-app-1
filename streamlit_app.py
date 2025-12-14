import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
import pandas as pd
from datetime import datetime, date, timedelta
import json
import base64
from pathlib import Path

# Page configuration
st.set_page_config(
    page_title="Our Adventure Together",
    page_icon="💕",
    layout="wide"
)

# Custom CSS
def _img_to_datauri(path: Path):
    try:
        with open(path, "rb") as f:
            data = base64.b64encode(f.read()).decode()
        ext = path.suffix.lstrip('.').lower()
        return f"data:image/{ext};base64,{data}"
    except Exception:
        return None

# prepare background images (use local files picture1.jpg and picture2.jpg if present)
bg1 = _img_to_datauri(Path("picture1.jpg")) or ''
bg2 = _img_to_datauri(Path("picture2.jpg")) or ''

# Always show the full image as the page background and make content
# containers transparent so the image is visible.
content_bg = 'transparent'

st.markdown(f"""
<style>
    /* Apply the page background to Streamlit's app container */
    section[data-testid="stAppViewContainer"] {{
        {'background-image: url("' + bg1 + '");' if bg1 else ''}
        background-size: contain;
        background-attachment: fixed;
        background-position: center;
        background-repeat: no-repeat;
    }}

    /* Make main content area translucent so background is visible */
    .block-container {{
        background: {content_bg} !important;
        padding-top: 1rem;
        border-radius: 0.5rem;
    }}

    .main-header {{
        background: linear-gradient(135deg, rgba(236,72,153,0.65) 0%, rgba(139,92,246,0.65) 100%) {' , ' if bg2 else ''} url('{bg2}');
        background-size: cover;
        padding: 2rem;
        border-radius: 1rem;
        color: white;
        margin-bottom: 2rem;
    }}

    .stat-card {{
        background: rgba(255,255,255,0.9);
        padding: 1.5rem;
        border-radius: 1rem;
        box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        text-align: center;
    }}

    .trip-card {{
        background: rgba(255,255,255,0.95);
        padding: 1.5rem;
        border-radius: 1rem;
        margin-bottom: 1rem;
        border-left: 4px solid #ec4899;
        box-shadow: 0 2px 8px rgba(0,0,0,0.06);
    }}

    .category-badge {{
        display: inline-block;
        padding: 0.25rem 0.75rem;
        border-radius: 1rem;
        font-size: 0.875rem;
        font-weight: 600;
        margin-right: 0.5rem;
    }}
</style>
""", unsafe_allow_html=True)

# Insert a fixed full-screen <img> behind the app for pixel-perfect background
if bg1:
    st.markdown(
        f"""
        <style>
            #page-bg-img {{
                position: fixed;
                inset: 0;
                z-index: -9999;
                width: 100%;
                height: 100%;
                object-fit: contain;
                pointer-events: none;
                opacity: 1;
            }}
            /* ensure the app content sits above the image */
            section[data-testid="stAppViewContainer"] {{
                position: relative;
                z-index: 0;
            }}
        </style>
        <img id="page-bg-img" src="{bg1}" alt="background" />
        """,
        unsafe_allow_html=True,
    )

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
        if isinstance(creds_dict, str):
            try:
                creds_dict = json.loads(creds_dict)
            except Exception as ex:
                # Provide a helpful error to the user in Streamlit UI
                st.error("Could not parse gcp_service_account JSON from Streamlit secrets: %s" % ex)
                return None
        creds = Credentials.from_service_account_info(creds_dict, scopes=SCOPES)
        client = gspread.authorize(creds)
        return client
    except Exception as e:
        st.error(f"Error connecting to Google Sheets: {e}")
        st.info("Please set up your Google Cloud service account credentials in Streamlit secrets.")
        return None

def get_or_create_sheet(client, spreadsheet_name="Travel Planner Dec 2025"):
    """Get existing spreadsheet or create new one"""
    try:
        spreadsheet = client.open(spreadsheet_name)
    except gspread.SpreadsheetNotFound:
        try:
            spreadsheet = client.create(spreadsheet_name)
            # Share with your email (optional)
            # spreadsheet.share('your-email@gmail.com', perm_type='user', role='writer')
        except gspread.exceptions.APIError as e:
            # Common cause: Drive storage quota exceeded for the account that
            # would own the newly-created spreadsheet (often the service account).
            st.error(f"Google Drive API error creating spreadsheet: {e}")
            st.info(
                "Common fixes:\n"
                "- Free up Drive storage or purchase more storage for the account.\n"
                "- Create the spreadsheet manually in a Google account that has available storage, then share it with the service account's email and set it in the app by name or ID.\n"
                "- Use a different service account that has sufficient Drive quota."
            )
            return None
    
    try:
        worksheet = spreadsheet.worksheet("Plans")
    except gspread.WorksheetNotFound:
        worksheet = spreadsheet.add_worksheet(title="Plans", rows=1000, cols=10)
        # Add headers
        headers = ['ID', 'Title', 'Date', 'Time', 'Location', 'Category', 'Budget', 'Notes', 'Priority', 'Created']
        worksheet.append_row(headers)
    
    return worksheet

def load_data(worksheet):
    """Load all data from Google Sheets"""
    try:
        data = worksheet.get_all_records()
        if data:
            df = pd.DataFrame(data)
            df['Date'] = pd.to_datetime(df['Date']).dt.date
            return df
        return pd.DataFrame(columns=['ID', 'Title', 'Date', 'Time', 'Location', 'Category', 'Budget', 'Notes', 'Priority', 'Created'])
    except Exception as e:
        st.error(f"Error loading data: {e}")
        return pd.DataFrame(columns=['ID', 'Title', 'Date', 'Time', 'Location', 'Category', 'Budget', 'Notes', 'Priority', 'Created'])

def add_trip(worksheet, trip_data):
    """Add new trip to Google Sheets"""
    try:
        # sanitize values to native Python types (avoid numpy/pandas types)
        safe_row = [_sanitize_value(v) for v in trip_data]
        worksheet.append_row(safe_row)
        return True
    except Exception as e:
        st.error(f"Error adding trip: {e}")
        return False

def update_trip(worksheet, row_num, trip_data):
    """Update existing trip in Google Sheets"""
    try:
        # row_num is 1-indexed, +1 for header
        for i, value in enumerate(trip_data):
            v = _sanitize_value(value)
            worksheet.update_cell(row_num + 2, i + 1, v)
        return True
    except Exception as e:
        st.error(f"Error updating trip: {e}")
        return False

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
    st.markdown("""
    <div class="main-header">
        <h1>💕 Our Adventure Together</h1>
        <p style="font-size: 1.2rem; margin-top: 0.5rem;">Dec 17, 2025 - Jan 1, 2026 • 16 magical days</p>
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
    
    # Stats
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.markdown(f"""
        <div class="stat-card">
            <h2 style="color: #ec4899; margin: 0;">📅 {len(df)}</h2>
            <p style="margin: 0.5rem 0 0 0; color: #6b7280;">Total Plans</p>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        total_budget = df['Budget'].astype(float).sum() if len(df) > 0 else 0
        st.markdown(f"""
        <div class="stat-card">
            <h2 style="color: #8b5cf6; margin: 0;">💰 ${total_budget:.2f}</h2>
            <p style="margin: 0.5rem 0 0 0; color: #6b7280;">Total Budget</p>
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        days = (TRIP_END - TRIP_START).days + 1
        st.markdown(f"""
        <div class="stat-card">
            <h2 style="color: #ec4899; margin: 0;">❤️ {days}</h2>
            <p style="margin: 0.5rem 0 0 0; color: #6b7280;">Days Together</p>
        </div>
        """, unsafe_allow_html=True)
    
    with col4:
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
                    budget_html = f" | 💵 ${trip['Budget']}" if trip.get('Budget') else ''

                    col_main, col_action = st.columns([10, 1])
                    with col_main:
                        html = (
                            f"<div class=\"trip-card\" style=\"border-left-color: {cat['color']};\">"
                            f"<h3 style=\"margin: 0 0 0.25rem 0; color: #1f2937;\">{cat['emoji']} {trip['Title']}</h3>"
                            f"<p style=\"margin: 0; color: #6b7280;\">🕐 {trip['Time']}{location_html}{budget_html}</p>"
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
                    budget_html = f" | 💵 ${trip['Budget']}" if trip.get('Budget') else ''
                    note_html = f"<p style='margin: 0.5rem 0 0 0; color: #4b5563; font-style: italic;'>{trip['Notes']}</p>" if trip.get('Notes') else ''
                    html = (
                        f"<div class=\"trip-card\" style=\"border-left-color: {cat['color']};\">"
                        f"<h3 style=\"margin: 0 0 0.5rem 0; color: #1f2937;\">{cat['emoji']} {trip['Title']}</h3>"
                        f"<p style=\"margin: 0.25rem 0; color: #6b7280;\">📅 {trip['Date'].strftime('%b %d, %Y')} | 🕐 {trip['Time']}{location_html}{budget_html}</p>"
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
                budget = st.number_input("Budget ($)", min_value=0.0, step=10.0, format="%.2f")
                priority = st.selectbox("Priority", options=["Low", "Medium", "High"], index=1)
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
                        budget,
                        notes,
                        priority,
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
                        edit_budget = st.number_input("Budget ($)", value=float(trip['Budget']), min_value=0.0, step=10.0, format="%.2f")
                        edit_priority = st.selectbox("Priority", options=["Low", "Medium", "High"], index=["Low", "Medium", "High"].index(trip['Priority']))
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
                            edit_budget,
                            edit_notes,
                            edit_priority,
                            trip['Created']
                        ]
                        
                        if update_trip(worksheet, selected_plan, updated_data):
                            st.success("✅ Plan updated successfully!")
                            st.rerun()
        else:
            st.info("No plans to edit yet.")

if __name__ == "__main__":
    main()