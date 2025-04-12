from autogen import ConversableAgent, UserProxyAgent, AssistantAgent, register_function
from azure.identity import ClientSecretCredential
from azure.search.documents import SearchClient
from azure.core.credentials import AzureKeyCredential
from azure.storage.blob import BlobServiceClient, generate_blob_sas, BlobSasPermissions
import os
from datetime import datetime, timedelta
import requests
import pandas as pd
from dotenv import load_dotenv
from sqlalchemy import create_engine
from database.db import get_db
from database.db import Base, engine
import json
# from gauge_reader import gauge_reader
from dotenv import load_dotenv
load_dotenv()

SQLITE_DB_PATH = os.path.join(os.getcwd(),"new_db.db")
SQLALCHEMY_DATABASE_URL = f"sqlite:///{SQLITE_DB_PATH}"

# Create an SQLite engine
engine = create_engine(
    SQLALCHEMY_DATABASE_URL, 
    connect_args={"check_same_thread": False}  # Required for SQLite with SQLAlchemy
)

llm_config = [
    {
        "model": "GPT4",
        "api_key": os.getenv("APIKEY"),
        "base_url": os.getenv("BASEURL"),
        "api_type": "azure",
        "api_version": "2024-02-01",
        "max_tokens": 2048,
        "stream": True
    }
]

llm_config_GPT4V = [
    {
        "model": "GPT4",
        "api_key": os.getenv("APIKEY"),
        "base_url": os.getenv("GPT4VBASEURL"),
        "api_type": "azure",
        "api_version": "2024-02-15",
        "max_tokens": 2048,
    }
]


def get_customer_details(cust_id: int) -> str:
    """
    Function to get the customer details from an Excel file using customer ID.

    :param identifier: Customer ID (int).
    :return: A JSON string with customer details.
    """
    # Read the Excel file
    customer_file_path = "test_data.xlsx"
    df = pd.read_excel(customer_file_path)
    df['cust_id'] = df['cust_id'].astype(str)
    df['Transaction Date'] = pd.to_datetime(df['Transaction Date'], dayfirst=True, errors='coerce')
    # Convert input cust_id to string for comparison
    cust_id = str(cust_id)
    customers = df[df['cust_id'] == cust_id]
    # List to store customer details
    customer_list = []

    # Iterate over each customer and censor the cust_id
    for _, customer in customers.iterrows():
        cutomer_id = str(customer['cust_id'])
        censored_cust_id = '*' * (len(cutomer_id) - 4) + cutomer_id[-4:]

         # Convert 'Transaction Date' to string if it's a datetime object
        transaction_date = customer['Transaction Date']
        if pd.notna(transaction_date):  # Check if date is not NaT
            transaction_date = transaction_date.strftime('%Y-%m-%d')  # Format the date as 'YYYY-MM-DD'
        else:
            transaction_date = None  # Handle missing or invalid dates        
        # Create a dictionary with customer details
        cust_details = {
            'customer name': customer['Name'],
            'customer id': censored_cust_id,
            'email address': customer['email_address'],
            'Transaction type': customer['Transaction Type'],
            'Transaction Amount': customer['Transaction Amount'],
            'Transaction Date': transaction_date,
            'Reference Number': customer['Reference Number'],
            'Mode of Payment': customer['Mode of Payment'],
            'Transaction_Detail': customer['Detail']
        }
        # Add the dictionary to the list
        customer_list.append(cust_details)
    cust_det = json.dumps(customer_list)
    
    return cust_det


def bing_search(query: str) -> str:
    bing_endpoint = "https://api.bing.microsoft.com/v7.0/search"
    bing_subscription_key = "088b5b8f0ff84ae29388258b92ddcfba"
    headers = {"Ocp-Apim-Subscription-Key": bing_subscription_key}
    
    # Queries for OCBC and UOB separately
    ocbc_query = f"site:ocbc.com {query}"
    uob_query = f"site:uob.com.sg {query}"
    
    # Function to get search results
    def get_results(site_query):
        params = {"q": site_query, "textDecorations": True, "textFormat": "HTML"}
        response = requests.get(bing_endpoint, headers=headers, params=params)
        response.raise_for_status()
        return response.json().get("webPages", {}).get("value", [])
    
    
    ocbc_results = get_results(ocbc_query)
    uob_results = get_results(uob_query)
    
    combined_results = ocbc_results + uob_results
    
    results = []
    for result in combined_results:
        result_data = {
            "title": result["name"],
            "url": result["url"],
            "snippet": result["snippet"]
        }
        results.append(result_data)

    return results