import csv
import requests
import os
import re
from collections import defaultdict
from dotenv import load_dotenv

load_dotenv()

def call_api(method, url, params, headers):
    print(f"Calling API: {method} {url} with headers: {headers} and params: {params}")
    response = requests.request(method, url, params=params, headers=headers)
    print(f"API responded with status code: {response.status_code}")
    return response.json()

def get_users_with_pagination(client):
    url = f"{client.base_url}/identity/resources/users/v3?includeSubTenants=true&_limit=200"
    headers = {"authorization": f"Bearer {client.token}"}
    print(f"Fetching users from: {url}")
    res = call_api("GET", url, {}, headers)
    next_page = res.get("_links", {}).get("next", "")
    items_arr = res.get("items", [])
    while next_page:
        offset_match = re.search(r'_offset=(\d+)', next_page)
        if offset_match:
            offset_value = offset_match.group(1)
            url = f"{client.base_url}/identity/resources/users/v3?includeSubTenants=true&_limit=200&_offset={offset_value}"
            print(f"Fetching next page of users from: {url}")
            next_page_res = call_api("GET", url, {}, headers)
            items_arr.extend(next_page_res.get("items", []))
            next_page = next_page_res.get("_links", {}).get("next", "")
        else:
            break
    print("Response from /users/v3 endpoint:", res)
    print("Retrieved users and their IDs:")
    for user in items_arr:
        print(f"Email: {user.get('email')}, User ID: {user.get('id')}")
    return {"count": len(items_arr), "items": items_arr}

def create_role_mapping(destination_mapping_file):
    """
    Builds a mapping between role names and destination role IDs.
    The destination mapping CSV is expected to have the fields:
         "roleId" and "name"
    For example, a row like:
         c3911b41-6a83-4c76-bc35-485fd94d45d0,Editor
    will map the role name "Editor" to the destination roleId.
    """
    role_mapping = {}
    print(f"Building role mapping from destination file: {destination_mapping_file}")
    with open(destination_mapping_file, mode='r') as dest_file:
        csv_reader = csv.DictReader(dest_file)
        print("Destination mapping CSV headers:", csv_reader.fieldnames)
        for row in csv_reader:
            role_name = row.get("name", "").strip()
            role_id = row.get("roleId", "").strip()
            print(f"Mapping row: role name '{role_name}' -> destination role '{role_id}'")
            if role_name and role_id:
                role_mapping[role_name] = role_id
    print("Final role mapping:", role_mapping)
    return role_mapping

def assign_roles_to_users(source, destination):
    """
    Assigns roles to destination users based on CSV data.
    - source: client for the source account (available for future use)
    - destination: client for the destination account (to retrieve users and post roles)
    
    The assign_roles_to_users.csv file is expected to have the following fields:
         "email","userId","roleId","name","tenantId"
    Here, the "name" field represents the role name (e.g. Editor).

    The roles_in_destination.csv file is expected to have the following fields:
         "roleId","name"
    The mapping is built by matching the role name.
    """
    source_file = 'account_data/assign_roles_to_users.csv'
    roles_mapping_file = 'account_data/roles_in_destination.csv'
    print("Starting role assignment process...")

    # Build mapping from role name to destination role ID.
    role_mapping = create_role_mapping(roles_mapping_file)
    
    # Retrieve destination users and build an email-to-userID mapping.
    dest_users_response = get_users_with_pagination(destination)
    dest_users = dest_users_response.get("items", [])
    email_to_userid = {
        user.get('email').strip(): user.get('id')
        for user in dest_users if user.get('email') and user.get('id')
    }
    print("Email to user ID mapping:", email_to_userid)
    
    # Group CSV rows by (email, tenantId) for efficient processing.
    groups = defaultdict(list)
    with open(source_file, mode='r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            email = row.get('email', '').strip()
            tenant_id = row.get('tenantId', '').strip()
            groups[(email, tenant_id)].append(row)
    print("Grouped CSV rows by (email, tenantId):")
    for key, rows in groups.items():
        print(f"{key}: {len(rows)} rows")
    
    # Process each group: aggregate destination role IDs and post them.
    for (email, tenant_id), rows in groups.items():
        dest_user_id = email_to_userid.get(email)
        if not dest_user_id:
            print(f"Destination user not found for email: {email}")
            continue
        
        role_ids = []
        for row in rows:
            # Use the role name from the source CSV.
            role_name = row.get('name', '').strip()
            dst_role = role_mapping.get(role_name)
            print(f"Processing row for email '{email}': role name '{role_name}' maps to destination role '{dst_role}'")
            if dst_role:
                role_ids.append(dst_role)
        
        if role_ids:
            print(f"Assigning roles {role_ids} to destination user {dest_user_id} for tenant '{tenant_id}'")
            post_roles_to_user(destination, dest_user_id, tenant_id, role_ids)
        else:
            print(f"No valid roles to assign for destination user {dest_user_id} (email: {email})")

def post_roles_to_user(client, user_id, tenant_id, role_ids):
    url = f"{client.base_url}/identity/resources/users/v1/{user_id}/roles"
    headers = {
        'Authorization': f"Bearer {client.token}",
        'Content-Type': 'application/json',
        'frontegg-tenant-id': tenant_id
    }
    data = {"roleIds": role_ids}
    print(f"Posting roles to user {user_id} in tenant '{tenant_id}': {role_ids}")
    response = requests.post(url, headers=headers, json=data)
    print(f"Post response status code: {response.status_code}")
    if response.status_code == 200:
        print(f"Successfully assigned roles to user {user_id} in tenant {tenant_id}.")
    else:
        print(f"Failed to assign roles to user {user_id} in tenant {tenant_id}. Response: {response.text}")
