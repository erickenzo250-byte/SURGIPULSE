from datetime import datetime
from typing import Optional, List

import pandas as pd
import streamlit as st
from sqlmodel import SQLModel, Field, create_engine, Session, Relationship
from sqlalchemy import func

# -------------------------
# DATABASE MODELS
# -------------------------

class Staff(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    role: str
    surgeries: List["Surgery"] = Relationship(back_populates="staff")
    targets: List["SurgeryTarget"] = Relationship(back_populates="staff")

class Surgery(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    staff_id: int = Field(foreign_key="staff.id")
    surgery_type: str
    date: datetime = Field(default_factory=datetime.utcnow)
    staff: Optional[Staff] = Relationship(back_populates="surgeries")

class SurgeryTarget(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    staff_id: int = Field(foreign_key="staff.id")
    month: str   # e.g. "2025-09"
    target_count: int
    staff: Optional[Staff] = Relationship(back_populates="targets")

# -------------------------
# DATABASE SETUP
# -------------------------

sqlite_url = "sqlite:///database.db"
engine = create_engine(sqlite_url, echo=True)

def init_db():
    SQLModel.metadata.create_all(engine)

def get_session():
    return Session(engine)

# -------------------------
# REPORT FUNCTIONS
# -------------------------

def get_staff_progress():
    with get_session() as session:
        results = []
        staff_list = session.query(Staff).all()

        for staff in staff_list:
            # Get all targets for this staff
            targets = session.query(SurgeryTarget).filter(SurgeryTarget.staff_id == staff.id).all()
            total_target = sum(t.target_count for t in targets)

            # Count surgeries logged
            surgeries_done = session.query(func.count(Surgery.id)).filter(Surgery.staff_id == staff.id).scalar()

            results.append({
                "name": staff.name,
                "role": staff.role,
                "total_targets": total_target,
                "achieved": surgeries_done,
                "progress_%": round((surgeries_done / total_target * 100), 1) if total_target > 0 else 0,
            })
        return results

# -------------------------
# STREAMLIT APP
# -------------------------

init_db()

st.set_page_config(page_title="Surgery Dashboard", layout="wide")
st.title("🏥 Staff Surgery Targets Dashboard")

# -------------------------
# Admin Panel: Assign Staff Targets
# -------------------------
st.sidebar.header("⚙️ Admin Panel")

with st.sidebar.form("assign_target_form"):
    staff_name = st.text_input("Staff Name")
    staff_role = st.text_input("Role (e.g. Surgeon, Nurse)")
    month = st.text_input("Month (YYYY-MM)", "2025-09")
    target_count = st.number_input("Target Surgeries", min_value=1, value=5)
    submitted = st.form_submit_button("Assign Target")

    if submitted:
        with get_session() as session:
            # Ensure staff exists
            staff = session.query(Staff).filter(Staff.name == staff_name).first()
            if not staff:
                staff = Staff(name=staff_name, role=staff_role)
                session.add(staff)
                session.commit()
                session.refresh(staff)

            # Assign monthly target
            target = SurgeryTarget(staff_id=staff.id, month=month, target_count=target_count)
            session.add(target)
            session.commit()
            st.success(f"✅ Target of {target_count} surgeries assigned to {staff_name} for {month}")

# -------------------------
# Staff Panel: Log Surgeries
# -------------------------
st.sidebar.header("📝 Staff Panel")

with st.sidebar.form("log_surgery_form"):
    staff_name_log = st.text_input("Staff Name (Log Surgery)")
    surgery_type = st.text_input("Surgery Type")
    log_submit = st.form_submit_button("Log Surgery")

    if log_submit:
        with get_session() as session:
            staff = session.query(Staff).filter(Staff.name == staff_name_log).first()
            if staff:
                surgery = Surgery(staff_id=staff.id, surgery_type=surgery_type)
                session.add(surgery)
                session.commit()
                st.success(f"✅ Logged surgery for {staff_name_log} ({surgery_type})")
            else:
                st.error("❌ Staff not found. Please ask Admin to add them first.")

# -------------------------
# Reports & Progress
# -------------------------
st.header("📊 Staff Surgery Progress")

progress_data = get_staff_progress()
df = pd.DataFrame(progress_data)

if not df.empty:
    st.dataframe(df)

    col1, col2 = st.columns(2)
    with col1:
        st.subheader("Surgeries Achieved")
        st.bar_chart(df.set_index("name")[["achieved"]])
    with col2:
        st.subheader("Surgery Targets")
        st.bar_chart(df.set_index("name")[["total_targets"]])
else:
    st.info("No staff or targets assigned yet.")
