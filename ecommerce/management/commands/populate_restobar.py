import random
import datetime
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from django.utils import timezone
from django.db import transaction, connection
from django.conf import settings
from decimal import Decimal
from faker import Faker
from ecommerce.models import (
    Category, MenuItem, Reservation, Order, OrderItem, Review, Cart, CartItem
)

fake = Faker()

# Restaurant-specific data
RESTAURANT_CATEGORIES = [
    {
        'name': 'Appetizers',
        'description': 'Start your meal with our delicious appetizers.',
        'items': [
            {
                'name': 'Calamari Fritti',
                'description': 'Crispy fried calamari served with marinara sauce and lemon wedges.',
                'price': '12.99',
                'is_vegetarian': False,
                'spice_level': 0
            },
            {
                'name': 'Bruschetta',
                'description': 'Toasted bread topped with fresh tomatoes, basil, garlic, and olive oil.',
                'price': '9.99',
                'is_vegetarian': True,
                'spice_level': 0
            },
            {
                'name': 'Buffalo Wings',
                'description': 'Crispy chicken wings tossed in spicy buffalo sauce, served with blue cheese dip.',
                'price': '14.99',
                'is_vegetarian': False,
                'spice_level': 3
            },
            {
                'name': 'Spinach Artichoke Dip',
                'description': 'Creamy spinach and artichoke dip served with tortilla chips.',
                'price': '11.99',
                'is_vegetarian': True,
                'spice_level': 0
            },
            {
                'name': 'Shrimp Cocktail',
                'description': 'Chilled jumbo shrimp served with cocktail sauce and lemon.',
                'price': '16.99',
                'is_vegetarian': False,
                'spice_level': 1
            }
        ]
    },
    {
        'name': 'Salads',
        'description': 'Fresh and healthy salad options.',
        'items': [
            {
                'name': 'Caesar Salad',
                'description': 'Crisp romaine lettuce, parmesan cheese, croutons, and Caesar dressing.',
                'price': '10.99',
                'is_vegetarian': True,
                'spice_level': 0
            },
            {
                'name': 'Greek Salad',
                'description': 'Mixed greens, tomatoes, cucumbers, red onions, olives, and feta cheese with Greek dressing.',
                'price': '12.99',
                'is_vegetarian': True,
                'spice_level': 0
            },
            {
                'name': 'Cobb Salad',
                'description': 'Mixed greens topped with grilled chicken, bacon, avocado, blue cheese, tomatoes, and hard-boiled egg.',
                'price': '15.99',
                'is_vegetarian': False,
                'spice_level': 0
            }
        ]
    },
    {
        'name': 'Main Courses',
        'description': 'Delicious entrees prepared by our expert chefs.',
        'items': [
            {
                'name': 'Filet Mignon',
                'description': '8oz filet mignon cooked to perfection, served with mashed potatoes and seasonal vegetables.',
                'price': '34.99',
                'is_vegetarian': False,
                'is_featured': True,
                'spice_level': 0
            },
            {
                'name': 'Grilled Salmon',
                'description': 'Fresh Atlantic salmon grilled with lemon and herbs, served with rice pilaf and asparagus.',
                'price': '26.99',
                'is_vegetarian': False,
                'spice_level': 0
            },
            {
                'name': 'Chicken Parmesan',
                'description': 'Breaded chicken breast topped with marinara sauce and melted mozzarella, served with spaghetti.',
                'price': '22.99',
                'is_vegetarian': False,
                'spice_level': 1
            },
            {
                'name': 'Vegetable Stir Fry',
                'description': 'Fresh vegetables stir-fried in a savory sauce, served over steamed rice.',
                'price': '18.99',
                'is_vegetarian': True,
                'spice_level': 2
            },
            {
                'name': 'Beef Tenderloin',
                'description': 'Slow-roasted beef tenderloin with red wine reduction, served with roasted potatoes and vegetables.',
                'price': '32.99',
                'is_vegetarian': False,
                'is_featured': True,
                'spice_level': 0
            }
        ]
    },
    {
        'name': 'Pasta',
        'description': 'Authentic Italian pasta dishes.',
        'items': [
            {
                'name': 'Spaghetti Bolognese',
                'description': 'Spaghetti with rich meat sauce, topped with parmesan cheese.',
                'price': '18.99',
                'is_vegetarian': False,
                'spice_level': 1
            },
            {
                'name': 'Fettuccine Alfredo',
                'description': 'Fettuccine pasta in a creamy parmesan sauce.',
                'price': '17.99',
                'is_vegetarian': True,
                'spice_level': 0
            },
            {
                'name': 'Shrimp Scampi',
                'description': 'Linguine pasta with garlic butter shrimp, white wine, and lemon.',
                'price': '24.99',
                'is_vegetarian': False,
                'is_featured': True,
                'spice_level': 1
            },
            {
                'name': 'Penne Arrabbiata',
                'description': 'Penne pasta in a spicy tomato sauce with garlic and red chili flakes.',
                'price': '16.99',
                'is_vegetarian': True,
                'spice_level': 4
            }
        ]
    },
    {
        'name': 'Pizza',
        'description': 'Wood-fired artisan pizzas.',
        'items': [
            {
                'name': 'Margherita Pizza',
                'description': 'Classic pizza with tomato sauce, fresh mozzarella, and basil.',
                'price': '15.99',
                'is_vegetarian': True,
                'spice_level': 0
            },
            {
                'name': 'Pepperoni Pizza',
                'description': 'Traditional pizza with tomato sauce, mozzarella, and pepperoni.',
                'price': '17.99',
                'is_vegetarian': False,
                'spice_level': 1
            },
            {
                'name': 'Supreme Pizza',
                'description': 'Loaded pizza with pepperoni, sausage, bell peppers, onions, olives, and mushrooms.',
                'price': '19.99',
                'is_vegetarian': False,
                'is_featured': True,
                'spice_level': 2
            },
            {
                'name': 'BBQ Chicken Pizza',
                'description': 'BBQ sauce, grilled chicken, red onions, and cilantro.',
                'price': '18.99',
                'is_vegetarian': False,
                'spice_level': 2
            }
        ]
    },
    {
        'name': 'Desserts',
        'description': 'Sweet treats to end your meal.',
        'items': [
            {
                'name': 'Tiramisu',
                'description': 'Classic Italian dessert with layers of coffee-soaked ladyfingers and mascarpone cream.',
                'price': '9.99',
                'is_vegetarian': True,
                'is_featured': True,
                'spice_level': 0
            },
            {
                'name': 'Chocolate Lava Cake',
                'description': 'Warm chocolate cake with a molten center, served with vanilla ice cream.',
                'price': '10.99',
                'is_vegetarian': True,
                'spice_level': 0
            },
            {
                'name': 'New York Cheesecake',
                'description': 'Creamy cheesecake with a graham cracker crust, topped with berry compote.',
                'price': '8.99',
                'is_vegetarian': True,
                'spice_level': 0
            },
            {
                'name': 'Crème Brûlée',
                'description': 'Rich custard topped with a layer of caramelized sugar.',
                'price': '9.99',
                'is_vegetarian': True,
                'spice_level': 0
            }
        ]
    },
    {
        'name': 'Beverages',
        'description': 'Refreshing drinks and cocktails.',
        'items': [
            {
                'name': 'Classic Mojito',
                'description': 'Refreshing cocktail with rum, mint, lime, sugar, and soda water.',
                'price': '12.99',
                'is_vegetarian': True,
                'spice_level': 0
            },
            {
                'name': 'Margarita',
                'description': 'Tequila, triple sec, and lime juice, served with a salt rim.',
                'price': '13.99',
                'is_vegetarian': True,
                'spice_level': 0
            },
            {
                'name': 'Red Wine Sangria',
                'description': 'Red wine mixed with fresh fruits and a splash of brandy.',
                'price': '11.99',
                'is_vegetarian': True,
                'spice_level': 0
            },
            {
                'name': 'Craft Beer',
                'description': 'Selection of local craft beers.',
                'price': '7.99',
                'is_vegetarian': True,
                'spice_level': 0
            },
            {
                'name': 'Fresh Lemonade',
                'description': 'Homemade lemonade with fresh lemons and a hint of mint.',
                'price': '4.99',
                'is_vegetarian': True,
                'spice_level': 0
            }
        ]
    }
]

# Sample review comments
REVIEW_COMMENTS = [
    "Absolutely delicious! Will definitely order again.",
    "Great flavor and presentation. Highly recommend!",
    "Perfectly cooked and seasoned. One of my favorites.",
    "Good portion size and excellent taste.",
    "Decent dish but a bit overpriced for what you get.",
    "Amazing! The flavors were perfectly balanced.",
    "Not bad, but I've had better elsewhere.",
    "Exceeded my expectations. A must-try!",
    "Authentic taste and great quality ingredients.",
    "Delicious but the portion was a bit small.",
    "Outstanding dish! The chef really knows what they're doing.",
    "Solid choice, though nothing extraordinary.",
    "Fantastic! Will be coming back just for this dish.",
    "Good flavor but arrived a bit cold.",
    "Incredible value for the quality and portion size."
]

class Command(BaseCommand):
    help = 'Populates the database with sample data for a restobar'

    def add_arguments(self, parser):
        parser.add_argument(
            '--users',
            type=int,
            default=10,
            help='Number of users to create'
        )
        parser.add_argument(
            '--orders',
            type=int,
            default=30,
            help='Number of orders to create'
        )
        parser.add_argument(
            '--reservations',
            type=int,
            default=20,
            help='Number of reservations to create'
        )
        parser.add_argument(
            '--reviews',
            type=int,
            default=50,
            help='Number of reviews to create'
        )

    def handle(self, *args, **options):
        num_users = options['users']
        num_orders = options['orders']
        num_reservations = options['reservations']
        num_reviews = options['reviews']

        self.stdout.write(self.style.SUCCESS('Starting to populate the database...'))

        # Create admin user if it doesn't exist
        if not User.objects.filter(username='admin').exists():
            User.objects.create_superuser('admin', 'admin@example.com', 'admin123')
            self.stdout.write(self.style.SUCCESS('Admin user created'))

        # Create regular users
        self.create_users(num_users)

        # Create categories and menu items
        self.create_menu()

        # Create reservations
        self.create_reservations(num_reservations)

        # Create orders
        self.create_orders(num_orders)

        # Create reviews
        self.create_reviews(num_reviews)

        # Create carts for some users
        self.create_carts()

        self.stdout.write(self.style.SUCCESS('Database successfully populated!'))

    @transaction.atomic
    def create_users(self, num_users):
        self.stdout.write('Creating users...')

        # Create users
        users = []
        for i in range(num_users):
            first_name = fake.first_name()
            last_name = fake.last_name()
            username = f"{first_name.lower()}{last_name.lower()}{random.randint(1, 999)}"
            email = f"{username}@example.com"

            user = User(
                username=username,
                email=email,
                first_name=first_name,
                last_name=last_name,
                is_active=True,
                date_joined=fake.date_time_between(start_date='-1y', end_date='now', tzinfo=timezone.get_current_timezone())
            )
            user.set_password('password123')
            users.append(user)

        User.objects.bulk_create(users)
        self.stdout.write(self.style.SUCCESS(f'Created {num_users} users'))

    @transaction.atomic
    def create_menu(self):
        self.stdout.write('Creating menu categories and items...')

        for category_data in RESTAURANT_CATEGORIES:
            category = Category.objects.create(
                name=category_data['name'],
                description=category_data['description'],
                is_active=True
            )

            menu_items = []
            for item_data in category_data['items']:
                menu_item = MenuItem(
                    category=category,
                    name=item_data['name'],
                    description=item_data['description'],
                    price=Decimal(item_data['price']),
                    is_available=True,
                    is_featured=item_data.get('is_featured', False),
                    is_vegetarian=item_data.get('is_vegetarian', False),
                    spice_level=item_data.get('spice_level', 0)
                )
                menu_items.append(menu_item)

            MenuItem.objects.bulk_create(menu_items)

        self.stdout.write(self.style.SUCCESS(f'Created {Category.objects.count()} categories and {MenuItem.objects.count()} menu items'))

    def create_reservations(self, num_reservations):
        self.stdout.write('Creating reservations...')

        created_count = 0
        for _ in range(num_reservations):
            try:
                # Generate a date between today and 30 days in the future
                future_date = fake.date_between(start_date='today', end_date='+30d')

                # Generate a time between 11:00 AM and 10:00 PM
                hour = random.randint(11, 22)
                minute = random.choice([0, 15, 30, 45])
                reservation_time = datetime.time(hour, minute)

                # Create the reservation directly
                Reservation.objects.create(
                    name=fake.name(),
                    email=fake.email(),
                    phone=fake.phone_number(),
                    date=future_date,
                    time=reservation_time,
                    party_size=random.randint(1, 10),
                    special_requests=fake.text(max_nb_chars=100) if random.random() > 0.7 else '',
                    status=random.choice(['PENDING', 'CONFIRMED', 'CANCELLED']),
                    created_at=timezone.now(),
                    updated_at=timezone.now()
                )
                created_count += 1
            except Exception as e:
                self.stdout.write(self.style.WARNING(f'Error creating reservation: {e}'))

                # Try with direct SQL as a fallback
                try:
                    with connection.cursor() as cursor:
                        cursor.execute("""
                        INSERT INTO ecommerce_reservation
                        (name, email, phone, date, time, party_size, special_requests, status, created_at, updated_at)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                        """, [
                            fake.name(),
                            fake.email(),
                            fake.phone_number(),
                            future_date,
                            reservation_time,
                            random.randint(1, 10),
                            fake.text(max_nb_chars=100) if random.random() > 0.7 else '',
                            random.choice(['PENDING', 'CONFIRMED', 'CANCELLED']),
                            timezone.now(),
                            timezone.now()
                        ])
                    created_count += 1
                except Exception as inner_e:
                    self.stdout.write(self.style.ERROR(f'SQL insertion also failed: {inner_e}'))

        self.stdout.write(self.style.SUCCESS(f'Created {created_count} reservations'))

    def create_orders(self, num_orders):
        self.stdout.write('Creating orders...')

        users = list(User.objects.all())
        menu_items = list(MenuItem.objects.all())

        created_count = 0
        for _ in range(num_orders):
            try:
                with transaction.atomic():
                    # Select a random user
                    user = random.choice(users)

                    # Create order
                    order_date = fake.date_time_between(start_date='-60d', end_date='now', tzinfo=timezone.get_current_timezone())
                    status = random.choice(['PENDING', 'PREPARING', 'READY', 'COMPLETED', 'CANCELLED'])

                    # Select 1-5 random menu items for this order
                    order_items_count = random.randint(1, 5)
                    selected_items = random.sample(menu_items, order_items_count)

                    # Calculate total amount
                    total_amount = Decimal('0.00')
                    order_items = []

                    for item in selected_items:
                        quantity = random.randint(1, 3)
                        price = item.price
                        subtotal = price * quantity
                        total_amount += subtotal

                        order_items.append({
                            'menu_item': item,
                            'quantity': quantity,
                            'price': price,
                            'special_instructions': fake.text(max_nb_chars=50) if random.random() > 0.8 else ''
                        })

                    # Create the order
                    order = Order.objects.create(
                        user=user,
                        status=status,
                        total_amount=total_amount,
                        special_instructions=fake.text(max_nb_chars=100) if random.random() > 0.7 else '',
                        created_at=order_date,
                        updated_at=order_date + datetime.timedelta(minutes=random.randint(10, 60))
                    )

                    # Create order items
                    for item_data in order_items:
                        OrderItem.objects.create(
                            order=order,
                            menu_item=item_data['menu_item'],
                            quantity=item_data['quantity'],
                            price=item_data['price'],
                            special_instructions=item_data['special_instructions']
                        )

                    created_count += 1
            except Exception as e:
                self.stdout.write(self.style.WARNING(f'Error creating order: {e}'))

        self.stdout.write(self.style.SUCCESS(f'Created {created_count} orders with items'))

    def create_reviews(self, num_reviews):
        self.stdout.write('Creating reviews...')

        users = list(User.objects.all())
        menu_items = list(MenuItem.objects.all())

        created_count = 0
        attempts = 0
        max_attempts = num_reviews * 2  # Allow for some duplicates

        while created_count < num_reviews and attempts < max_attempts:
            attempts += 1
            try:
                with transaction.atomic():
                    user = random.choice(users)
                    menu_item = random.choice(menu_items)

                    # Skip if this user already reviewed this item
                    if Review.objects.filter(user=user, menu_item=menu_item).exists():
                        continue

                    rating = random.randint(3, 5)  # Biased towards positive reviews
                    if random.random() < 0.2:  # 20% chance of a lower rating
                        rating = random.randint(1, 2)

                    comment = random.choice(REVIEW_COMMENTS)

                    review_date = fake.date_time_between(start_date='-90d', end_date='now', tzinfo=timezone.get_current_timezone())

                    Review.objects.create(
                        user=user,
                        menu_item=menu_item,
                        rating=rating,
                        comment=comment,
                        created_at=review_date,
                        updated_at=review_date
                    )
                    created_count += 1
            except Exception as e:
                self.stdout.write(self.style.WARNING(f'Error creating review: {e}'))

        self.stdout.write(self.style.SUCCESS(f'Created {created_count} reviews'))

    def create_carts(self):
        self.stdout.write('Creating shopping carts...')

        users = list(User.objects.all())
        menu_items = list(MenuItem.objects.all())

        created_count = 0
        # Create carts for 30% of users
        for user in random.sample(users, int(len(users) * 0.3)):
            try:
                with transaction.atomic():
                    # Skip if user already has a cart
                    if Cart.objects.filter(user=user).exists():
                        continue

                    cart = Cart.objects.create(user=user)

                    # Add 1-4 items to cart
                    cart_items_count = random.randint(1, 4)
                    selected_items = random.sample(menu_items, min(cart_items_count, len(menu_items)))

                    for item in selected_items:
                        quantity = random.randint(1, 2)
                        CartItem.objects.create(
                            cart=cart,
                            menu_item=item,
                            quantity=quantity,
                            special_instructions=fake.text(max_nb_chars=30) if random.random() > 0.8 else ''
                        )
                    created_count += 1
            except Exception as e:
                self.stdout.write(self.style.WARNING(f'Error creating cart: {e}'))

        self.stdout.write(self.style.SUCCESS(f'Created {created_count} carts with items'))
