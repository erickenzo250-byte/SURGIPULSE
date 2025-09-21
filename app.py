import streamlit as st
import pandas as pd
import numpy as np
import altair as alt
from datetime import datetime, timedelta
import random
from sqlmodel import SQLModel, Field, Session, create_engine, select, Relationship
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
import io
from sklearn.linear_model import LinearRegression
import time

# -------------------------------
# DATABASE MODELS
# -------------------------------
class Staff(SQLModel, table=True):
    id: int = Field(default=None, primary_key=True)
    name: str
    region: str
    hospital: str
    role: str = "Surgeon"
    created_at: datetime = Field(default_factory=datetime.utcnow)
    surgeries: "list[Surgery] | None" = Relationship(back_populates="staff")
    targets: "list[Target] | None" = Relationship(back_populates="staff")

class Surgery(SQLModel, table=True):
    id: int = Field(default=None, primary_key=True)
    staff_id: int = Field(foreign_key="staff.id")
    date: datetime = Field(default_factory=datetime.utcnow)
    region: str
    hospital: str
    staff: "Staff | None" = Relationship(back_populates="surgeries")

class Target(SQLModel, table=True):
    id: int = Field(default=None, primary_key=True)
    staff_id: int = Field(foreign_key="staff.id")
    month: str
    target_surgeries: int
    assigned_at: datetime = Field(default_factory=datetime.utcnow)
    staff: "Staff | None" = Relationship(back_populates="targets")

# -------------------------------
# DATABASE SETUP
# -------------------------------
engine = create_engine("sqlite:///surgipulse.db")
SQLModel.metadata.create_all(engine)

def get_session():
    return Session(engine)

# -------------------------------
# DEFAULT DATA
# -------------------------------
DEFAULT_STAFF = [
    "Josephine","Carol","Jacob","Naomi","Charity","Kevin","Miriam",
    "Brian","James","Faith","Geoffrey","Spencer","Evans","Eric"
]
DEFAULT_REGIONS = ["Eldoret","Nairobi/Kijabe","Meru","Mombasa"]
HOSPITAL_MAP = {
    "Eldoret": ["Moi Teaching & Referral","Eldoret County Hospital"],
    "Nairobi/Kijabe": ["Kenyatta National Hospital","Kijabe Mission Hospital"],
    "Meru": ["Meru Teaching & Referral","Meru County Hospital"],
    "Mombasa": ["Coast General","Mombasa Hospital"]
}

def seed_staff():
    with get_session() as session:
        existing = session.exec(select(Staff)).all()
        if not existing:
            staff_objs = []
            for name in DEFAULT_STAFF:
                region = random.choice(DEFAULT_REGIONS)
                hospital = random.choice(HOSPITAL_MAP[region])
                staff_objs.append(Staff(name=name, region=region, hospital=hospital))
            session.add_all(staff_objs)
            session.commit()
seed_staff()

# -------------------------------
# RANDOM SURGERY GENERATION
# -------------------------------
def generate_random_surgeries(n=200):
    with get_session() as session:
        staff_list = session.exec(select(Staff)).all()
        surgeries = []
        for _ in range(n):
            staff = random.choice(staff_list)
            date = datetime.today() - timedelta(days=random.randint(0, 300))
            hospital = staff.hospital
            region = staff.region
            surgeries.append(Surgery(staff_id=staff.id, date=date, hospital=hospital, region=region))
        session.add_all(surgeries)
        session.commit()
generate_random_surgeries()

# -------------------------------
# EXPORT FUNCTIONS
# -------------------------------
def export_excel(df: pd.DataFrame):
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="Report")
    return output.getvalue()

def export_pdf(df: pd.DataFrame):
    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4
    text = c.beginText(40, height-40)
    text.setFont("Helvetica", 10)
    lines = df.to_string(index=False).split("\n")
    for line in lines:
        text.textLine(line)
    c.drawText(text)
    c.showPage()
    c.save()
    buffer.seek(0)
    return buffer.getvalue()

# -------------------------------
# STREAMLIT APP
# -------------------------------
st.set_page_config(page_title="SurgiPulse Pro", page_icon="🦴", layout="wide")
st.sidebar.title("SurgiPulse Navigation")
page = st.sidebar.radio("Go to", ["Dashboard","Log Surgery","Assign Targets","Leaderboard","Trends","Reports"])

# -------------------------------
# DASHBOARD
# -------------------------------
if page=="Dashboard":
    st.header("📊 Surgery Dashboard")
    with get_session() as session:
        surgeries = session.exec(select(Surgery)).all()
        staff_list_db = session.exec(select(Staff)).all()
        st.metric("🟢 Total Surgeries", len(surgeries))
        st.metric("🔵 Total Staff", len(staff_list_db))

        if surgeries:
            df = pd.DataFrame([{"Region": s.region, "Hospital": s.hospital, "Date": s.date} for s in surgeries])
            # Region Chart
            region_chart = alt.Chart(df).mark_bar().encode(
                x='Region', y='count()', color='Region', tooltip=['Region','count()']
            ).properties(title="Surgeries by Region")
            st.altair_chart(region_chart,use_container_width=True)
            # Hospital Chart
            hospital_chart = alt.Chart(df).mark_bar().encode(
                x='Hospital', y='count()', color='Hospital', tooltip=['Hospital','count()']
            ).properties(title="Surgeries by Hospital")
            st.altair_chart(hospital_chart,use_container_width=True)

# -------------------------------
# LOG SURGERY
# -------------------------------
elif page=="Log Surgery":
    st.header("📝 Log Surgery")
    with get_session() as session:
        staff_list_db = session.exec(select(Staff)).all()
        staff_dict = {s.name:s for s in staff_list_db}
        staff_name = st.selectbox("Select Staff", list(staff_dict.keys()))
        staff = staff_dict[staff_name]
        hospital = st.selectbox("Hospital", HOSPITAL_MAP[staff.region])
        date = st.date_input("Surgery Date", datetime.today())
        if st.button("Log Surgery"):
            session.add(Surgery(staff_id=staff.id, date=date, hospital=hospital, region=staff.region))
            session.commit()
            st.success(f"Surgery logged for {staff_name} on {date}")

# -------------------------------
# ASSIGN TARGETS
# -------------------------------
elif page=="Assign Targets":
    st.header("🎯 Assign Surgery Targets")
    with get_session() as session:
        staff_list_db = session.exec(select(Staff)).all()
        staff_dict = {s.name:s for s in staff_list_db}
        staff_name = st.selectbox("Select Staff", list(staff_dict.keys()))
        staff = staff_dict[staff_name]
        month = st.selectbox("Month", [
            "January","February","March","April","May","June",
            "July","August","September","October","November","December"
        ])
        target = st.number_input("Target Surgeries", min_value=1, step=1)
        if st.button("Assign Target"):
            session.add(Target(staff_id=staff.id, month=month, target_surgeries=target))
            session.commit()
            st.success(f"Assigned {target} surgeries for {staff_name} in {month}")

# -------------------------------
# LEADERBOARD
# -------------------------------
elif page=="Leaderboard":
    st.header("🏆 Leaderboard with Badges")
    with get_session() as session:
        staff_list_db = session.exec(select(Staff)).all()
        leaderboard = []
        for s in staff_list_db:
            surgeries = session.exec(select(Surgery).where(Surgery.staff_id==s.id)).all()
            targets = session.exec(select(Target).where(Target.staff_id==s.id)).all()
            total_target = sum(t.target_surgeries for t in targets)
            progress = len(surgeries)/total_target if total_target else 0
            leaderboard.append({"Staff":s.name,"Surgeries":len(surgeries),"Target":total_target,"Progress":progress})
        df_lb = pd.DataFrame(leaderboard).sort_values(by="Surgeries",ascending=False)
        badges=["🥇","🥈","🥉"]
        for i,row in df_lb.iterrows():
            badge=badges[i] if i<3 else ""
            st.markdown(f"**{badge} {row['Staff']}** - Surgeries: {row['Surgeries']} | Target: {row['Target']}")
            st.progress(min(row["Progress"],1.0))

# -------------------------------
# TRENDS
# -------------------------------
elif page=="Trends":
    st.header("📈 Surgery Trends & Forecast")
    with get_session() as session:
        surgeries = session.exec(select(Surgery)).all()
        if surgeries:
            df_trend = pd.DataFrame([{"Staff": s.staff.name, "Date": s.date} for s in surgeries])
            df_trend['Month'] = df_trend['Date'].dt.to_period('M').dt.to_timestamp()
            trend = df_trend.groupby('Month').count()['Staff'].reset_index()
            trend.rename(columns={"Staff":"Total Surgeries"}, inplace=True)
            trend['MA3']=trend['Total Surgeries'].rolling(3).mean()
            # Linear regression
            trend['MonthNum']=np.arange(len(trend)).reshape(-1,1)
            model = LinearRegression()
            model.fit(trend['MonthNum'],trend['Total Surgeries'])
            trend['Forecast']=model.predict(trend['MonthNum'])
            # Chart
            base = alt.Chart(trend).encode(x='Month:T')
            line1 = base.mark_line(color='blue').encode(y='Total Surgeries')
            line2 = base.mark_line(color='red',strokeDash=[5,5]).encode(y='Forecast')
            ma_line = base.mark_line(color='green').encode(y='MA3')
            chart = line1+line2+ma_line
            st.altair_chart(chart,use_container_width=True)
            st.dataframe(trend)

# -------------------------------
# REPORTS
# -------------------------------
elif page=="Reports":
    st.header("📑 Reports")
    with get_session() as session:
        surgeries = session.exec(select(Surgery)).all()
        if surgeries:
            df = pd.DataFrame([{"Staff": s.staff.name, "Hospital": s.hospital, "Region": s.region, "Date": s.date} for s in surgeries])
            st.dataframe(df)
            col1,col2=st.columns(2)
            with col1:
                excel = export_excel(df)
                st.download_button("⬇ Export Excel", excel, "report.xlsx")
            with col2:
                pdf = export_pdf(df)
                st.download_button("⬇ Export PDF", pdf, "report.pdf", mime="application/pdf")
