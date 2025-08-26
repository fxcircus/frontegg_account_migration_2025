import csv
import requests
import os
from utility.frontegg_client import FronteggClient
from dotenv import load_dotenv
import logging

# Load environment variables
load_dotenv()

# Update these to match your environment
CSV_FILE_PATH = "account_data/user_tenants_with_roles.csv"
API_URL = "https://api.us.frontegg.com/identity/resources/users/bulk/v1/invite"

# Configure logging
logging.basicConfig(filename='log.txt', level=logging.INFO, 
                    format='%(asctime)s - %(levelname)s - %(message)s')

def main():
    # Initialize Frontegg client to get the token
    frontegg_client = FronteggClient(os.getenv("BASE_URL_2"), 
                                     os.getenv("CLIENT_ID_2"), 
                                     os.getenv("API_KEY_2"))
    BEARER_TOKEN = frontegg_client.token

    logging.info("Starting bulk invite process")

    # Dictionary to group data: { tenantId: { email: { "name": ..., "roleIds": set(...) } } }
    grouped_data = {}

    # Read the CSV file and process each row
    try:
        with open(CSV_FILE_PATH, mode="r", newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            rows = list(reader)  # Convert iterator to list to allow multiple passes
            logging.info(f"Number of rows read from CSV: {len(rows)}")
    except Exception as e:
        logging.error(f"Error reading CSV file: {e}")
        return

    for row in rows:
        tenant_id = row.get("tenantId")
        email = row.get("email")
        role_id = row.get("id")
        name = row.get("name", "")

        # Skip the row if required fields are missing
        if not tenant_id or not email or not role_id:
            logging.warning(f"Skipping row with missing required fields: {row}")
            continue

        if tenant_id not in grouped_data:
            grouped_data[tenant_id] = {}
        if email not in grouped_data[tenant_id]:
            grouped_data[tenant_id][email] = {
                "name": name,
                "roleIds": set(),
            }
        grouped_data[tenant_id][email]["roleIds"].add(role_id)

    logging.info(f"Grouped data: {grouped_data}")

    # For each tenant, send a single POST request with all its users
    for tenant_id, users_dict in grouped_data.items():
        users_payload = []
        for email, user_info in users_dict.items():
            users_payload.append({
                "email": email,
                "name": user_info["name"],
                "skipInviteEmail": True,  # Adjust based on your needs
                "roleIds": list(user_info["roleIds"]),
                "verified": True          # Adjust based on your needs
            })

        # Prepare headers with the bearer token and the tenant ID
        headers = {
            "Authorization": f"Bearer {BEARER_TOKEN}",
            "Content-Type": "application/json",
            "frontegg-tenant-id": tenant_id,
        }

        payload = {"users": users_payload}

        logging.info(f"Inviting users for tenant {tenant_id}")
        logging.info(f"Payload for tenant {tenant_id}: {payload}")

        response = requests.post(API_URL, headers=headers, json=payload)
        if response.status_code == 200:
            logging.info(f"Successfully invited users for tenant {tenant_id}")
        elif response.status_code == 202:
            job_id = response.json().get("id", "unknown")
            logging.info(f"202 successful bulk invite request! job ID {job_id}")
        else:
            logging.error(f"Error inviting users for tenant {tenant_id}: {response.status_code} - {response.text}")

    logging.info("Bulk invite process completed")

if __name__ == "__main__":
    main()
