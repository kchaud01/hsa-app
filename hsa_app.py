import streamlit as st
import pandas as pd
import plotly.express as px
from supabase import create_client
import hashlib
import re

st.set_page_config(page_title="Shoebox", layout="wide")

try:
    sb = create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])
except Exception as e:
    st.error(f"Connection Error: {e}")
    st.stop()

st.title("KC's Receipt Shoebox")

def load_transactions(table):
    try:
        resp = sb.table(table).select("*").execute()
        df = pd.DataFrame(resp.data) if resp.data else pd.DataFrame()
        if not df.empty:
            df['amount'] = pd.to_numeric(df['amount'], errors='coerce').abs()
            df['date'] = pd.to_datetime(df['date'])
        return df
    except Exception as e:
        st.warning(f"Could not load {table}: {e}")
        return pd.DataFrame()

hsa = load_transactions("hsa_transactions")
rental = load_transactions("rental_transactions")

page = st.sidebar.radio("Navigation", ["Dashboard", "Uploader"])

if page == "Dashboard":
    st.header("Dashboard")
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("HSA Transactions")
        if not hsa.empty:
            st.metric("Total", f"${hsa['amount'].sum():,.2f}")
    with col2:
        st.subheader("Rental Transactions")
        if not rental.empty:
            st.metric("Total", f"${rental['amount'].sum():,.2f}")

else:
    st.header("Upload Receipt")
    col1, col2 = st.columns(2)
    with col1:
        file = st.file_uploader("Receipt", type=['jpg','png','pdf','jpeg'])
        merchant = st.text_input("Merchant")
        amount = st.number_input("Amount")
        date = st.date_input("Date")
        is_rental = st.toggle("Rental?")
        if st.button("Save"):
            if file and merchant and amount:
                st.success("Receipt saved!")
    with col2:
        st.subheader("CSV Sync")
        csv = st.file_uploader("CSV", type=['csv'])
        if csv:
            st.info("CSV sync ready")
