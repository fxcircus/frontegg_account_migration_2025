import csv
import requests
from utility.utils import log

# Function to read groups from CSV and create them in the destination account
def fetch_users_from_destination(client, tenant_id):
    """Fetch users from the destination account for a given tenant."""
    url = f"{client.base_url}/identity/resources/users/v3?_limit=200"
    headers = {
        'Authorization': f'Bearer {client.token}',
        'Content-Type': 'application/json',
        'frontegg-tenant-id': tenant_id
    }
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    users = response.json().get('items', [])
    return {user['email']: user['id'] for user in users}

def migrate_groups(frontegg_client_1, frontegg_client_2):
    # Read the CSV file
    with open('account_data/groups.csv', newline='') as csvfile:
        group_reader = csv.DictReader(csvfile)
        for row in group_reader:
            tenant_id = row['tenantId']
            name = row['name']
            description = row['description']

            # Skip groups where both userIds and userEmails are null
            if not row['userIds'] and not row['userEmails']:
                log(f"Skipping group '{name}' as both userIds and userEmails are null.")
                continue

            # Prepare the API request to create the group
            url = f"{frontegg_client_2.base_url}/identity/resources/groups/v1"
            headers = {
                'Authorization': f'Bearer {frontegg_client_2.token}',
                'Content-Type': 'application/json',
                'frontegg-tenant-id': tenant_id
            }
            data = {
                'name': name,
                'description': description
            }

            # Make the API request to create the group
            response = requests.post(url, headers=headers, json=data)

            if response.status_code == 201:
                group_id = response.json().get('id')
                log(f"Successfully created group '{name}' with ID: {group_id}")

                # Fetch users from the destination account
                email_to_user_id = fetch_users_from_destination(frontegg_client_2, tenant_id)

                # Map emails to user IDs
                user_emails = row['userEmails'].split(',') if row['userEmails'] else []
                user_ids = [email_to_user_id[email] for email in user_emails if email in email_to_user_id]

                # Assign users to the group
                if user_ids:
                    assign_users_to_group(frontegg_client_2, tenant_id, group_id, user_ids)
                else:
                    log(f"No valid user IDs found for group '{name}'.")
            else:
                log(f"Failed to create group '{name}'. Status Code: {response.status_code}, Response: {response.text}")

def assign_users_to_group(client, tenant_id, group_id, user_ids):
    """Assign users to a group in the destination account."""
    url = f"{client.base_url}/identity/resources/groups/v1/{group_id}/users"
    headers = {
        'Authorization': f'Bearer {client.token}',
        'Content-Type': 'application/json',
        'frontegg-tenant-id': tenant_id
    }
    data = {'userIds': user_ids}
    response = requests.post(url, headers=headers, json=data)
    if response.status_code == 201:
        log(f"Successfully assigned users to group ID: {group_id}")
    else:
        log(f"Failed to assign users to group ID: {group_id}. Status Code: {response.status_code}, Response: {response.text}")
