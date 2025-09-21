import streamlit as st
import pandas as pd
from sqlalchemy import func
from db import get_session, User, Target, Surgery, Deliverable
from reports import generate_monthly_report


def update_deliverables():
    with get_session() as session:
        deliverables = session.query(Deliverable).all()
        for d in deliverables:
            target = session.get(Target, d.target_id)

            query = (
                session.query(func.count(Surgery.id))
                .filter(Surgery.staff_id == target.staff_id)
                .filter(func.strftime("%Y-%m", Surgery.date) == target.period[:7])
            )
            if target.case_type != "all":
                query = query.filter(Surgery.surgery_type == target.case_type)

            completed_cases = query.scalar()
            d.is_completed = completed_cases >= target.target_cases

        session.commit()


st.title("🏥 Surgery Target Dashboard")

with get_session() as session:
    results = (
        session.query(
            User.username,
            Target.period,
            Target.case_type,
            Target.target_cases,
            func.count(Surgery.id).label("completed_cases"),
        )
        .join(Target, User.id == Target.staff_id)
        .join(Surgery, Surgery.staff_id == User.id, isouter=True)
        .group_by(User.username, Target.period, Target.case_type, Target.target_cases)
        .all()
    )

df = pd.DataFrame(results, columns=["Staff", "Period", "Case Type", "Target Cases", "Completed Cases"])
df["Progress %"] = (df["Completed Cases"] / df["Target Cases"] * 100).round(1)

st.dataframe(df)
st.bar_chart(df.set_index(["Staff", "Case Type"])[["Target Cases", "Completed Cases"]])

period = st.selectbox("Select reporting period", df["Period"].unique())
months = sorted(df["Period"].unique().tolist())

if st.button("📊 Generate Monthly Report"):
    excel_file, pdf_file = generate_monthly_report(period, months)
    st.success("Reports generated successfully!")
    st.download_button("⬇ Download Excel", open(excel_file, "rb"), file_name=f"surgery_report_{period}.xlsx")
    st.download_button("⬇ Download PDF", open(pdf_file, "rb"), file_name=f"surgery_report_{period}.pdf")
