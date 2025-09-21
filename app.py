import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import altair as alt
from sqlmodel import SQLModel, Field, Session, create_engine, select, Relationship
import io
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4

# ---------------------------
# DATABASE MODELS
# ---------------------------
class Staff(SQLModel, table=True):
    id: int = Field(default=None, primary_key=True)
    name: str
    role: str = "Surgeon"
    hospital: str
    region: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
    surgeries: list["Surgery"] = Relationship(back_populates="staff")

class Surgery(SQLModel, table=True):
    id: int = Field(default=None, primary_key=True)
    staff_id: int = Field(foreign_key="staff.id")
    hospital: str
    region: str
    date: datetime = Field(default_factory=datetime.utcnow)
    staff: "Staff" = Relationship(back_populates="surgeries")

# ---------------------------
# DATABASE SETUP
# ---------------------------
engine = create_engine("sqlite:///data/surgipulse.db")
SQLModel.metadata.create_all(engine)

def get_session():
    return Session(engine)

# ---------------------------
# DEFAULT STAFF & HOSPITALS
# ---------------------------
DEFAULT_STAFF = [
    "Josephine","Carol","Jacob","Naomi","Charity","Kevin",
    "Miriam","Brian","James","Faith","Geoffrey","Spencer","Evans","Eric"
]

HOSPITALS = {
    "Eldoret Hospital":"Eldoret",
    "Nairobi Hospital":"Nairobi/Kijabe",
    "Meru Hospital":"Meru",
    "Mombasa General":"Mombasa"
}

# ---------------------------
# SEED STAFF
# ---------------------------
def seed_staff():
    with get_session() as session:
        existing = session.exec(select(Staff)).all()
        if not existing:
            staff_objs = [Staff(name=name, hospital=np.random.choice(list(HOSPITALS.keys())),
                                region=np.random.choice(list(HOSPITALS.values()))) for name in DEFAULT_STAFF]
            session.add_all(staff_objs)
            session.commit()
seed_staff()

# ---------------------------
# RANDOM SURGERY DATA
# ---------------------------
def generate_random_surgeries(n=200):
    with get_session() as session:
        staff_list = session.exec(select(Staff)).all()
        for _ in range(n):
            staff = np.random.choice(staff_list)
            date = datetime(datetime.now().year,1,1) + timedelta(days=np.random.randint(0,(datetime.now() - datetime(datetime.now().year,1,1)).days))
            surgery = Surgery(staff_id=staff.id, hospital=staff.hospital, region=staff.region, date=date)
            session.add(surgery)
        session.commit()
# Uncomment to generate test data
# generate_random_surgeries(200)

# ---------------------------
# EXPORT HELPERS
# ---------------------------
def export_excel(df):
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="Report")
    return output.getvalue()

def export_pdf(df):
    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4
    text = c.beginText(40, height - 40)
    text.setFont("Helvetica", 10)
    for line in df.to_string(index=False).split("\n"):
        text.textLine(line)
    c.drawText(text)
    c.showPage()
    c.save()
    buffer.seek(0)
    return buffer.getvalue()

# ---------------------------
# STREAMLIT APP
# ---------------------------
st.set_page_config(page_title="SurgiPulse Pro", layout="wide", page_icon="🩺")
st.sidebar.title("SurgiPulse Pro")
page = st.sidebar.radio("Navigate", ["Dashboard","Log Surgery","Reports","Leaderboard","Trends"])

# ---------------------------
# DASHBOARD
# ---------------------------
if page == "Dashboard":
    st.title("📊 SurgiPulse Pro Dashboard")
    with get_session() as session:
        surgeries = session.exec(select(Surgery)).all()
        staff = session.exec(select(Staff)).all()
        st.metric("Total Surgeries", len(surgeries))
        st.metric("Total Staff", len(staff))
        if surgeries:
            df = pd.DataFrame([{"Staff":s.staff.name,"Hospital":s.hospital,"Region":s.region,"Date":s.date.date()} for s in surgeries])
            st.subheader("Surgeries by Hospital")
            chart = alt.Chart(df).mark_bar().encode(
                x="Hospital", y="count()", color="Hospital"
            )
            st.altair_chart(chart,use_container_width=True)

# ---------------------------
# LOG SURGERY
# ---------------------------
elif page=="Log Surgery":
    st.title("📝 Log Surgery")
    with get_session() as session:
        staff_list = session.exec(select(Staff)).all()
        staff_dict = {s.name:s for s in staff_list}
        staff_name = st.selectbox("Select Staff", list(staff_dict.keys()))
        staff = staff_dict[staff_name]
        date = st.date_input("Surgery Date", datetime.today())
        if st.button("Log Surgery"):
            surgery = Surgery(staff_id=staff.id, hospital=staff.hospital, region=staff.region, date=date)
            session.add(surgery)
            session.commit()
            st.success(f"Surgery logged for {staff_name} on {date}")

# ---------------------------
# REPORTS
# ---------------------------
elif page=="Reports":
    st.title("📑 Reports")
    with get_session() as session:
        surgeries = session.exec(select(Surgery)).all()
        if surgeries:
            df = pd.DataFrame([{"Staff":s.staff.name,"Hospital":s.hospital,"Region":s.region,"Date":s.date.date()} for s in surgeries])
            st.dataframe(df)
            col1,col2 = st.columns(2)
            with col1:
                st.download_button("⬇ Export Excel", export_excel(df), "report.xlsx")
            with col2:
                st.download_button("⬇ Export PDF", export_pdf(df), "report.pdf", mime="application/pdf")

# ---------------------------
# LEADERBOARD
# ---------------------------
elif page=="Leaderboard":
    st.title("🏆 Leaderboard")
    with get_session() as session:
        staff_list = session.exec(select(Staff)).all()
        leaderboard=[]
        for s in staff_list:
            surgeries = session.exec(select(Surgery).where(Surgery.staff_id==s.id)).all()
            leaderboard.append({"Staff":s.name,"Surgeries":len(surgeries)})
        df = pd.DataFrame(leaderboard).sort_values("Surgeries",ascending=False)
        st.dataframe(df)

# ---------------------------
# TRENDS
# ---------------------------
elif page=="Trends":
    st.title("📈 Monthly Surgery Trends")
    with get_session() as session:
        surgeries = session.exec(select(Surgery)).all()
        if surgeries:
            df = pd.DataFrame([{"Date":s.date.date()} for s in surgeries])
            df['Month'] = pd.to_datetime(df['Date']).dt.to_period('M').dt.to_timestamp()
            trend_df = df.groupby("Month").size().reset_index(name="Total Surgeries")
            line = alt.Chart(trend_df).mark_line(point=True, color="blue").encode(
                x="Month", y="Total Surgeries"
            )
            st.altair_chart(line, use_container_width=True)
