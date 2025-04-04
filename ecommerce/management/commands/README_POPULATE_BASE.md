# Base Data Population Command

This Django management command populates the database with base data for the 5th Avenue Grill and Restobar application. It creates essential data like menu categories, menu items (food and drinks), and staff users.

## Usage

To populate the database with all base data:

```bash
python manage.py populate_base
```

Or with UV:

```bash
uv run django populate_base
```

### Optional Parameters

You can customize what data to populate:

```bash
# Create only staff users (admin, manager, cashier)
python manage.py populate_base --staff

# Create only food categories and menu items
python manage.py populate_base --food

# Create only drink categories and menu items (including wine, beer)
python manage.py populate_base --drinks

# Create all base data (equivalent to no parameters)
python manage.py populate_base --all
```

## Generated Data

The command creates the following data:

### Staff Users
- Admin user (username: admin, password: admin123)
- Manager user (username: manager, password: manager123)
- Cashier user (username: cashier, password: cashier123)

### Food Categories
- Appetizers
- Salads
- Main Courses
- Pizza
- Pasta
- Desserts

### Drink Categories
- Wine (various types)
- Beer (various types)
- Cocktails
- Non-Alcoholic Beverages
- Coffee & Tea

Each menu item includes:
- Name and description
- Price and cost price
- Initial inventory stock
- Attributes like vegetarian status and spice level

## Differences from populate_restobar

The `populate_base` command focuses on creating essential base data for the restaurant, while the `populate_restobar` command creates more comprehensive sample data including users, orders, reservations, and reviews.

Use `populate_base` when you need a clean database with just the essential menu items and staff users, and use `populate_restobar` when you need a fully populated database with sample transactions for testing and demonstration purposes.
