# Populating the Database for 5th Avenue Grill and Restobar

This guide explains how to populate your database with sample data for the 5th Avenue Grill and Restobar application.

## Using UV (Recommended)

The simplest way to run the command is using UV:

```bash
uv run django populate_restobar
```

You can customize the amount of data generated:

```bash
uv run django populate_restobar --users=20 --orders=50 --reservations=30 --reviews=100
```

## Using Django's manage.py

Alternatively, you can use Django's manage.py:

```bash
python manage.py populate_restobar
```

With custom parameters:

```bash
python manage.py populate_restobar --users=20 --orders=50 --reservations=30 --reviews=100
```

## Generated Data

The command creates the following data:

1. **Admin User**:
   - Username: `admin`
   - Password: `admin123`
   - Email: `admin@example.com`

2. **Regular Users**:
   - Random users with usernames based on their names
   - All users have the password: `password123`

3. **Menu Categories and Items**:
   - Appetizers
   - Salads
   - Main Courses
   - Pasta
   - Pizza
   - Desserts
   - Beverages

4. **Reservations**:
   - Random reservations for future dates
   - Various party sizes and statuses

5. **Orders**:
   - Orders with random menu items
   - Various statuses (Pending, Preparing, Ready, Completed, Cancelled)

6. **Reviews**:
   - Reviews for menu items with ratings and comments

7. **Shopping Carts**:
   - Active carts for approximately 30% of users

## Troubleshooting

If you encounter any issues:

1. Make sure Faker is installed:
   ```bash
   uv pip install faker
   ```

2. Try running with fewer items:
   ```bash
   uv run django populate_restobar --orders=10 --reservations=10
   ```

3. Check for validation errors in your models:
   - The command tries to handle validation errors gracefully
   - It will fall back to direct SQL insertion if needed

4. If you see warnings about some items not being created, this is normal:
   - The command will report how many items were successfully created
   - It will continue even if some items fail to be created
