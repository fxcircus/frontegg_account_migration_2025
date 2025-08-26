import json
import requests
from utility.utils import log
from migration_scripts.tenants import make_request_with_rate_limiting, get_headers

def log_detailed_api_call(method, url, headers=None, data=None):
    """Log all details of the API call."""
    log(f"API CALL: {method} {url}")
    if headers:
        log(f"Headers: {json.dumps(headers, indent=2)}")
    if data:
        log(f"Data Payload: {json.dumps(data, indent=2)}")

def get_categories(client):
    log("Getting categories from account.")
    endpoint = client.base_url + '/identity/resources/permissions/v1/categories'
    headers = get_headers(client)
    try:
        response = make_request_with_rate_limiting('GET', endpoint, client, headers=headers)
        categories = response.json()
        
        # Structure the categories as expected
        formatted_categories = [
            {
                "id": cat["id"],
                "name": cat["name"],
                "description": cat.get("description", ""),
                "createdAt": cat.get("createdAt", ""),
                "feCategory": cat.get("feCategory", False),
            }
            for cat in categories
        ]
        
        log(f"Retrieved {len(formatted_categories)} categories.")
        return formatted_categories
    except Exception as e:
        log(f"Error fetching categories: {e}")
        return []

def create_categories(client, categories):
    log("Creating categories in destination account.")
    endpoint = client.base_url + '/identity/resources/permissions/v1/categories'
    headers = get_headers(client)
    category_mapping = {}

    for category in categories:
        category_json = {
            'name': category['name'],
            'description': category.get('description', ''),
        }
        try:
            response = make_request_with_rate_limiting('POST', endpoint, client, headers=headers, json_data=category_json)
            response_data = response.json()
            destination_category_id = response_data["id"]
            category_mapping[category["id"]] = destination_category_id
            log(f"Category '{category['name']}' created with ID: {destination_category_id}")
        except requests.exceptions.HTTPError as e:
            if e.response is not None:
                error_content = e.response.json()
                if any("already exist" in error.lower() for error in error_content.get('errors', [])):
                    log(f"Category '{category['name']}' already exists. Skipping.")
                else:
                    raise
            else:
                raise
    log("Categories creation completed.")
    return category_mapping

def get_permissions(client):
    log("Getting permissions from source account.")
    endpoint = client.base_url + '/identity/resources/permissions/v1'
    headers = get_headers(client)
    try:
        response = make_request_with_rate_limiting('GET', endpoint, client, headers=headers)
        permissions = response.json()
        log(f"Retrieved {len(permissions)} permissions.")
        return permissions
    except Exception as e:
        log(f"Error fetching permissions: {e}")
        return []

def create_permissions(client, permissions, batch_size=100):
    log("Creating permissions in destination account.")
    endpoint = client.base_url + '/identity/resources/permissions/v1'
    headers = get_headers(client)
    
    # Prepare permissions data in batches
    for i in range(0, len(permissions), batch_size):
        permissions_batch = permissions[i:i + batch_size]
        permissions_data = [
            {
                'key': permission['key'],
                'name': permission['name'],
                'description': permission.get('description', ''),
                'categoryId': permission['categoryId'],
            }
            for permission in permissions_batch if permission.get('key') and permission.get('categoryId')
        ]

        if not permissions_data:
            log("No valid permissions to create in this batch. Skipping.")
            continue

        log(f"Creating batch of {len(permissions_data)} permissions.")
        
        # Log the API call details for each batch
        log_detailed_api_call("POST", endpoint, headers=headers, data=permissions_data)
        
        try:
            response = make_request_with_rate_limiting('POST', endpoint, client, headers=headers, json_data=permissions_data)
            log(f"Batch creation of permissions completed with status code: {response.status_code}")
        except requests.exceptions.HTTPError as e:
            if e.response is not None:
                error_content = e.response.json()
                log(f"Error creating permissions batch. Response content:\n{json.dumps(error_content, indent=2)}")
            else:
                raise

    log("Permissions creation completed.")
    
def migrate_settings(source_client, destination_client, migrate_categories, migrate_permissions):
    """Orchestrate the migration of categories and permissions."""
    log("Starting settings migration.")
    
    # Step 1: Fetch categories from source and destination
    source_categories = get_categories(source_client)
    log(f"Retrieved {len(source_categories)} categories from source.")
    
    destination_categories = get_categories(destination_client)
    log(f"Retrieved {len(destination_categories)} categories from destination.")
    
    # Step 2: Map source categories to destination categories based on name and description
    category_mapping = {}
    for src_cat in source_categories:
        matching_dest_cat = next(
            (dest_cat for dest_cat in destination_categories
             if dest_cat['name'] == src_cat['name'] and dest_cat.get('description', '') == src_cat.get('description', '')),
            None
        )
        if matching_dest_cat:
            category_mapping[src_cat['id']] = matching_dest_cat['id']

    log(f"Category mapping completed with {len(category_mapping)} mapped categories.")

    # Step 3: Create categories if enabled and not already existing in the destination
    if migrate_categories:
        categories_to_create = [cat for cat in source_categories if cat['id'] not in category_mapping]
        if categories_to_create:
            new_category_mapping = create_categories(destination_client, categories_to_create)
            category_mapping.update(new_category_mapping)
        log(f"{len(categories_to_create)} categories created in the destination account.")

    # Step 4: Migrate Permissions if enabled
    if migrate_permissions:
        source_permissions = get_permissions(source_client)
        log(f"Source permissions retrieved for migration: {len(source_permissions)} permissions.")
        
        # Step 5: Assign the correct categoryId from destination to each permission
        permissions_to_migrate = []
        for permission in source_permissions:
            dest_category_id = category_mapping.get(permission['categoryId'])
            if dest_category_id:
                permission['categoryId'] = dest_category_id
                permissions_to_migrate.append(permission)
            else:
                log(f"Destination category mapping for permission '{permission['name']}' with source category ID '{permission['categoryId']}' not found. Skipping.")

        # Step 6: Create permissions with mapped category IDs
        if permissions_to_migrate:
            log(f"{len(permissions_to_migrate)} permissions matched with categories for migration.")
            create_permissions(destination_client, permissions_to_migrate)
        else:
            log("No permissions with valid categories to migrate from the source.")
    else:
        log("Skipping permissions migration as per configuration.")

    log("Settings migration completed.")
