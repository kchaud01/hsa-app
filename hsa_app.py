import streamlit as st
import pandas as pd
import plotly.express as px
from supabase import create_client
import hashlib, re

# 1. SETUP & AESTHETICS (PRESERVED)
st.set_page_config(page_title="Shoebox", layout="wide")
st.markdown("<style>.stMetric {background:white; padding:12px; border-radius:10px; border:1px solid #eee;} h1 {text-align: center;}</style>", unsafe_allow_html=True)

try:
    sb = create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])
except Exception as e:
    st.error(f"Config Error: {e}"); st.stop()

st.title("KC's Receipt Shoebox")

def mk_l(u): return f'<a href="{u}" target="_blank">📄 View</a>' if pd.notnull(u) else "❌"

def ld_t(n):
    try:
        r = sb.table(n).select("*").execute()
        df = pd.DataFrame(r.data) if r.data else pd.DataFrame()
        if not df.empty:
            df['amount'] = df['amount'].astype(str).str.replace(r'[^\d.]', '', regex=True).astype(float).abs()
            df['date'] = pd.to_datetime(df['date'])
            df['Receipt'] = df.get('receipt_url', pd.Series([None]*len(df))).apply(mk_l)
        return df
    except: return pd.DataFrame()

h_db, r_db = ld_t("hsa_transactions"), ld_t("rental_transactions")

with st.sidebar:
    st.subheader("Cloud Utilities")
    if st.button("Check Connection"):
        try:
            sb.table("hsa_transactions").select("count", count="exact").limit(1).execute()
            st.success("Connected!")
        except: st.error("Failed")
    page = st.radio("Nav", ["Dashboard", "Uploader"], label_visibility="collapsed")

# 2. DASHBOARD
if page == "Dashboard":
    s1, s2 = st.tabs(["Medical (HSA)", "Rental (Atlanta)"])
    for d, t, c, g in [(h_db,"HSA","#00CC96",8550),(r_db,"Rental","#636EFA",None)]:
        with (s1 if t=="HSA" else s2):
            if not d.empty:
                st.metric(f"{t} Total", f"${d['amount'].sum():,.2f}")
                # FIXED: Ensuring full line completion for resampling
                tr = d.set_index('date').resample('YE')['amount'].sum().reset_index()
                tr['year'] = tr['date'].dt.year.astype(str)
                fig = px.bar(tr, x='year', y='amount', title=f"Annual {t} Spend", color_discrete_sequence=[c])
                fig.update_xaxes(type='category')
                st.plotly_chart(fig, use_container_width=True)
                st.write(d.sort_values('date', ascending=False)[['date','merchant_name','amount','Receipt']].to_html(escape=False, index=False), unsafe_allow_html=True)
            else: st.info(f"No {t} data.")

# 3. UPLOADER
else:
    l, r = st.columns(2)
    with l:
        st.subheader("📷 Capture")
        with st.form("cap", clear_on_submit=True):
            f, m, a, d = st.file_uploader("Rec", type=['jpg','png','pdf','jpeg']), st.text_input("Mcht"), st.number_input
