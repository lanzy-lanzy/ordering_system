# 5th Avenue Grill and Restobar - System Credentials

This document contains all the credentials for the different user accounts created by the `populate_base.py` command. These accounts are used for testing and development purposes.

## Staff User Accounts

### Administrator
- **Username:** admin
- **Password:** admin123
- **Email:** admin@example.com
- **Role:** ADMIN
- **Phone:** 09123456789
- **Permissions:** Full access to all system features, including user management, sales reports, inventory management, and system configuration.

### Manager
- **Username:** manager
- **Password:** manager123
- **Email:** manager@example.com
- **Role:** MANAGER
- **Phone:** 09123456788
- **Permissions:** Access to manage staff, view sales reports, manage inventory, process orders, and manage menu items.

### Cashier
- **Username:** cashier
- **Password:** cashier123
- **Email:** cashier@example.com
- **Role:** CASHIER
- **Phone:** 09123456787
- **Permissions:** Process orders, manage basic inventory, and handle customer transactions.

## How to Use These Accounts

1. **Login to Admin Dashboard:**
   - Navigate to `/admin/`
   - Use the admin credentials to access the Django admin interface

2. **Login to Staff Portal:**
   - Navigate to `/accounts/login/`
   - Use any of the staff credentials based on the role you want to test

3. **Testing Different Permissions:**
   - Use different accounts to test role-specific features
   - Admin can access all features
   - Manager has limited administrative capabilities
   - Cashier can only process orders and perform basic operations

## Security Notice

These are default credentials created for development and testing purposes. In a production environment:

1. **Change Default Passwords:**
   - All default passwords should be changed immediately
   - Use strong, unique passwords for each account

2. **Limit Admin Access:**
   - Restrict admin account usage to necessary administrative tasks
   - Create individual accounts for each staff member with appropriate permissions

3. **Regular Audits:**
   - Regularly review user accounts and permissions
   - Remove or disable unused accounts

## How to Create Additional Accounts

To create additional staff accounts, you can:

1. **Use the Admin Interface:**
   - Login as admin
   - Navigate to Users section
   - Create a new user and assign appropriate staff profile

2. **Use the Staff Management Interface:**
   - Login as admin or manager
   - Navigate to Staff Management
   - Add a new staff member with appropriate role

3. **Use Django Management Command:**
   ```bash
   python manage.py createsuperuser
   ```
   This will create a new superuser (admin) account.

## How to Reset Credentials

If you need to reset these credentials to their default values, run:

```bash
python manage.py populate_base --staff
```

This will ensure the default staff accounts exist with their default credentials.
