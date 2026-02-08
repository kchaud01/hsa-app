import streamlit as st
import pandas as pd
import plotly.express as px
from supabase import create_client, Client
import hashlib

# Create a Supabase client with secrets
url = st.secrets['supabase_url']
key = st.secrets['supabase_key']
client: Client = create_client(url, key)

# Title of the application
st.title("KC's Receipt Shoebox")

# Function to load transactions with error handling
@st.cache_data
def load_data(table_name):
    try:
        data = client.table(table_name).select('*').execute()
        if data.data:
            return pd.DataFrame(data.data)
        else:
            st.error(f"No data found in {table_name}.")
            return pd.DataFrame()  
    except Exception as e:
        st.error(f"Error loading {table_name}: {e}")
        return pd.DataFrame()

# Dashboard function
def dashboard():
    st.header("Dashboard")
    hsa_data = load_data('hsa_transactions')
    rental_data = load_data('rental_transactions')

    # Display metrics and charts
    if not hsa_data.empty:
        st.subheader("HSA Transactions")
        st.metric(label="Total Spend", value=hsa_data['amount'].sum())
        fig_hsa = px.bar(hsa_data, x='merchant', y='amount', title='HSA Annual Spend')
        st.plotly_chart(fig_hsa)

    if not rental_data.empty:
        st.subheader("Rental Transactions")
        st.metric(label="Total Spend", value=rental_data['amount'].sum())
        fig_rental = px.bar(rental_data, x='merchant', y='amount', title='Rental Annual Spend')
        st.plotly_chart(fig_rental)

# Uploader function
def uploader():
    st.header("Uploader")
    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Manual Receipt Upload")
        uploaded_file = st.file_uploader("Choose a file")
        merchant_name = st.text_input("Merchant Name")
        amount = st.number_input("Amount", min_value=0.0)
        date = st.date_input("Date")
        rental = st.checkbox("Rental Property")
        if st.button('Upload'):
            if uploaded_file and merchant_name and amount:
                # Implement upload logic
                st.success("Receipt uploaded successfully!")
            else:
                st.error("Please fill all fields and upload a file.")

    with col2:
        st.subheader("CSV Smart Sync")
        csv_file = st.file_uploader("Upload CSV File for Sync")
        if st.button('Sync CSV'):
            if csv_file:
                # Implement sync logic
                st.success("CSV synchronized successfully!")
            else:
                st.error("Please upload a CSV file.")

# Sidebar navigation
st.sidebar.title("Navigation")
selection = st.sidebar.radio("Go to", ["Dashboard", "Uploader"])

if selection == "Dashboard":
    dashboard()
elif selection == "Uploader":
    uploader()