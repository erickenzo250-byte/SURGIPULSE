import streamlit as st
from sqlmodel import SQLModel, Field, Session, create_engine, select, Relationship
from typing import Optional, List
from datetime import datetime
import pandas as pd
import altair as alt
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
import io

# -------------------------------
# DATABASE MODELS
# -------------------------------
class Staff(SQLModel, table=True):
    __tablename__ = "staff"

    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    role: str
    hospital: str
    region: str
    created_at: datetime = Field(default_factory=datetime.utcnow)

    surgeries: List["Surgery"] = Relationship(back_populates="staff")
    targets: List["Target"] = Relationship(back_populates="staff")


class Surgery(SQLModel, table=True):
    __tablename__ = "surgery"

    id: Optional[int] = Field(default=None, primary_key=True)
    staff_id: int = Field(foreign_key="staff.id")
    hospital: str
    region: str
    date: datetime = Field(default_factory=datetime.utcnow)

    staff: Staff = Relationship(back_populates="surgeries")


class Target(SQLModel, table=True):
    __tablename__ = "target"

    id: Optional[int] = Field(default=None, primary_key=True)
    staff_id: int = Field(foreign_key="staff.id")
    month: str
    target_surgeries: int
    assigned_at: datetime = Field(default_factory=datetime.utcnow)

    staff: Staff = Relationship(back_populates="targets")


# -------------------------------
# DATABASE SETUP
# -------------------------------
engine = create_engine("sqlite:///surgipulse.db")
SQLModel.metadata.create_all(engine)


def get_session():
    return Session(engine)


def seed_default_staff():
    """Seed default staff if none exist"""
    with get_session() as session:
        staff_count = session.exec(select(Staff)).all()
        if not staff_count:
            staff_list = [
                Staff(name="Dr. Alice", role="Surgeon", hospital="Eldoret Hospital", region="Rift Valley"),
                Staff(name="Dr. Brian", role="Surgeon", hospital="Kenyatta Hospital", region="Nairobi"),
                Staff(name="Dr. Carol", role="Surgeon", hospital="Coast General", region="Coast"),
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
# STREAMLIT APP
# -------------------------------
st.set_page_config(page_title="SurgiPulse Dashboard", layout="wide")
st.sidebar.title("SurgiPulse Navigation")
page = st.sidebar.radio("Go to", ["Dashboard", "Log Surgery", "Assign Targets", "Reports", "Leaderboard"])


# -------------------------------
# DASHBOARD
# -------------------------------
if page == "Dashboard":
    st.title("📊 Surgery Dashboard")

    with get_session() as session:
        surgeries = session.exec(select(Surgery)).all()
        staff = session.exec(select(Staff)).all()

        st.metric("Total Surgeries", len(surgeries))
        st.metric("Total Staff", len(staff))

        if surgeries:
            df = pd.DataFrame([{
                "Region": s.region,
                "Hospital": s.hospital,
                "Date": s.date.date()
            } for s in surgeries])

            st.subheader("📈 Surgeries by Region")
            region_chart = alt.Chart(df).mark_bar().encode(
                x="Region",
                y="count()",
                color="Region"
            )
            st.altair_chart(region_chart, use_container_width=True)


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
            df = pd.DataFrame([{
                "Staff": s.staff.name,
                "Hospital": s.hospital,
                "Region": s.region,
                "Date": s.date.date()
            } for s in surgeries])

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
                x="Hospital",
                y="count()",
                color="Hospital"
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
