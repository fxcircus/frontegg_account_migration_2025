import json
import time
from datetime import datetime
from utility.logger import get_logger, log_success, log_error, log_warning, log_subsection

# Rate limit configuration
DEFAULT_RATE_LIMIT = 30
last_request_times = {}

def get_headers(client):
    """Generate headers with the client token."""
    return {
        "Authorization": f"Bearer {client.token}",
        "Content-Type": "application/json"
    }

def enforce_rate_limit(endpoint, rate_limit=DEFAULT_RATE_LIMIT):
    """Enforce the rate limit for a specific endpoint."""
    interval = 60 / rate_limit
    
    if endpoint in last_request_times:
        time_since_last_request = time.time() - last_request_times[endpoint]
        if time_since_last_request < interval:
            time.sleep(interval - time_since_last_request)
    
    last_request_times[endpoint] = time.time()

def make_request_with_rate_limiting(method, url, client, headers=None, json_data=None):
    """Handle rate-limited requests."""
    enforce_rate_limit(url)
    try:
        response = client.session.request(method, url, headers=headers, json=json_data)
        if response.status_code == 429:
            log_warning("⚠ Rate limit exceeded. Retrying after delay...")
            time.sleep(60)
            response = client.session.request(method, url, headers=headers, json=json_data)
        response.raise_for_status()
        return response
    except Exception as e:
        log_error(f"Request failed: {e}")
        raise

def get_applications(client):
    """Fetch all applications from the client."""
    logger = get_logger()
    logger.debug("Fetching applications")
    
    endpoint = f"{client.base_url}/applications/resources/applications/v1?_excludeAgents=true"
    headers = get_headers(client)
    
    try:
        response = make_request_with_rate_limiting('GET', endpoint, client, headers=headers)
        applications = response.json()
        log_success(f"Retrieved {len(applications)} applications")
        return applications
    except Exception as e:
        log_error(f"Error fetching applications: {e}")
        return []

def create_application(client, app_data):
    """Create an application in the destination."""
    logger = get_logger()
    app_name = app_data.get('name', 'Unknown')
    logger.debug(f"Creating application: {app_name}")
    
    endpoint = f"{client.base_url}/applications/resources/applications/v1"
    headers = get_headers(client)
    
    # Prepare the request body - remove fields that shouldn't be sent in creation
    req_body = {
        'name': app_data['name'],
        'appURL': app_data.get('appURL', ''),
        'loginURL': app_data.get('loginURL', ''),
        'accessType': app_data.get('accessType', 'FREE_ACCESS'),
        'isActive': app_data.get('isActive', True),
        'type': app_data.get('type', 'WEB'),
        'frontendStack': app_data.get('frontendStack', 'REACT'),
        'isDefault': app_data.get('isDefault', False)  # IMPORTANT: Preserve default flag
    }
    
    # Add optional fields if they exist
    if app_data.get('logoURL'):
        req_body['logoURL'] = app_data['logoURL']
    if app_data.get('description'):
        req_body['description'] = app_data['description']
    if app_data.get('metadata'):
        req_body['metadata'] = app_data['metadata']
    
    # Log if this is a default app
    if app_data.get('isDefault', False):
        logger.info(f"📌 Setting {app_name} as DEFAULT application")
    
    try:
        response = make_request_with_rate_limiting('POST', endpoint, client, headers=headers, json_data=req_body)
        created_app = response.json()
        log_success(f"✓ Created application: {app_name} (ID: {created_app.get('id', 'N/A')})")
        return created_app
    except Exception as e:
        log_error(f"✗ Failed to create application '{app_name}': {e}")
        return None

def delete_application(client, app_id, app_name=None):
    """Delete an application."""
    logger = get_logger()
    display_name = app_name if app_name else app_id
    logger.debug(f"Deleting application: {display_name}")
    
    endpoint = f"{client.base_url}/applications/resources/applications/v1/{app_id}"
    headers = get_headers(client)
    
    try:
        response = make_request_with_rate_limiting('DELETE', endpoint, client, headers=headers)
        log_success(f"✓ Deleted application: {display_name}")
        return True
    except Exception as e:
        log_error(f"✗ Failed to delete application '{display_name}': {e}")
        return False

def update_application(client, app_id, app_data):
    """Update an existing application."""
    logger = get_logger()
    app_name = app_data.get('name', 'Unknown')
    logger.debug(f"Updating application: {app_name}")
    
    endpoint = f"{client.base_url}/applications/resources/applications/v1/{app_id}"
    headers = get_headers(client)
    
    # Prepare update body - only include fields that can be updated
    update_body = {
        'name': app_data['name'],
        'appURL': app_data.get('appURL', ''),
        'loginURL': app_data.get('loginURL', ''),
        'accessType': app_data.get('accessType', 'FREE_ACCESS'),
        'isActive': app_data.get('isActive', True),
        'type': app_data.get('type', 'WEB'),
        'frontendStack': app_data.get('frontendStack', 'REACT')
    }
    
    if app_data.get('logoURL'):
        update_body['logoURL'] = app_data['logoURL']
    if app_data.get('description'):
        update_body['description'] = app_data['description']
    if app_data.get('metadata'):
        update_body['metadata'] = app_data['metadata']
    
    try:
        response = make_request_with_rate_limiting('PUT', endpoint, client, headers=headers, json_data=update_body)
        log_success(f"✓ Updated application: {app_name}")
        return response.json()
    except Exception as e:
        log_error(f"✗ Failed to update application '{app_name}': {e}")
        return None

def migrate_applications(source_client, destination_client):
    """Migrate all applications from source to destination."""
    logger = get_logger()
    logger.info("🚀 Starting applications migration process")
    
    # Fetch applications from source
    source_applications = get_applications(source_client)
    if not source_applications:
        log_warning("No applications found to migrate")
        return
    
    # Separate default and non-default applications
    source_default_app = None
    non_default_apps = []
    
    for app in source_applications:
        if app.get('isDefault', False):
            source_default_app = app
            logger.info(f"Found source default application: {app.get('name', 'Unknown')}")
        else:
            non_default_apps.append(app)
    
    # Fetch existing applications from destination
    log_subsection("Analyzing Destination Applications")
    dest_applications = get_applications(destination_client)
    dest_default_app = None
    
    for app in dest_applications:
        if app.get('isDefault', False):
            dest_default_app = app
            logger.info(f"Found destination default application: {app.get('name', 'Unknown')} (ID: {app.get('id')})")
            break
    
    # Display migration plan
    logger.print_summary([
        f"Source applications: {len(source_applications)} ({len(non_default_apps)} non-default, {'1 default' if source_default_app else 'no default'})",
        f"Destination applications to remove: {len(dest_applications)}",
        f"Step 1: Migrate {len(non_default_apps)} non-default apps from source",
        f"Step 2: Delete ALL {len(dest_applications)} destination apps",
        f"Step 3: Migrate source default app"
    ], "Migration Plan")
    
    created_count = 0
    failed_count = 0
    
    # Step 1: Migrate all non-default applications
    if non_default_apps:
        log_subsection("Step 1: Migrating Non-Default Applications")
        progress, task = logger.start_progress(len(non_default_apps), "Creating non-default applications")
        
        for app in non_default_apps:
            app_name = app.get('name', 'Unknown')
            logger.update_progress(1, f"Creating: {app_name}")
            
            result = create_application(destination_client, app)
            if result:
                created_count += 1
            else:
                failed_count += 1
        
        logger.stop_progress()
        
        logger.print_stats("Non-Default Applications Migration", {
            "Total": len(non_default_apps),
            "Successfully Created": created_count,
            "Failed": failed_count
        })
    
    # Step 2: Delete ALL destination applications (including any leftovers)
    if dest_applications and source_default_app:
        log_subsection("Step 2: Removing ALL Destination Applications")
        
        for app in dest_applications:
            app_name = app.get('name', 'Unknown')
            logger.info(f"Deleting destination app: {app_name}")
            delete_success = delete_application(
                destination_client, 
                app['id'], 
                app_name
            )
            
            if not delete_success:
                log_warning(f"Failed to delete {app_name}. Continuing anyway...")
    
    # Step 3: Migrate source default application
    if source_default_app:
        log_subsection("Step 3: Migrating Source Default Application")
        logger.info(f"Creating default application: {source_default_app.get('name', 'Unknown')}")
        
        result = create_application(destination_client, source_default_app)
        if result:
            created_count += 1
            log_success(f"✅ Successfully migrated default application: {source_default_app.get('name')}")
        else:
            failed_count += 1
            log_error(f"❌ Failed to migrate default application: {source_default_app.get('name')}")
    
    # Final summary
    logger.print_stats("Applications Migration Summary", {
        "Total Source Applications": len(source_applications),
        "Applications Created": created_count,
        "Applications Failed": failed_count,
        "Default App Replaced": "Yes" if source_default_app else "No"
    })
    
    log_success("✅ Applications migration completed successfully!")