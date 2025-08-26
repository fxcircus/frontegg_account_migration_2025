import json
import requests
import os
from dotenv import load_dotenv

# Constants - Source account
load_dotenv()
BASE_URL = os.getenv("BASE_URL_2")
CLIENT_ID = os.getenv("CLIENT_ID_2")
API_KEY = os.getenv("API_KEY_2")

# Deletion Flags - Read from environment variables
DELETE_TENANTS = os.getenv("DELETE_TENANTS", "False").lower() == "true"
DELETE_USERS = os.getenv("DELETE_USERS", "False").lower() == "true"
DELETE_PERMISSIONS = os.getenv("DELETE_PERMISSIONS", "False").lower() == "true"
DELETE_ROLES = os.getenv("DELETE_ROLES", "False").lower() == "true"
DELETE_APPLICATIONS = os.getenv("DELETE_APPLICATIONS", "False").lower() == "true"
DELETE_PREHOOKS = os.getenv("DELETE_PREHOOKS", "False").lower() == "true"

def get_vendor_token():
    """Fetches the vendor token using CLIENT_ID and API_KEY."""
    url = f"{BASE_URL}/auth/vendor/"
    headers = {
        'accept': 'application/json',
        'content-type': 'application/json'
    }
    data = {
        "clientId": CLIENT_ID,
        "secret": API_KEY
    }
    response = requests.post(url, headers=headers, json=data)
    response.raise_for_status()
    return response.json().get("token")

def get_all_users(token):
    """Fetches all users using the vendor token."""
    url = f"{BASE_URL}/identity/resources/users/v2"
    headers = {
        'Authorization': f'Bearer {token}',
        'Content-Type': 'application/json'
    }
    params = {
        '_limit': 200,
        '_includeSubTenants': True,
        '_include': 'tenants',
    }
    users = []
    next_url = url
    while next_url:
        response = requests.get(next_url, headers=headers, params=params)
        response.raise_for_status()
        data = response.json()
        users.extend(data.get("items", []))
        next_url = data.get("_links", {}).get("next")
        params = None  # Only pass params on the first request
    print(f"Retrieved {len(users)} users.")
    return users

def delete_user(token, user_id):
    """Deletes a user by ID using the vendor token."""
    url = f"{BASE_URL}/identity/resources/users/v1/{user_id}"
    headers = {'Authorization': f'Bearer {token}'}
    try:
        response = requests.delete(url, headers=headers)
        response.raise_for_status()
        print(f"Deleted user with ID: {user_id}")
    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 404:
            print(f"User with ID {user_id} not found (404), skipping...")
        else:
            print(f"Failed to delete user with ID {user_id}: {e}")

def get_tenant_ids(token):
    """Fetches tenant IDs using the vendor token."""
    url = f"{BASE_URL}/tenants/resources/tenants/v2"
    headers = {'Authorization': f'Bearer {token}'}
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    return [tenant["tenantId"] for tenant in response.json().get("items", [])]

def delete_tenant(token, tenant_id):
    """Deletes a tenant by ID."""
    url = f"{BASE_URL}/tenants/resources/tenants/v1/{tenant_id}"
    headers = {'Authorization': f'Bearer {token}'}
    response = requests.delete(url, headers=headers)
    response.raise_for_status()
    print(f"Deleted tenant with ID: {tenant_id}")

def get_permissions(token):
    """Fetches all permissions using the vendor token."""
    url = f"{BASE_URL}/identity/resources/permissions/v1"
    headers = {'Authorization': f'Bearer {token}'}
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    return [permission["id"] for permission in response.json()]

def delete_permission(token, permission_id):
    """Deletes a permission by ID using the vendor token."""
    url = f"{BASE_URL}/identity/resources/permissions/v1/{permission_id}"
    headers = {'Authorization': f'Bearer {token}'}
    try:
        response = requests.delete(url, headers=headers)
        response.raise_for_status()
        print(f"Deleted permission with ID: {permission_id}")
    except requests.exceptions.HTTPError as e:
        if response.status_code == 404:
            print(f"Permission with ID {permission_id} not found (404), skipping...")
        else:
            raise  # Re-raise other HTTP errors

def get_roles(token):
    """Fetches all roles using the vendor token."""
    url = f"{BASE_URL}/identity/resources/roles/v2?_limit=2000"
    headers = {'Authorization': f'Bearer {token}'}
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    return [role["id"] for role in response.json().get("items", [])]

def delete_role(token, role_id):
    """Deletes a role by ID using the vendor token."""
    url = f"{BASE_URL}/identity/resources/roles/v1/{role_id}"
    headers = {'Authorization': f'Bearer {token}'}
    try:
        response = requests.delete(url, headers=headers)
        response.raise_for_status()
        print(f"Deleted role with ID: {role_id}")
    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 404:
            print(f"Role with ID {role_id} not found (404), skipping...")
        else:
            print(f"Failed to delete role with ID {role_id}: {e}")

def get_applications(token):
    """Fetches all applications using the vendor token."""
    url = f"{BASE_URL}/applications/resources/applications/v1?_excludeAgents=true"
    headers = {'Authorization': f'Bearer {token}'}
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    applications = response.json()
    print(f"Retrieved {len(applications)} applications.")
    return applications

def create_dummy_application(token):
    """Creates a temporary dummy application to allow deletion of all other apps."""
    url = f"{BASE_URL}/applications/resources/applications/v1"
    headers = {
        'Authorization': f'Bearer {token}',
        'Content-Type': 'application/json'
    }
    data = {
        "name": "Temporary Dummy App",
        "appURL": "https://dummy.example.com",
        "loginURL": "https://dummy.example.com/login",
        "accessType": "FREE_ACCESS",
        "isActive": True,
        "type": "web",
        "frontendStack": "react",
        "description": "Temporary app for deletion process"
    }
    try:
        response = requests.post(url, headers=headers, json=data)
        response.raise_for_status()
        app_data = response.json()
        print(f"✓ Created dummy application: {app_data.get('name')} (ID: {app_data.get('id')})")
        return app_data
    except requests.exceptions.HTTPError as e:
        print(f"✗ Failed to create dummy application: {e}")
        return None

def delete_application(token, app_id, app_name=None):
    """Deletes an application by ID using the vendor token."""
    url = f"{BASE_URL}/applications/resources/applications/v1/{app_id}"
    headers = {'Authorization': f'Bearer {token}'}
    display_name = app_name if app_name else app_id
    try:
        response = requests.delete(url, headers=headers)
        response.raise_for_status()
        print(f"✓ Deleted application: {display_name} (ID: {app_id})")
        return True
    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 404:
            print(f"⚠ Application {display_name} not found (404), skipping...")
        elif e.response.status_code == 400:
            print(f"⚠ Cannot delete {display_name} - likely the default application (400)")
        else:
            print(f"✗ Failed to delete application {display_name}: {e}")
        return False

def get_prehooks(token):
    """Fetches all prehook configurations using the vendor token."""
    url = f"{BASE_URL}/prehooks/resources/configurations/v1"
    headers = {
        'Authorization': f'Bearer {token}',
        'frontegg-environment-id': CLIENT_ID
    }
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        prehooks = response.json()
        print(f"Retrieved {len(prehooks)} prehook(s).")
        return prehooks
    except requests.exceptions.HTTPError as e:
        print(f"Failed to get prehooks: {e}")
        return []

def delete_prehook(token, prehook_id, prehook_name=None):
    """Deletes a prehook by ID using the vendor token."""
    url = f"{BASE_URL}/prehooks/resources/configurations/v1/{prehook_id}"
    headers = {
        'Authorization': f'Bearer {token}',
        'frontegg-environment-id': CLIENT_ID
    }
    display_name = prehook_name if prehook_name else prehook_id
    try:
        response = requests.delete(url, headers=headers)
        response.raise_for_status()
        print(f"✓ Deleted prehook: {display_name} (ID: {prehook_id})")
        return True
    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 404:
            print(f"⚠ Prehook {display_name} not found (404), skipping...")
        else:
            print(f"✗ Failed to delete prehook {display_name}: {e}")
        return False

def main():
    token = get_vendor_token()

    # Execute deletion processes based on flags
    if DELETE_APPLICATIONS:
        print("\n=== Deleting Applications ===")
        
        # Step 1: Create a dummy application first
        print("Step 1: Creating dummy application to enable full deletion...")
        dummy_app = create_dummy_application(token)
        
        if not dummy_app:
            print("⚠ Warning: Could not create dummy app, some applications may not be deletable")
        
        # Step 2: Get all applications (including the dummy we just created)
        print("\nStep 2: Fetching all applications...")
        applications = get_applications(token)
        
        if not applications:
            print("No applications found to delete.")
        else:
            # Separate dummy app from others
            dummy_app_id = dummy_app['id'] if dummy_app else None
            apps_to_delete = []
            
            for app in applications:
                app_name = app.get('name', 'Unknown')
                is_default = app.get('isDefault', False)
                
                # We'll delete the dummy app last
                if app['id'] == dummy_app_id:
                    print(f"ℹ Will delete dummy app '{app_name}' last")
                else:
                    apps_to_delete.append(app)
                    if is_default:
                        print(f"ℹ Found default application: {app_name}")
            
            # Step 3: Delete all non-dummy applications
            print(f"\nStep 3: Deleting {len(apps_to_delete)} original applications...")
            deleted_count = 0
            failed_count = 0
            
            for app in apps_to_delete:
                if delete_application(token, app['id'], app.get('name')):
                    deleted_count += 1
                else:
                    failed_count += 1
            
            # Step 4: Try to delete the dummy app (this might fail if it's now the default)
            if dummy_app:
                print("\nStep 4: Attempting to delete dummy application...")
                if delete_application(token, dummy_app['id'], dummy_app.get('name')):
                    deleted_count += 1
                    print("✓ Successfully cleaned up dummy application")
                else:
                    print("ℹ Dummy app remains (now default) - you may want to delete it manually")
            
            print(f"\n📊 Summary: Deleted {deleted_count}/{len(applications)} applications")
            if failed_count > 0:
                print(f"   ({failed_count} could not be deleted)")
    
    if DELETE_TENANTS:
        print("\n=== Deleting Tenants ===")
        tenant_ids = get_tenant_ids(token)
        for tenant_id in tenant_ids:
            delete_tenant(token, tenant_id)

    if DELETE_USERS:
        print("\n=== Deleting Users ===")
        users = get_all_users(token)
        for user in users:
            delete_user(token, user["id"])

    if DELETE_PERMISSIONS:
        print("\n=== Deleting Permissions ===")
        permissions = get_permissions(token)
        for permission_id in permissions:
            delete_permission(token, permission_id)

    if DELETE_ROLES:
        print("\n=== Deleting Roles ===")
        roles = get_roles(token)
        for role_id in roles:
            delete_role(token, role_id)
    
    if DELETE_PREHOOKS:
        print("\n=== Deleting Prehooks ===")
        prehooks = get_prehooks(token)
        if not prehooks:
            print("No prehooks found to delete.")
        else:
            deleted_count = 0
            for prehook in prehooks:
                prehook_name = prehook.get('displayName', 'Unknown')
                prehook_id = prehook.get('id')
                if delete_prehook(token, prehook_id, prehook_name):
                    deleted_count += 1
            print(f"\n📊 Summary: Deleted {deleted_count}/{len(prehooks)} prehooks")

if __name__ == "__main__":
    main()
