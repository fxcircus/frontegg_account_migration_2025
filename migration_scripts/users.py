import json
import os
import pandas as pd
import requests
from utility.utils import log
from migration_scripts.roles import get_roles 

def log_detailed_api_call(method, url, headers=None, data=None):
    """Log all details of the API call."""
    log(f"API CALL: {method} {url}")
    if headers:
        log(f"Headers: {json.dumps(headers, indent=2)}")
    if data:
        log(f"Data Payload: {json.dumps(data, indent=2)}")

def create_final_csv():
    """Generate final_data.csv from user_migration_data.csv with required transformations."""
    input_path = os.path.join(os.getcwd(), 'account_data', 'user_migration_data.csv')
    output_path = os.path.join(os.getcwd(), 'account_data', 'final_data.csv')

    if not os.path.exists(input_path):
        log(f"Input CSV file not found at {input_path}. Please check the file path.")
        return

    df = pd.read_csv(input_path, dtype={'phoneNumber': str})  # Ensure phoneNumber is read as a string
    df.columns = [col.strip('"') for col in df.columns]

    def format_metadata(metadata):
        try:
            metadata_json = json.loads(metadata)
            return json.dumps(metadata_json)
        except (json.JSONDecodeError, TypeError):
            return metadata

    if 'metadata' in df.columns:
        df['metadata'] = df['metadata'].fillna("{}").apply(format_metadata)

    return df  # Return DataFrame without formatting phone numbers

def finalize_csv(df):
    """Finalizes the CSV by formatting phone numbers and saving the file."""
    output_path = os.path.join(os.getcwd(), 'account_data', 'final_data.csv')

    def format_phone_number(phone):
        """Format phone numbers by ensuring they are treated as strings and prefixed with '+'."""
        if pd.isna(phone):
            return ""
        phone_str = str(phone).split('.')[0]  # Remove any decimals introduced by reading as float
        return f"+{phone_str}" if not phone_str.startswith("+") else phone_str

    if 'phoneNumber' in df.columns:
        df['phoneNumber'] = df['phoneNumber'].apply(format_phone_number)

    df.to_csv(output_path, index=False)
    log(f"Generated transformed CSV file at {output_path}")
    return output_path

def create_users_in_destination(source_client, destination_client, migrate_user_roles):
    """Create users in the destination account with role assignment based on mapped roles."""
    df = create_final_csv()  # Read initial transformations without formatting phone numbers

    if migrate_user_roles:
        # Get a merged list of roles instead of a tuple.
        source_roles = get_roles(source_client, split=False)  
        dest_roles = get_roles(destination_client, split=False)

        # Map destination role IDs based on matching role names
        role_name_to_dest_id = {dest_role['name']: dest_role['id'] for dest_role in dest_roles}
        role_id_mapping = {src_role['id']: role_name_to_dest_id.get(src_role['name'])
                           for src_role in source_roles if src_role['name'] in role_name_to_dest_id}

        log(f"Role ID Mapping: {role_id_mapping}")

        roles_for_csv = []

        for idx, row in df.iterrows():
            email = row["email"]
            tenant_id = row["tenantId"]
            
            # Fetch user ID from the source client
            user_id = get_user_id_by_email(source_client, email, tenant_id)

            if user_id:
                source_role_ids = get_user_roles(source_client, user_id, tenant_id)
                translated_role_ids = [role_id_mapping.get(role_id) for role_id in source_role_ids if role_id_mapping.get(role_id)]
                
                log(f"User {email} - Translated Role IDs: {translated_role_ids}")

                roles_string = "|".join(translated_role_ids) if translated_role_ids else ""
                roles_for_csv.append(roles_string)
            else:
                log(f"User ID not found for {email} in source client.")
                roles_for_csv.append("")

        # Add the new 'roleIds' column to the DataFrame
        df["roleIds"] = roles_for_csv

    # Finalize the CSV with formatted phone numbers
    csv_file_path = finalize_csv(df)
    initiate_csv_migration(destination_client, csv_file_path)

def initiate_csv_migration(client, csv_file_path):
    """Initiates CSV migration API request to Frontegg with role mapping."""
    endpoint = f"{client.base_url}/identity/resources/migrations/v1/local/bulk/csv"
    headers = {
        'accept': 'application/json, text/plain, */*',
        'accept-language': 'en-US,en;q=0.9',
        'authorization': f'Bearer {client.token}',
        'frontegg-environment-id': client.client_id
    }

    fields_mapper = json.dumps({
        "name": "name",
        "email": "email",
        "tenantId": "tenantId",
        "password": "passwordHash",
        "metadata": "metadata",
        "phoneNumber": "phoneNumber",
        "roleIds": "roleIds"
    })

    hashing_config = json.dumps({
        "passwordHashType": "bcrypt"
    })

    try:
        with open(csv_file_path, 'rb') as csv_file:
            files = {
                'csv': csv_file,
                'fieldsMapper': (None, fields_mapper, 'application/json'),
                'hashingConfig': (None, hashing_config, 'application/json')
            }
            log_detailed_api_call("POST", endpoint, headers=headers, data={
                'fieldsMapper': fields_mapper,
                'hashingConfig': hashing_config
            })
            response = requests.post(endpoint, headers=headers, files=files)
            log(f"Users created: {response.status_code}")
            log(f"Response Content:\n{response.text}\n")
            response.raise_for_status()
    except requests.exceptions.HTTPError as e:
        log(f"Error creating users: {e}")
        if e.response is not None:
            log(f"Error response content:\n{e.response.text}")
        raise
    except Exception as e:
        log(f"Error creating users: {e}")
        raise

    log("User creation in destination account via CSV bulk migration completed")

def migrate_users(source_client, destination_client, migrate_users_flag, migrate_user_roles):
    """Migrate users and assign roles if specified."""
    log("Starting user migration")

    if migrate_users_flag or migrate_user_roles:
        create_users_in_destination(source_client, destination_client, migrate_user_roles)
        log("Users and roles have been set up in final_data.csv")

def get_user_id_by_email(client, email, tenant_id):
    """Fetch user ID by email and tenantId, with detailed API call and response logging for troubleshooting."""
    endpoint = f"{client.base_url}/identity/resources/users/v3?_email={email}"
    headers = {'Authorization': f'Bearer {client.token}', 'frontegg-tenant-id': tenant_id}

    # Log the API call details
    log(f"Fetching user ID for {email} with tenant ID {tenant_id}")
    log(f"API Endpoint: {endpoint}")
    log(f"Headers: {json.dumps(headers, indent=2)}")

    try:
        response = requests.get(endpoint, headers=headers)
        response.raise_for_status()

        # Log the raw response for debugging
        log(f"Response Status Code: {response.status_code}")
        log(f"Response Content: {response.text}")

        # Parse the JSON response correctly
        users = response.json().get("items", [])
        return users[0].get('id') if users else None
    except requests.exceptions.HTTPError as e:
        log(f"HTTP error when fetching user ID for {email}: {e}")
        return None
    except Exception as e:
        log(f"Error fetching user ID for {email}: {e}")
        return None

def get_user_roles(client, user_id, tenant_id):
    """Fetch role IDs for a user within a tenant."""
    endpoint = f"{client.base_url}/identity/resources/users/v3/roles?ids={user_id}"
    headers = {'Authorization': f'Bearer {client.token}', 'frontegg-tenant-id': tenant_id}

    try:
        response = requests.get(endpoint, headers=headers)
        response.raise_for_status()
        roles_info = response.json()
        return roles_info[0].get("roleIds", []) if roles_info else []
    except requests.exceptions.HTTPError as e:
        log(f"HTTP error when fetching roles for user ID {user_id}: {e}")
        return []
    except Exception as e:
        log(f"Error fetching roles for user ID {user_id}: {e}")
        return []
