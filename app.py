import streamlit as st
from sqlmodel import SQLModel, Field, Session, create_engine, select, Relationship
from datetime import datetime, timedelta
import pandas as pd
import altair as alt
import io
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
import random
import numpy as np
from sklearn.linear_model import LinearRegression

# -------------------------------
# DATABASE MODELS
# -------------------------------
class Staff(SQLModel, table=True):
    id: int = Field(default=None, primary_key=True)
    name: str
    role: str = "Surgeon"
    hospital: str
    region: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
    surgeries: list["Surgery"] = Relationship(back_populates="staff")
    targets: list["Target"] = Relationship(back_populates="staff")

class Surgery(SQLModel, table=True):
    id: int = Field(default=None, primary_key=True)
    staff_id: int = Field(foreign_key="staff.id")
    hospital: str
    region: str
    date: datetime
    staff: "Staff" = Relationship(back_populates="surgeries")

class Target(SQLModel, table=True):
    id: int = Field(default=None, primary_key=True)
    staff_id: int = Field(foreign_key="staff.id")
    month: str
    target_surgeries: int
    assigned_at: datetime = Field(default_factory=datetime.utcnow)
    staff: "Staff" = Relationship(back_populates="targets")

# -------------------------------
# DATABASE SETUP
# -------------------------------
engine = create_engine("sqlite:///surgipulse.db")
SQLModel.metadata.create_all(engine)

def get_session():
    return Session(engine)

# -------------------------------
# SEED DEFAULT STAFF
# -------------------------------
def seed_default_staff():
    default_staff = [
        {"name":"Josephine","hospital":"Eldoret Hospital","region":"Eldoret"},
        {"name":"Carol","hospital":"Nairobi Hospital","region":"Nairobi/Kijabe"},
        {"name":"Jacob","hospital":"Meru Hospital","region":"Meru"},
        {"name":"Naomi","hospital":"Mombasa General","region":"Mombasa"},
        {"name":"Charity","hospital":"Eldoret Hospital","region":"Eldoret"},
        {"name":"Kevin","hospital":"Nairobi Hospital","region":"Nairobi/Kijabe"},
        {"name":"Miriam","hospital":"Meru Hospital","region":"Meru"},
        {"name":"Brian","hospital":"Mombasa General","region":"Mombasa"},
        {"name":"James","hospital":"Eldoret Hospital","region":"Eldoret"},
        {"name":"Faith","hospital":"Nairobi Hospital","region":"Nairobi/Kijabe"},
        {"name":"Geoffrey","hospital":"Meru Hospital","region":"Meru"},
        {"name":"Spencer","hospital":"Mombasa General","region":"Mombasa"},
        {"name":"Evans","hospital":"Eldoret Hospital","region":"Eldoret"},
        {"name":"Eric","hospital":"Nairobi Hospital","region":"Nairobi/Kijabe"},
    ]
    with get_session() as session:
        existing = session.exec(select(Staff)).all()
        if not existing:
            for s in default_staff:
                session.add(Staff(**s))
            session.commit()

seed_default_staff()

# -------------------------------
# RANDOM SURGERY GENERATION
# -------------------------------
def generate_random_surgeries(n=150):
    with get_session() as session:
        staff_list = session.exec(select(Staff)).all()
        if not staff_list:
            return
        procedures = ["THA","TKA","Hip Revision","Knee Revision","Trauma Fixation"]
        for _ in range(n):
            staff = random.choice(staff_list)
            date = datetime.today() - timedelta(days=random.randint(0, 300))
            surgery = Surgery(
                staff_id=staff.id,
                hospital=staff.hospital,
                region=staff.region,
                date=date
            )
            session.add(surgery)
        session.commit()

# Uncomment below to generate test data once
# generate_random_surgeries(200)

# -------------------------------
# EXPORT HELPERS
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
    text.setFont("Helvetica",10)
    for line in df.to_string(index=False).split("\n"):
        text.textLine(line)
    c.drawText(text)
    c.showPage()
    c.save()
    buffer.seek(0)
    return buffer.getvalue()

# -------------------------------
# STREAMLIT APP
# -------------------------------
st.set_page_config(page_title="SurgiPulse Pro", layout="wide")
st.sidebar.title("SurgiPulse Navigation")
page = st.sidebar.radio("Go to", ["Dashboard","Log Surgery","Assign Targets","Trends","Leaderboard","Reports"])

# -------------------------------
# DASHBOARD
# -------------------------------
if page=="Dashboard":
    st.header("📊 Dashboard")
    with get_session() as session:
        surgeries = session.exec(select(Surgery)).all()
        staff = session.exec(select(Staff)).all()
        st.metric("Total Surgeries", len(surgeries))
        st.metric("Total Staff", len(staff))
        if surgeries:
            df = pd.DataFrame([{"Region": s.region, "Hospital": s.hospital, "Date": s.date} for s in surgeries])
            chart = alt.Chart(df).mark_bar().encode(
                x="Region", y="count()", color="Region"
            )
            st.altair_chart(chart,use_container_width=True)

# -------------------------------
# LOG SURGERY
# -------------------------------
elif page=="Log Surgery":
    st.header("📝 Log Surgery")
    with get_session() as session:
        staff_list = session.exec(select(Staff)).all()
        staff_dict = {s.name:s for s in staff_list}
        staff_name = st.selectbox("Select Staff",list(staff_dict.keys()))
        staff = staff_dict[staff_name]
        date = st.date_input("Surgery Date", datetime.today())
        if st.button("Log Surgery"):
            surgery = Surgery(staff_id=staff.id,hospital=staff.hospital,region=staff.region,date=date)
            session.add(surgery)
            session.commit()
            st.success(f"Surgery logged for {staff_name} on {date}")

# -------------------------------
# ASSIGN TARGETS
# -------------------------------
elif page=="Assign Targets":
    st.header("🎯 Assign Targets")
    with get_session() as session:
        staff_list = session.exec(select(Staff)).all()
        staff_dict = {s.name:s for s in staff_list}
        staff_name = st.selectbox("Select Staff",list(staff_dict.keys()))
        staff = staff_dict[staff_name]
        month = st.selectbox("Month", ["January","February","March","April","May","June","July","August","September","October","November","December"])
        target = st.number_input("Target Surgeries",min_value=1,step=1)
        if st.button("Assign Target"):
            new_target = Target(staff_id=staff.id, month=month, target_surgeries=target)
            session.add(new_target)
            session.commit()
            st.success(f"Assigned {target} surgeries for {staff_name} in {month}")

# -------------------------------
# TRENDS
# -------------------------------
elif page=="Trends":
    st.header("📈 Trends")
    with get_session() as session:
        surgeries = session.exec(select(Surgery)).all()
        if surgeries:
            df = pd.DataFrame([{"Date": s.date.date()} for s in surgeries])
            df['Month'] = df['Date'].apply(lambda x: x.strftime("%Y-%m"))
            trend = df.groupby('Month').size().reset_index(name="Total Surgeries")
            trend['MonthNum'] = np.arange(len(trend)).reshape(-1,1)
            # Linear Regression Forecast
            X = trend['MonthNum'].values.reshape(-1,1)
            y = trend['Total Surgeries'].values
            model = LinearRegression()
            model.fit(X,y)
            trend['Forecast'] = model.predict(X)
            trend['MA3'] = trend['Total Surgeries'].rolling(3).mean()
            base = alt.Chart(trend).encode(x='Month:T')
            line_actual = base.mark_line(color='blue').encode(y='Total Surgeries')
            line_forecast = base.mark_line(color='red',strokeDash=[5,5]).encode(y='Forecast')
            ma_line = base.mark_line(color='green').encode(y='MA3')
            chart = line_actual + line_forecast + ma_line
            st.altair_chart(chart,use_container_width=True)
            st.dataframe(trend)

# -------------------------------
# LEADERBOARD
# -------------------------------
elif page=="Leaderboard":
    st.header("🏆 Leaderboard")
    with get_session() as session:
        staff_list = session.exec(select(Staff)).all()
        leaderboard = []
        for s in staff_list:
            surgeries = session.exec(select(Surgery).where(Surgery.staff_id==s.id)).all()
            targets = session.exec(select(Target).where(Target.staff_id==s.id)).all()
            total_target = sum(t.target_surgeries for t in targets)
            leaderboard.append({
                "Staff": s.name,
                "Surgeries": len(surgeries),
                "Target": total_target,
                "Progress": f"{len(surgeries)}/{total_target}" if total_target else "No target"
            })
        df = pd.DataFrame(leaderboard).sort_values(by="Surgeries",ascending=False)
        st.dataframe(df)

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
            col1,col2 = st.columns(2)
            with col1:
                st.download_button("⬇ Export Excel", export_excel(df), "report.xlsx")
            with col2:
                st.download_button("⬇ Export PDF", export_pdf(df), "report.pdf", mime="application/pdf")
