# app.py
import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import random
from sklearn.linear_model import LinearRegression
from io import BytesIO
from reportlab.pdfgen import canvas

# ---------------------------
# Page Config
# ---------------------------
st.set_page_config(
    page_title="🦴 OrthoPulse Pro 2.0",
    page_icon="🩺",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("<h1 style='text-align:center; color:#4B0082;'>🦴 OrthoPulse Pro 2.0 Dashboard</h1>", unsafe_allow_html=True)

# ---------------------------
# Theme
# ---------------------------
if 'theme' not in st.session_state:
    st.session_state.theme = 'light'

theme_choice = st.sidebar.radio("Choose Theme", ['Light', 'Dark'])
st.session_state.theme = theme_choice

# ---------------------------
# Hospital -> Region mapping
# ---------------------------
hospital_region_map = {
    "Nairobi General": "Nairobi/Kijabe",
    "Kijabe Hospital": "Nairobi/Kijabe",
    "Meru County": "Meru",
    "Mombasa Central": "Mombasa",
    "Eldoret General": "Eldoret"
}

# ---------------------------
# Default Staff Names
# ---------------------------
default_staff = ["Josephine", "Carol","Jacob","Naomi","Charity","Kevin","Miriam","Brian","James","Faith","Geoffrey","Spencer","Evans","Eric"]

# ---------------------------
# Generate Random Procedures
# ---------------------------
def generate_random_procedures(num_records=200):
    hospitals = list(hospital_region_map.keys())
    procedures = ["THA", "TKA", "Hip Revision", "Knee Revision", "Trauma Fixation"]
    surgeons = ["Dr. Mwangi", "Dr. Kimani", "Dr. Ochieng", "Dr. Wanjiru", "Dr. Njoroge"]
    implants = ["Implant A", "Implant B", "Implant C", "Implant D"]

    data = []
    start_date = datetime(datetime.today().year, 1, 1)
    for _ in range(num_records):
        date = start_date + timedelta(days=random.randint(0, (datetime.today() - start_date).days))
        hospital = random.choice(hospitals)
        region = hospital_region_map[hospital]
        procedure = random.choice(procedures)
        surgeon = random.choice(surgeons)
        implant = ", ".join(random.sample(implants, k=random.randint(1, 2)))
        staff_count = random.randint(1, 3)
        staff = ", ".join(random.sample(default_staff, k=staff_count))
        notes = "Routine procedure"
        data.append([date, region, hospital, procedure, surgeon, implant, staff, notes])

    df = pd.DataFrame(data, columns=["Date","Region","Hospital","Procedure","Surgeon","Implants","Staff","Notes"])
    df["Date"] = pd.to_datetime(df["Date"])
    df["Staff"] = df["Staff"].fillna("")
    return df

# ---------------------------
# Load Procedures
# ---------------------------
if "procedures" not in st.session_state:
    st.session_state["procedures"] = generate_random_procedures()

df_all = st.session_state["procedures"]

# ---------------------------
# Role Selection
# ---------------------------
role = st.sidebar.selectbox("Select Role", ["Admin", "Staff"])
staff_name = ""
staff_region = ""
if role == "Staff":
    staff_name = st.sidebar.text_input("Enter Your Name (as in Staff list)")

# ---------------------------
# Filtering by Role
# ---------------------------
df = df_all.copy()
if role == "Staff" and staff_name:
    df = df[df['Staff'].str.contains(staff_name, case=False, na=False)]
    if not df.empty:
        staff_region = df['Region'].iloc[0]

if role == "Admin":
    regions = ["All"] + sorted(df_all["Region"].unique().tolist())
    selected_region = st.sidebar.selectbox("Filter by Region", regions)
    if selected_region != "All":
        df = df[df["Region"] == selected_region]
elif role == "Staff" and staff_region:
    df = df[df["Region"] == staff_region]

# ---------------------------
# Advanced Sidebar Filters
# ---------------------------
st.sidebar.markdown("### Filters")
min_date = df['Date'].min()
max_date = df['Date'].max()
date_range = st.sidebar.date_input("Date Range", [min_date, max_date])
proc_types = st.sidebar.multiselect("Procedure Types", df['Procedure'].unique(), default=df['Procedure'].unique())
hosp_filter = st.sidebar.multiselect("Hospitals", df['Hospital'].unique(), default=df['Hospital'].unique())
surgeon_filter = st.sidebar.multiselect("Surgeons", df['Surgeon'].unique(), default=df['Surgeon'].unique())
staff_filter = st.sidebar.multiselect("Staff", list(set(",".join(df['Staff']).split(", "))), default=list(set(",".join(df['Staff']).split(", "))))

df_filtered = df[
    (df['Date'] >= pd.to_datetime(date_range[0])) &
    (df['Date'] <= pd.to_datetime(date_range[1])) &
    (df['Procedure'].isin(proc_types)) &
    (df['Hospital'].isin(hosp_filter)) &
    (df['Surgeon'].isin(surgeon_filter)) &
    (df['Staff'].apply(lambda x: any(s in x for s in staff_filter)))
]

# ---------------------------
# Tabs
# ---------------------------
tabs = st.tabs(["📊 Metrics","📈 Trends","🏆 Leaderboards","📝 Reports","➕ Add Procedure"])

# ---------------------------
# Metrics Tab
# ---------------------------
with tabs[0]:
    st.markdown("### Key Metrics")
    total_cases = len(df_filtered)
    total_surgeons = df_filtered["Surgeon"].nunique()
    total_staff = df_filtered["Staff"].str.split(",").explode().str.strip().nunique()
    top_hospital = df_filtered['Hospital'].value_counts().idxmax() if not df_filtered.empty else "N/A"
    top_procedure = df_filtered['Procedure'].value_counts().idxmax() if not df_filtered.empty else "N/A"

    cols = st.columns(5)
    cols[0].metric("Total Cases", total_cases)
    cols[1].metric("Total Surgeons", total_surgeons)
    cols[2].metric("Total Staff", total_staff)
    cols[3].metric("Top Hospital", top_hospital)
    cols[4].metric("Top Procedure", top_procedure)

# ---------------------------
# Trends Tab
# ---------------------------
with tabs[1]:
    st.markdown("### Monthly Trend (Linear Regression Prediction)")
    if not df_filtered.empty:
        df_month = df_filtered.groupby(pd.Grouper(key="Date", freq="M")).size().reset_index(name="Procedures")
        df_month = df_month.sort_values("Date")
        X = np.arange(len(df_month)).reshape(-1,1)
        y = df_month["Procedures"].values
        model = LinearRegression().fit(X, y)
        y_pred = model.predict(X)

        fig = go.Figure()
        fig.add_trace(go.Scatter(x=df_month["Date"], y=y, mode='lines+markers', name="Actual Procedures"))
        fig.add_trace(go.Scatter(x=df_month["Date"], y=y_pred, mode='lines', name="Trend Prediction"))
        fig.update_layout(height=500, xaxis_title="Month", yaxis_title="Procedures")
        st.plotly_chart(fig, use_container_width=True)

# ---------------------------
# Leaderboards Tab
# ---------------------------
with tabs[2]:
    st.markdown("### Leaderboards")
    lb_surgeons = df_filtered['Surgeon'].value_counts().reset_index()
    lb_surgeons.columns = ['Surgeon', 'Procedures Done']
    fig_surgeon = px.bar(lb_surgeons, x='Surgeon', y='Procedures Done', text='Procedures Done', color='Procedures Done', color_continuous_scale=px.colors.sequential.Viridis)
    st.plotly_chart(fig_surgeon, use_container_width=True)

    staff_series = df_filtered['Staff'].str.split(",").explode().str.strip().dropna()
    lb_staff = staff_series.value_counts().reset_index()
    lb_staff.columns = ["Staff", "Appearances"]
    fig_staff = px.bar(lb_staff, x="Staff", y="Appearances", text="Appearances", color="Appearances", color_continuous_scale=px.colors.sequential.Plasma)
    st.plotly_chart(fig_staff, use_container_width=True)

# ---------------------------
# Reports Tab
# ---------------------------
with tabs[3]:
    st.markdown("### Generate Reports")
    csv = df_filtered.to_csv(index=False).encode()
    st.download_button("Download CSV", csv, "report.csv", "text/csv")

    buffer = BytesIO()
    pdf = canvas.Canvas(buffer)
    pdf.drawString(50, 800, "OrthoPulse Pro 2.0 Report")
    y = 770
    for _, row in df_filtered.iterrows():
        pdf.drawString(50, y, f"{row['Date'].date()} - {row['Hospital']} - {row['Procedure']} - {row['Surgeon']}")
        y -= 15
        if y < 50:
            pdf.showPage()
            y = 800
    pdf.save()
    buffer.seek(0)
    st.download_button("Download PDF", buffer, "report.pdf", "application/pdf")

# ---------------------------
# Add Procedure Tab
# ---------------------------
with tabs[4]:
    st.markdown("### Add Procedure")
    with st.form("add_proc"):
        date_input = st.date_input("Date", datetime.today())
        region_input = st.text_input("Region")
        hospital_input = st.text_input("Hospital")
        procedure_input = st.text_input("Procedure")
        surgeon_input = st.text_input("Surgeon")
        staff_input = st.text_input("Staff (comma separated)")
        notes_input = st.text_area("Notes")
        submitted = st.form_submit_button("Add Procedure")
        if submitted:
            new_row = pd.DataFrame([[date_input, region_input, hospital_input, procedure_input, surgeon_input, "", staff_input, notes_input]], columns=df_all.columns)
            st.session_state.procedures = pd.concat([st.session_state.procedures, new_row], ignore_index=True)
            st.success("✅ Procedure added successfully!")
