import streamlit as st
from sqlmodel import SQLModel, Field, Session, create_engine, select, Relationship
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
import altair as alt
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
import io
import random

# -------------------------------
# DATABASE MODELS
# -------------------------------

class Staff(SQLModel, table=True):
    id: int = Field(default=None, primary_key=True)
    name: str
    role: str
    hospital: str
    region: str
    created_at: datetime = Field(default_factory=datetime.utcnow)

    surgeries: "list[Surgery] | None" = Relationship(back_populates="staff")
    targets: "list[Target] | None" = Relationship(back_populates="staff")


class Surgery(SQLModel, table=True):
    id: int = Field(default=None, primary_key=True)
    staff_id: int = Field(foreign_key="staff.id")
    hospital: str
    region: str
    date: datetime = Field(default_factory=datetime.utcnow)

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
# SEED DEFAULT STAFF (only once)
# -------------------------------
def seed_default_staff():
    with get_session() as session:
        existing = session.exec(select(Staff)).all()
        if not existing:
            staff_list = [
                Staff(name="Josephine", role="Nurse", hospital="Moi Teaching & Referral Hospital", region="Eldoret"),
                Staff(name="Carol", role="Surgeon", hospital="Aga Khan University Hospital", region="Nairobi/Kijabe"),
                Staff(name="Jacob", role="Technician", hospital="Meru Teaching & Referral", region="Meru"),
                Staff(name="Naomi", role="Nurse", hospital="Coast General Hospital", region="Mombasa"),
                Staff(name="Charity", role="Surgeon", hospital="Kenyatta National Hospital", region="Nairobi/Kijabe"),
                Staff(name="Kevin", role="Assistant", hospital="St. Luke’s Orthopedic Hospital", region="Eldoret"),
                Staff(name="Miriam", role="Surgeon", hospital="Meru Level 5 Hospital", region="Meru"),
                Staff(name="Brian", role="Technician", hospital="Mombasa Hospital", region="Mombasa"),
                Staff(name="James", role="Surgeon", hospital="Kijabe Mission Hospital", region="Nairobi/Kijabe"),
                Staff(name="Faith", role="Nurse", hospital="Reale Hospital", region="Eldoret"),
                Staff(name="Geoffrey", role="Technician", hospital="Mater Hospital", region="Nairobi/Kijabe"),
                Staff(name="Spencer", role="Surgeon", hospital="Pandya Memorial Hospital", region="Mombasa"),
                Staff(name="Evans", role="Nurse", hospital="Meru General Hospital", region="Meru"),
                Staff(name="Eric", role="Surgeon", hospital="Moi Teaching & Referral Hospital", region="Eldoret"),
            ]
            session.add_all(staff_list)
            session.commit()

seed_default_staff()


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


# -------------------------------
# RANDOM TEST DATA GENERATOR
# -------------------------------
def generate_random_surgeries():
    with get_session() as session:
        staff_list = session.exec(select(Staff)).all()
        start_date = datetime(2025, 1, 1)
        end_date = datetime.today()
        days = (end_date - start_date).days

        for s in staff_list:
            # Each staff gets between 10–50 surgeries randomly spread across months
            num_surgeries = random.randint(10, 50)
            for _ in range(num_surgeries):
                random_date = start_date + timedelta(days=random.randint(0, days))
                surgery = Surgery(
                    staff_id=s.id,
                    hospital=s.hospital,
                    region=s.region,
                    date=random_date
                )
                session.add(surgery)
        session.commit()


# -------------------------------
# STREAMLIT APP
# -------------------------------

st.set_page_config(page_title="SurgiPulse Dashboard", layout="wide")
st.sidebar.title("⚙️ SurgiPulse Navigation")
page = st.sidebar.radio("Go to", ["Dashboard", "Log Surgery", "Assign Targets", "Reports", "Leaderboard", "⚡ Generate Test Data"])


# -------------------------------
# DASHBOARD
# -------------------------------
if page == "Dashboard":
    st.title("📊 Surgery Dashboard")
    with get_session() as session:
        surgeries = session.exec(select(Surgery)).all()
        staff = session.exec(select(Staff)).all()

        col1, col2 = st.columns(2)
        col1.metric("Total Surgeries", len(surgeries))
        col2.metric("Total Staff", len(staff))

        if surgeries:
            df = pd.DataFrame([{"Region": s.region, "Hospital": s.hospital, "Date": s.date.date()} for s in surgeries])

            # Surgeries by Region
            st.subheader("📍 Surgeries by Region")
            region_chart = alt.Chart(df).mark_bar().encode(
                x="Region", y="count()", color="Region"
            )
            st.altair_chart(region_chart, use_container_width=True)

            # Trend by Month
            st.subheader("📈 Monthly Surgery Trend (Jan–Now)")
            df["Month"] = pd.to_datetime(df["Date"]).dt.to_period("M").astype(str)
            trend = df.groupby("Month").size().reset_index(name="Total Surgeries")
            all_months = pd.period_range("2025-01", datetime.today().strftime("%Y-%m")).astype(str)
            trend = trend.set_index("Month").reindex(all_months, fill_value=0).reset_index().rename(columns={"index": "Month"})
            line_chart = alt.Chart(trend).mark_line(point=True).encode(
                x="Month", y="Total Surgeries"
            )
            st.altair_chart(line_chart, use_container_width=True)


# -------------------------------
# LOG SURGERY
# -------------------------------
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


# -------------------------------
# ASSIGN TARGETS
# -------------------------------
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


# -------------------------------
# REPORTS
# -------------------------------
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


# -------------------------------
# LEADERBOARD
# -------------------------------
elif page == "Leaderboard":
    st.title("🏆 Leaderboard")
    with get_session() as session:
        staff_list = session.exec(select(Staff)).all()
        leaderboard = []
        for s in staff_list:
            surgeries = session.exec(select(Surgery).where(Surgery.staff_id == s.id)).all()
            targets = session.exec(select(Target).where(Target.staff_id == s.id)).all()
            total_target = sum(t.target_surgeries for t in targets)
            leaderboard.append({
                "Staff": s.name,
                "Surgeries": len(surgeries),
                "Target": total_target,
                "Progress": f"{len(surgeries)}/{total_target}" if total_target else "No target"
            })
        df = pd.DataFrame(leaderboard).sort_values(by="Surgeries", ascending=False)
        st.dataframe(df)


# -------------------------------
# GENERATE TEST DATA
# -------------------------------
elif page == "⚡ Generate Test Data":
    st.title("⚡ Generate Random Test Data")
    if st.button("Generate Now"):
        generate_random_surgeries()
        st.success("✅ Random test data generated successfully!")
        st.rerun()
