import streamlit as st
import pandas as pd
import plotly.express as px
from supabase import create_client
import hashlib, re

st.set_page_config(page_title="Shoebox", layout="wide")
st.markdown("<style>.stMetric {background:white; padding:12px; border-radius:10px; border:1px solid #eee;} h1 {text-align: center;}</style>", unsafe_allow_html=True)

# Supabase Client Initialization
try:
    sb = create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])
except Exception as e:
    st.error(f"Configuration Error: {e}"); st.stop()

st.title("KC's Receipt Shoebox")

def mk_l(u): return f'<a href="{u}" target="_blank">📄 View</a>' if pd.notnull(u) else "❌"

def load_transactions(table):
    try:
        resp = sb.table(table).select("*").execute()
        df = pd.DataFrame(resp.data) if resp.data else pd.DataFrame()
        if not df.empty:
            # Clean numeric data (handles bank comma formatting like "5,000.00")
            df['amount'] = df['amount'].astype(str).str.replace(r'[^\d.]', '', regex=True).astype(float).abs()
            df['date'] = pd.to_datetime(df['date'])
            df['Receipt'] = df.get('receipt_url', pd.Series([None]*len(df))).apply(mk_l)
        return df
    except Exception as e:
        st.warning(f"Could not load {table}: {e}")
        return pd.DataFrame()

# Load history for context and de-duplication
hsa = load_transactions("hsa_transactions")
rental = load_transactions("rental_transactions")

# Sidebar Utilities
with st.sidebar:
    st.subheader("Cloud Utilities")
    if st.button("Check Database Connection"):
        try:
            # Simple health check query
            sb.table("hsa_transactions").select("count", count="exact").limit(1).execute()
            st.success("Cloud Connection: ACTIVE")
        except Exception as e:
            st.error(f"Cloud Connection: FAILED\n{e}")
    
    st.divider()
    page = st.radio("Navigation", ["Dashboard", "Uploader"], label_visibility="collapsed")

if page == "Dashboard":
    s1, s2 = st.tabs(["Medical (HSA)", "Rental (Atlanta)"])
    
    with s1:
        if not hsa.empty:
            st.metric("HSA Total", f"${hsa['amount'].sum():,.2f}")
            tr = hsa.set_index('date').resample('YE')['amount'].sum().reset_index()
            tr['year'] = tr['date'].dt.year.astype(str)
            st.plotly_chart(px.bar(tr, x='year', y='amount', title="Annual HSA Spend", color_discrete_sequence=['#00CC96']), use_container_width=True)
            st.write(hsa.sort_values('date', ascending=False)[['date','merchant_name','amount','Receipt']].to_html(escape=False, index=False), unsafe_allow_html=True)
        else: st.info("No HSA data found.")

    with s2:
        if not rental.empty:
            st.metric("Rental Total", f"${rental['amount'].sum():,.2f}")
            tr_r = rental.set_index('date').resample('YE')['amount'].sum().reset_index()
            tr_r['year'] = tr_r['date'].dt.year.astype(str)
            st.plotly_chart(px.bar(tr_r, x='year', y='amount', title="Annual Rental Spend", color_discrete_sequence=['#636EFA']), use_container_width=True)
            st.write(rental.sort_values('date', ascending=False)[['date','merchant_name','amount','Receipt']].to_html(escape=False, index=False), unsafe_allow_html=True)
        else: st.info("No Rental data found.")

else:
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("📷 Capture")
        with st.form("manual_upload", clear_on_submit=True):
            f, m, a, d = st.file_uploader("Rec", type=['jpg','png','pdf','jpeg']), st.text_input("Mcht"), st.number_input("Amt"), st.date_input("Date")
            is_r = st.toggle("Save as Rental Transaction?")
            if st.form_submit_button("Save"):
                if f and m and a:
                    fn = f"{d}_{re.sub(r'\W+','',m).lower()}_{hashlib.md5(f.getvalue()).hexdigest()[:6]}.{f.name.split('.')[-1]}"
                    sb.storage.from_('receipts').upload(fn, f.getvalue())
                    u = sb.storage.from_('receipts').get_public_url(fn)
                    sb.table("rental_transactions" if is_r else "hsa_transactions").insert({"merchant_name":m, "amount":abs(a), "date":str(d), "receipt_url":u}).execute()
                    st.success("Saved!"); st.rerun()

    with col2:
        st.subheader("💳 Smart Sync CSV")
        csv_file = st.file_uploader("CSV Sync", type=['csv'])
        if csv_file:
            raw = csv_file.getvalue().decode('latin1').splitlines()
            skip_n = next((i for i, line in enumerate(raw) if any(k in line for k in ["Description", "Amount"])), 0)
            csv_file.seek(0)
            df = pd.read_csv(csv_file, skiprows=skip_n, engine='python', on_bad_lines='warn').fillna(0)
            
            dest = st.radio("Sync Destination", ["Medical (HSA)", "Rental (Atlanta)"])
            
            mc = next((c for c in df.columns if any(k in c for k in ['Description','Payee','Merchant'])), df.columns[0])
            ac = next((c for c in df.columns if any(k in c for k in ['Amount','Debit','Price'])), df.columns[-1])
            dc = next((c for c in df.columns if 'Date' in c), df.columns[0])
            
            v = df[[dc, mc, ac]].copy(); v.columns = ['Date', 'Merchant', 'Amount']
            v['Date'] = pd.to_datetime(v['Date']).dt.date.astype(str)
            v['Amount'] = v['Amount'].astype(str).str.replace(r'[^\d.]', '', regex=True).astype(float).abs()
            
            # Triple-Check De-dupe set: (Date, Merchant, Amount)
            hist_h = set(zip(hsa['date'].dt.date.astype(str), hsa['merchant_name'].str.lower(), hsa['amount'].round(2)))
            hist_r = set(zip(rental['date'].dt.date.astype(str), rental['merchant_name'].str.lower(), rental['amount'].round(2)))
            all_hist = hist_h.union(hist_r)

            def smart_check(row):
                d, m, a = str(row['Date']), str(row['Merchant']).lower(), round(float(row['Amount']), 2)
                if (d, m, a) in all_hist: return False
                if "Medical" in dest:
                    kws = ['emory','clinic','cvs','dermatology','dental','vision','pharm','doctor','health']
                    known = [str(
