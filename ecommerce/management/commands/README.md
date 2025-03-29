# Restobar Database Population Command

This Django management command populates the database with sample data for the 5th Avenue Grill and Restobar application.

## Usage

To populate the database with default values:

```bash
python manage.py populate_restobar
```

### Optional Parameters

You can customize the amount of data generated:

```bash
python manage.py populate_restobar --users=20 --orders=50 --reservations=30 --reviews=100
```

- `--users`: Number of sample users to create (default: 10)
- `--orders`: Number of sample orders to create (default: 30)
- `--reservations`: Number of sample reservations to create (default: 20)
- `--reviews`: Number of sample reviews to create (default: 50)

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

## Notes

- Images are not included in the sample data. You'll need to add them manually or extend the command to handle image uploads.
- The command uses transactions to ensure data integrity.
- The Faker library is used to generate realistic names, emails, and other data.
