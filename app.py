import streamlit as st
from sqlmodel import SQLModel, Field, Session, select, create_engine, Relationship
from datetime import datetime, timedelta
import pandas as pd
import altair as alt
import io
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
import random

# ---------------------------
# DATABASE MODELS
# ---------------------------

class Staff(SQLModel, table=True):
    id: int = Field(default=None, primary_key=True)
    name: str
    role: str
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
    date: datetime = Field(default_factory=datetime.utcnow)
    staff: Staff = Relationship(back_populates="surgeries")

class Target(SQLModel, table=True):
    id: int = Field(default=None, primary_key=True)
    staff_id: int = Field(foreign_key="staff.id")
    month: str
    target_surgeries: int
    assigned_at: datetime = Field(default_factory=datetime.utcnow)
    staff: Staff = Relationship(back_populates="targets")

# ---------------------------
# DATABASE SETUP
# ---------------------------

engine = create_engine("sqlite:///data/surgipulse.db")
SQLModel.metadata.create_all(engine)

def get_session():
    return Session(engine)

# ---------------------------
# SEED DEFAULT STAFF
# ---------------------------

def seed_default_staff():
    default_staff = [
        {"name":"Josephine","role":"Surgeon","hospital":"Nairobi Hospital","region":"Nairobi/Kijabe"},
        {"name":"Carol","role":"Surgeon","hospital":"Kenyatta Hospital","region":"Nairobi/Kijabe"},
        {"name":"Jacob","role":"Surgeon","hospital":"Eldoret Hospital","region":"Eldoret"},
        {"name":"Naomi","role":"Surgeon","hospital":"Meru County Hospital","region":"Meru"},
        {"name":"Charity","role":"Surgeon","hospital":"Mombasa Hospital","region":"Mombasa"},
        {"name":"Kevin","role":"Surgeon","hospital":"Kijabe Hospital","region":"Nairobi/Kijabe"},
        {"name":"Miriam","role":"Surgeon","hospital":"Kisii Teaching","region":"Meru"},
        {"name":"Brian","role":"Surgeon","hospital":"Eldoret Hospital","region":"Eldoret"},
        {"name":"James","role":"Surgeon","hospital":"Meru County Hospital","region":"Meru"},
        {"name":"Faith","role":"Surgeon","hospital":"Mombasa Hospital","region":"Mombasa"},
        {"name":"Geoffrey","role":"Surgeon","hospital":"Nairobi Hospital","region":"Nairobi/Kijabe"},
        {"name":"Spencer","role":"Surgeon","hospital":"Kenyatta Hospital","region":"Nairobi/Kijabe"},
        {"name":"Evans","role":"Surgeon","hospital":"Eldoret Hospital","region":"Eldoret"},
        {"name":"Eric","role":"Surgeon","hospital":"Meru County Hospital","region":"Meru"},
    ]
    with get_session() as session:
        existing = session.exec(select(Staff)).all()
        if not existing:
            staff_objs = [Staff(**s) for s in default_staff]
            session.add_all(staff_objs)
            session.commit()

seed_default_staff()

# ---------------------------
# RANDOM SURGERY DATA (JAN TO NOW)
# ---------------------------

def generate_random_surgeries():
    with get_session() as session:
        staff_list = session.exec(select(Staff)).all()
        existing = session.exec(select(Surgery)).all()
        if existing:
            return
        for s in staff_list:
            for _ in range(random.randint(5,15)):
                days_ago = random.randint(0, datetime.today().timetuple().tm_yday)
                date = datetime.today() - timedelta(days=days_ago)
                surgery = Surgery(staff_id=s.id, hospital=s.hospital, region=s.region, date=date)
                session.add(surgery)
        session.commit()

generate_random_surgeries()

# ---------------------------
# EXPORT HELPERS
# ---------------------------

def export_excel(df: pd.DataFrame):
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="Report")
    return output.getvalue()

def export_pdf(df: pd.DataFrame):
    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4
    text = c.beginText(40, height - 40)
    text.setFont("Helvetica", 10)
    lines = df.to_string(index=False).split("\n")
    for line in lines:
        text.textLine(line)
    c.drawText(text)
    c.showPage()
    c.save()
    buffer.seek(0)
    return buffer.getvalue()

# ---------------------------
# STREAMLIT APP
# ---------------------------

st.set_page_config(page_title="SurgiPulse Pro", layout="wide")
st.sidebar.title("🩺 SurgiPulse Navigation")
page = st.sidebar.radio("Go to", ["Dashboard", "Log Surgery", "Assign Targets", "Reports", "Leaderboards", "Trends"])

# ---------------------------
# DASHBOARD
# ---------------------------
if page == "Dashboard":
    st.title("📊 Surgery Dashboard")
    with get_session() as session:
        surgeries = session.exec(select(Surgery)).all()
        staff = session.exec(select(Staff)).all()
        st.metric("Total Surgeries", len(surgeries))
        st.metric("Total Staff", len(staff))

        if surgeries:
            df = pd.DataFrame([{"Region": s.region, "Hospital": s.hospital, "Date": s.date.date()} for s in surgeries])
            st.subheader("📈 Surgeries by Region")
            region_chart = alt.Chart(df).mark_bar().encode(
                x="Region", y="count()", color="Region"
            )
            st.altair_chart(region_chart, use_container_width=True)

# ---------------------------
# LOG SURGERY
# ---------------------------
elif page == "Log Surgery":
    st.title("📝 Log Surgery")
    with get_session() as session:
        staff_list = session.exec(select(Staff)).all()
        staff_dict = {s.name: s for s in staff_list}
        staff_name = st.selectbox("Select Staff", list(staff_dict.keys()))
        staff = staff_dict[staff_name]

        hospital = st.text_input("Hospital", staff.hospital)
        region = st.text_input("Region", staff.region)
        date = st.date_input("Surgery Date", datetime.today())

        if st.button("Log Surgery"):
            new_surgery = Surgery(staff_id=staff.id, hospital=hospital, region=region, date=date)
            session.add(new_surgery)
            session.commit()
            st.success(f"Surgery logged for {staff_name} on {date}")

# ---------------------------
# ASSIGN TARGETS
# ---------------------------
elif page == "Assign Targets":
    st.title("🎯 Assign Surgery Targets")
    with get_session() as session:
        staff_list = session.exec(select(Staff)).all()
        staff_dict = {s.name: s for s in staff_list}
        staff_name = st.selectbox("Select Staff", list(staff_dict.keys()))
        staff = staff_dict[staff_name]

        month = st.selectbox("Month", [
            "January", "February", "March", "April", "May", "June",
            "July", "August", "September", "October", "November", "December"
        ])
        target = st.number_input("Target Surgeries", min_value=1, step=1)

        if st.button("Assign Target"):
            new_target = Target(staff_id=staff.id, month=month, target_surgeries=target)
            session.add(new_target)
            session.commit()
            st.success(f"Assigned target of {target} surgeries for {staff_name} in {month}")

# ---------------------------
# REPORTS
# ---------------------------
elif page == "Reports":
    st.title("📑 Reports")
    with get_session() as session:
        surgeries = session.exec(select(Surgery)).all()
        if surgeries:
            df = pd.DataFrame([{"Staff": s.staff.name, "Hospital": s.hospital, "Region": s.region, "Date": s.date.date()} for s in surgeries])
            st.subheader("Surgeries by Staff")
            st.dataframe(df)

            col1, col2 = st.columns(2)
            with col1:
                excel = export_excel(df)
                st.download_button("⬇ Export to Excel", excel, "report.xlsx")
            with col2:
                pdf = export_pdf(df)
                st.download_button("⬇ Export to PDF", pdf, "report.pdf", mime="application/pdf")

            st.subheader("📊 Surgeries by Hospital")
            hospital_chart = alt.Chart(df).mark_bar().encode(
                x="Hospital", y="count()", color="Hospital"
            )
            st.altair_chart(hospital_chart, use_container_width=True)

# ---------------------------
# LEADERBOARDS
# ---------------------------
elif page == "Leaderboards":
    st.title("🏆 Leaderboards")
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
        df_lb = pd.DataFrame(leaderboard).sort_values(by="Surgeries", ascending=False)
        st.dataframe(df_lb)

# ---------------------------
# TRENDS
# ---------------------------
elif page == "Trends":
    st.title("📈 Monthly Trends (Total Surgeries)")
    with get_session() as session:
        surgeries = session.exec(select(Surgery)).all()
        if surgeries:
            df = pd.DataFrame([{"Date": s.date.date()} for s in surgeries])
            df['Month'] = pd.to_datetime(df['Date']).dt.to_period('M').dt.to_timestamp()
            df_grouped = df.groupby('Month').size().reset_index(name='Total Surgeries')
            line_chart = alt.Chart(df_grouped).mark_line(point=True).encode(
                x='Month:T',
                y='Total Surgeries:Q',
                tooltip=['Month','Total Surgeries']
            ).properties(width=800, height=400)
            st.altair_chart(line_chart, use_container_width=True)
