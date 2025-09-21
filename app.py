import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
from sqlmodel import SQLModel, Field, Session, create_engine, select
from datetime import datetime
from typing import Optional
from io import BytesIO
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors

# -----------------------------
# DATABASE SETUP
# -----------------------------
DATABASE_URL = "sqlite:///katia.db"
engine = create_engine(DATABASE_URL, echo=False)

class Staff(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    role: str = "Surgeon"
    region: Optional[str] = None
    hospital: Optional[str] = None
    target: int = 0
    created_at: datetime = Field(default_factory=datetime.utcnow)

class Surgery(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    staff_id: int = Field(foreign_key="staff.id")
    surgery_type: str
    region: str
    hospital: str
    date: datetime = Field(default_factory=datetime.utcnow)

def init_db():
    SQLModel.metadata.create_all(engine)

def get_session():
    return Session(engine)

# -----------------------------
# INIT DB + SAMPLE STAFF
# -----------------------------
init_db()
with get_session() as session:
    if not session.exec(select(Staff)).all():
        staff_list = [
            Staff(name="Dr. Erick", region="Eldoret", hospital="MTRH", target=20),
            Staff(name="Dr. Jane", region="Nairobi", hospital="KNH", target=15),
            Staff(name="Dr. Brian", region="Meru", hospital="Meru General", target=10),
        ]
        session.add_all(staff_list)
        session.commit()

# -----------------------------
# HELPERS
# -----------------------------
def get_data():
    with get_session() as session:
        staff = session.exec(select(Staff)).all()
        surgeries = session.exec(select(Surgery)).all()
    df_staff = pd.DataFrame([s.dict() for s in staff]) if staff else pd.DataFrame()
    df_surg = pd.DataFrame([s.dict() for s in surgeries]) if surgeries else pd.DataFrame()
    return df_staff, df_surg

def export_excel(df_staff, df_surg):
    output = BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df_staff.to_excel(writer, sheet_name="Staff", index=False)
        df_surg.to_excel(writer, sheet_name="Surgeries", index=False)
    return output.getvalue()

def export_pdf(df_staff, df_surg):
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4)
    styles = getSampleStyleSheet()
    story = []

    story.append(Paragraph("Surgery Report", styles["Title"]))
    story.append(Spacer(1, 12))

    if not df_surg.empty:
        total = len(df_surg)
        by_region = df_surg.groupby("region").size().reset_index(name="count")
        by_hospital = df_surg.groupby("hospital").size().reset_index(name="count")

        story.append(Paragraph(f"Total Surgeries: {total}", styles["Heading2"]))
        story.append(Spacer(1, 12))

        # Region table
        story.append(Paragraph("By Region", styles["Heading3"]))
        table_data = [by_region.columns.tolist()] + by_region.values.tolist()
        table = Table(table_data)
        table.setStyle(TableStyle([("GRID", (0,0), (-1,-1), 0.5, colors.black)]))
        story.append(table)
        story.append(Spacer(1, 12))

        # Hospital table
        story.append(Paragraph("By Hospital", styles["Heading3"]))
        table_data = [by_hospital.columns.tolist()] + by_hospital.values.tolist()
        table = Table(table_data)
        table.setStyle(TableStyle([("GRID", (0,0), (-1,-1), 0.5, colors.black)]))
        story.append(table)

    doc.build(story)
    return buffer.getvalue()

# -----------------------------
# STREAMLIT APP
# -----------------------------
st.set_page_config(page_title="Surgery Dashboard", layout="wide")

with st.sidebar:
    st.image("https://img.icons8.com/color/96/surgery.png", width=64)
    st.title("Surgery Dashboard")
    menu = st.radio("Menu", ["Dashboard", "Surgeries", "Targets", "Exports"])
    st.markdown("---")
    st.caption("Built for Staff Performance & Insights")

# -----------------------------
# DASHBOARD
# -----------------------------
if menu == "Dashboard":
    st.header("📊 Surgery Dashboard")
    df_staff, df_surg = get_data()

    if df_staff.empty:
        st.warning("No staff found.")
    else:
        # KPIs
        total_staff = len(df_staff)
        total_surgeries = len(df_surg)
        top_performer = "-"
        avg_completion = 0

        if not df_surg.empty:
            counts = df_surg.groupby("staff_id").size()
            staff_counts = df_staff.set_index("id").join(counts.rename("completed")).fillna(0)
            staff_counts["completed"] = staff_counts["completed"].astype(int)
            staff_counts["progress %"] = (
                staff_counts["completed"] / staff_counts["target"].replace(0, 1) * 100
            ).round(1)
            top_performer = staff_counts.sort_values("completed", ascending=False).iloc[0]["name"]
            avg_completion = staff_counts["completed"].mean()

        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Total Staff", total_staff)
        col2.metric("Total Surgeries", total_surgeries)
        col3.metric("Top Performer", top_performer)
        col4.metric("Avg Surgeries per Staff", f"{avg_completion:.1f}")

        # Charts
        if not df_surg.empty:
            st.subheader("📈 Trends Over Time")
            df_surg["month"] = pd.to_datetime(df_surg["date"]).dt.to_period("M")
            trend = df_surg.groupby("month").size()
            fig, ax = plt.subplots()
            trend.plot(kind="line", marker="o", ax=ax)
            ax.set_ylabel("Surgeries")
            st.pyplot(fig)

            st.subheader("🏆 Leaderboard")
            leaderboard = staff_counts.sort_values("completed", ascending=False)
            fig, ax = plt.subplots()
            ax.barh(leaderboard["name"], leaderboard["completed"], color="skyblue")
            ax.set_xlabel("Completed Surgeries")
            st.pyplot(fig)

            st.subheader("🌍 Distribution")
            col1, col2 = st.columns(2)
            with col1:
                region_data = df_surg["region"].value_counts()
                fig, ax = plt.subplots()
                ax.pie(region_data, labels=region_data.index, autopct="%1.1f%%")
                ax.set_title("By Region")
                st.pyplot(fig)
            with col2:
                hospital_data = df_surg["hospital"].value_counts()
                fig, ax = plt.subplots()
                ax.pie(hospital_data, labels=hospital_data.index, autopct="%1.1f%%")
                ax.set_title("By Hospital")
                st.pyplot(fig)

# -----------------------------
# SURGERIES
# -----------------------------
elif menu == "Surgeries":
    tab1, tab2 = st.tabs(["📝 Log Surgery", "📑 Reports"])
    df_staff, df_surg = get_data()

    with tab1:
        st.subheader("Log Surgery")
        if df_staff.empty:
            st.warning("No staff available.")
        else:
            staff_dict = {s["name"]: s for s in df_staff.to_dict(orient="records")}
            surgeon = st.selectbox("Surgeon", staff_dict.keys())
            surgery_type = st.text_input("Surgery Type")
            region = st.text_input("Region")
            hospital = st.text_input("Hospital")
            if st.button("Log Surgery"):
                with get_session() as session:
                    staff = staff_dict[surgeon]
                    surgery = Surgery(
                        staff_id=staff["id"],
                        surgery_type=surgery_type,
                        region=region,
                        hospital=hospital,
                        date=datetime.utcnow(),
                    )
                    session.add(surgery)
                    session.commit()
                st.success(f"✅ Surgery logged for {surgeon}")

    with tab2:
        st.subheader("Reports")
        if df_surg.empty:
            st.info("No surgeries logged yet.")
        else:
            st.dataframe(df_surg)
            st.subheader("By Surgeon")
            st.dataframe(df_surg.groupby("staff_id").size().reset_index(name="surgeries"))
            st.subheader("By Region")
            st.dataframe(df_surg.groupby("region").size().reset_index(name="surgeries"))
            st.subheader("By Hospital")
            st.dataframe(df_surg.groupby("hospital").size().reset_index(name="surgeries"))

# -----------------------------
# TARGETS
# -----------------------------
elif menu == "Targets":
    st.header("🎯 Manage Targets & Staff")
    action = st.radio("Action", ["Assign Targets", "Add Staff"])
    df_staff, _ = get_data()

    if action == "Assign Targets":
        if df_staff.empty:
            st.warning("No staff found.")
        else:
            staff_dict = {s["name"]: s for s in df_staff.to_dict(orient="records")}
            selected = st.selectbox("Select Staff", staff_dict.keys())
            new_target = st.number_input("Set Target", min_value=0, step=1)
            if st.button("Update Target"):
                with get_session() as session:
                    staff = session.get(Staff, staff_dict[selected]["id"])
                    staff.target = new_target
                    session.add(staff)
                    session.commit()
                st.success(f"✅ Target updated for {selected}")

    elif action == "Add Staff":
        name = st.text_input("Name")
        region = st.text_input("Region")
        hospital = st.text_input("Hospital")
        target = st.number_input("Target", min_value=0, step=1)
        if st.button("Add Staff"):
            with get_session() as session:
                staff = Staff(name=name, region=region, hospital=hospital, target=target)
                session.add(staff)
                session.commit()
            st.success(f"✅ Staff {name} added")

# -----------------------------
# EXPORTS
# -----------------------------
elif menu == "Exports":
    st.header("📤 Export Reports")
    df_staff, df_surg = get_data()

    if st.button("⬇️ Download Excel"):
        data = export_excel(df_staff, df_surg)
        st.download_button("Download Excel File", data, "surgery_reports.xlsx")

    if st.button("⬇️ Download PDF"):
        data = export_pdf(df_staff, df_surg)
        st.download_button("Download PDF File", data, "surgery_report.pdf")
