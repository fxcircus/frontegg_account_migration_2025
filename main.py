import os
from utility.frontegg_client import FronteggClient
from migration_scripts.tenants import migrate_tenants
from migration_scripts.permissions_and_categories import migrate_settings
from migration_scripts.roles import migrate_roles
from migration_scripts.users import migrate_users
from utility.logger import get_logger, log_section, log_success, log_error
from dotenv import load_dotenv
from migration_scripts.bulk_invite_users import main as bulk_invite_main
from migration_scripts.groups import migrate_groups
from migration_scripts.applications import migrate_applications
from migration_scripts.security_rules import migrate_security_rules
from migration_scripts.email_templates import migrate_email_configuration
from migration_scripts.webhooks import migrate_webhook_configuration
from migration_scripts.allowed_origins import migrate_allowed_origins_configuration
from migration_scripts.jwt_settings import migrate_jwt_settings

# Load environment variables
load_dotenv()

# Migration Steps Control - Read from environment variables
MIGRATE_TENANTS = os.getenv("MIGRATE_TENANTS", "False").lower() == "true"
MIGRATE_CATEGORIES = os.getenv("MIGRATE_CATEGORIES", "False").lower() == "true"
MIGRATE_PERMISSIONS = os.getenv("MIGRATE_PERMISSIONS", "False").lower() == "true"
MIGRATE_ROLES = os.getenv("MIGRATE_ROLES", "False").lower() == "true"
MIGRATE_USERS = os.getenv("MIGRATE_USERS", "False").lower() == "true"
MIGRATE_USER_ROLES = os.getenv("MIGRATE_USER_ROLES", "False").lower() == "true"
BULK_INVITE_USERS_TO_TENANTS = os.getenv("BULK_INVITE_USERS_TO_TENANTS", "False").lower() == "true"
ASSIGN_ROLES_TO_USERS_ON_ALL_TENANTS = os.getenv("ASSIGN_ROLES_TO_USERS_ON_ALL_TENANTS", "False").lower() == "true"
MIGRATE_GROUPS = os.getenv("MIGRATE_GROUPS", "False").lower() == "true"
MIGRATE_APPLICATIONS = os.getenv("MIGRATE_APPLICATIONS", "False").lower() == "true"
MIGRATE_SECURITY_RULES = os.getenv("MIGRATE_SECURITY_RULES", "False").lower() == "true"
MIGRATE_EMAIL_TEMPLATES = os.getenv("MIGRATE_EMAIL_TEMPLATES", "False").lower() == "true"
MIGRATE_EMAIL_SENDER = os.getenv("MIGRATE_EMAIL_SENDER", "False").lower() == "true"
MIGRATE_PREHOOKS = os.getenv("MIGRATE_PREHOOKS", "False").lower() == "true"
MIGRATE_ALLOWED_ORIGINS = os.getenv("MIGRATE_ALLOWED_ORIGINS", "False").lower() == "true"
MIGRATE_JWT_SETTINGS = os.getenv("MIGRATE_JWT_SETTINTS", "False").lower() == "true"

def main():
    logger = get_logger()
    logger.section("Migration Process Starting")
    
    # Initialize Frontegg clients with authentication
    logger.subsection("Initializing Frontegg Clients")
    frontegg_client_1 = FronteggClient(os.getenv("BASE_URL_1"), os.getenv("CLIENT_ID_1"), os.getenv("API_KEY_1"))
    frontegg_client_2 = FronteggClient(os.getenv("BASE_URL_2"), os.getenv("CLIENT_ID_2"), os.getenv("API_KEY_2"))

    # Run migrations based on flags
    if frontegg_client_1.token and frontegg_client_2.token:
        migration_tasks = []
        if MIGRATE_TENANTS:
            migration_tasks.append("Tenants")
        if MIGRATE_CATEGORIES:
            migration_tasks.append("Categories")
        if MIGRATE_PERMISSIONS:
            migration_tasks.append("Permissions")
        if MIGRATE_ROLES:
            migration_tasks.append("Roles")
        if MIGRATE_USERS:
            migration_tasks.append("Users")
        if MIGRATE_USER_ROLES:
            migration_tasks.append("User Roles")
        if BULK_INVITE_USERS_TO_TENANTS:
            migration_tasks.append("Bulk Invites")
        if ASSIGN_ROLES_TO_USERS_ON_ALL_TENANTS:
            migration_tasks.append("Role Assignments")
        if MIGRATE_GROUPS:
            migration_tasks.append("Groups")
        if MIGRATE_APPLICATIONS:
            migration_tasks.append("Applications")
        if MIGRATE_SECURITY_RULES:
            migration_tasks.append("Security Rules")
        if MIGRATE_EMAIL_TEMPLATES:
            migration_tasks.append("Email Templates")
        if MIGRATE_EMAIL_SENDER:
            migration_tasks.append("Email Sender")
        if MIGRATE_PREHOOKS:
            migration_tasks.append("Prehooks")
        if MIGRATE_ALLOWED_ORIGINS:
            migration_tasks.append("Allowed Origins")
        if MIGRATE_JWT_SETTINGS:
            migration_tasks.append("JWT Settings")
        
        logger.print_summary(migration_tasks, "Scheduled Migration Tasks")
        
        if MIGRATE_TENANTS:
            log_section("Tenant Migration")
            migrate_tenants(frontegg_client_1, frontegg_client_2)
        
        if MIGRATE_CATEGORIES or MIGRATE_PERMISSIONS:
            log_section("Settings Migration (Categories & Permissions)")
            migrate_settings(frontegg_client_1, frontegg_client_2, MIGRATE_CATEGORIES, MIGRATE_PERMISSIONS)

        if MIGRATE_ROLES:
            log_section("Roles Migration")
            migrate_roles(frontegg_client_1, frontegg_client_2)

        if MIGRATE_USERS or MIGRATE_USER_ROLES:
            log_section("Users Migration")
            migrate_users(frontegg_client_1, frontegg_client_2, MIGRATE_USERS, MIGRATE_USER_ROLES)

        if BULK_INVITE_USERS_TO_TENANTS:
            log_section("Bulk Invite Process")
            bulk_invite_main()

        if ASSIGN_ROLES_TO_USERS_ON_ALL_TENANTS:
            log_section("Role Assignment Process")
            from migration_scripts.assign_roles_to_users import assign_roles_to_users
            assign_roles_to_users(frontegg_client_1,frontegg_client_2)

        if MIGRATE_GROUPS:
            log_section("Groups Migration")
            from migration_scripts.groups import migrate_groups
            migrate_groups(frontegg_client_1, frontegg_client_2)
        
        if MIGRATE_APPLICATIONS:
            log_section("Applications Migration")
            migrate_applications(frontegg_client_1, frontegg_client_2)
        
        if MIGRATE_SECURITY_RULES:
            log_section("Security Rules Migration")
            migrate_security_rules(frontegg_client_1, frontegg_client_2)
        
        if MIGRATE_EMAIL_TEMPLATES or MIGRATE_EMAIL_SENDER:
            log_section("Email Configuration Migration")
            migrate_email_configuration(frontegg_client_1, frontegg_client_2)
        
        if MIGRATE_PREHOOKS:
            log_section("Prehooks Migration")
            migrate_webhook_configuration(frontegg_client_1, frontegg_client_2)
        
        if MIGRATE_ALLOWED_ORIGINS:
            log_section("Allowed Origins Migration")
            migrate_allowed_origins_configuration(frontegg_client_1, frontegg_client_2)
        
        if MIGRATE_JWT_SETTINGS:
            migrate_jwt_settings(frontegg_client_1, frontegg_client_2)
        
        log_success("🎉 Migration process completed successfully!")
        
    else:
        log_error("✗ Authentication failed; migration aborted.")

if __name__ == "__main__":
    main()
