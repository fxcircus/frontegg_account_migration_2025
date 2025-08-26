# CLAUDE CODE INSTRUCTIONS - CRITICAL RULES

## 🚨 CRITICAL: .env FILE MANAGEMENT
**NEVER** touch, modify, or delete the `.env` file located at:
`/Users/roy/Desktop/dev/python_scripts/migration_from_eu_to_us/NEW/.env`

### Rules:
1. **NEVER** create any other `.env` files anywhere in the project
2. **NEVER** modify the existing `.env` file without explicit user permission
3. **ALWAYS** use the `.env` file at `/Users/roy/Desktop/dev/python_scripts/migration_from_eu_to_us/NEW/.env`
4. All environment variables should be loaded from this single `.env` file
5. Use `load_dotenv()` without any path parameters to automatically load from the correct location

## Project Structure
- Main project directory: `/Users/roy/Desktop/dev/python_scripts/migration_from_eu_to_us/NEW/`
- All scripts should run from within the NEW directory
- Environment variables are managed centrally in the `.env` file

## 📁 File Organization Rules
**NEVER** create files in the root directory. All files must be organized in appropriate folders:
- `migration_scripts/` - Migration logic and scripts
- `utility/` - Utility functions and helpers
- `adding_new_stuff/` - Documentation and specifications for new features
- Create new folders as needed for organization
- Test scripts should go in a `tests/` folder if needed
- Temporary scripts should be avoided; if necessary, put in a `temp/` folder

## Migration Control Flags
The following flags in `.env` control which migrations run:
- MIGRATE_TENANTS
- MIGRATE_CATEGORIES
- MIGRATE_PERMISSIONS
- MIGRATE_ROLES
- MIGRATE_USERS
- MIGRATE_USER_ROLES
- BULK_INVITE_USERS_TO_TENANTS
- ASSIGN_ROLES_TO_USERS_ON_ALL_TENANTS
- MIGRATE_GROUPS
- MIGRATE_APPLICATIONS
- MIGRATE_SECURITY_RULES
- MIGRATE_EMAIL_TEMPLATES
- MIGRATE_EMAIL_SENDER
- MIGRATE_JWT_SETTINTS

## Deletion Control Flags
The following flags in `.env` control what gets deleted (used by delete_account_data.py):
- DELETE_TENANTS
- DELETE_USERS
- DELETE_PERMISSIONS
- DELETE_ROLES
- DELETE_APPLICATIONS

## Important Notes
- This is a Frontegg account migration tool
- Uses enhanced logging with color output and progress bars
- All migrations are controlled via boolean flags in the `.env` file
- JWT Settings migration flag has a typo in the env variable name (MIGRATE_JWT_SETTINTS) for backward compatibility