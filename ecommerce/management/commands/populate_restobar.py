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
    Category, MenuItem, Reservation, Order, OrderItem, Review, Cart, CartItem,
    InventoryTransaction, PriceHistory, SalesSummary
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
            },
            {
                'name': 'Loaded Nachos',
                'description': 'Crispy tortilla chips topped with melted cheese, jalapeños, guacamole, sour cream, and pico de gallo.',
                'price': '13.99',
                'is_vegetarian': True,
                'spice_level': 2
            },
            {
                'name': 'Stuffed Mushrooms',
                'description': 'Mushroom caps filled with a savory blend of herbs, garlic, and parmesan cheese.',
                'price': '10.99',
                'is_vegetarian': True,
                'spice_level': 0
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
            },
            {
                'name': 'Caprese Salad',
                'description': 'Fresh mozzarella, tomatoes, and basil drizzled with balsamic glaze and olive oil.',
                'price': '13.99',
                'is_vegetarian': True,
                'spice_level': 0
            },
            {
                'name': 'Spinach & Strawberry Salad',
                'description': 'Baby spinach with fresh strawberries, candied walnuts, goat cheese, and raspberry vinaigrette.',
                'price': '14.99',
                'is_vegetarian': True,
                'spice_level': 0
            },
            {
                'name': 'Asian Chicken Salad',
                'description': 'Mixed greens with grilled chicken, mandarin oranges, almonds, crispy wontons, and sesame ginger dressing.',
                'price': '16.99',
                'is_vegetarian': False,
                'spice_level': 1
            }
        ]
    },
    {
        'name': 'Soups',
        'description': 'Hearty and flavorful soups made fresh daily.',
        'items': [
            {
                'name': 'French Onion Soup',
                'description': 'Caramelized onions in rich beef broth, topped with croutons and melted Gruyère cheese.',
                'price': '8.99',
                'is_vegetarian': False,
                'spice_level': 0
            },
            {
                'name': 'Tomato Basil Soup',
                'description': 'Creamy tomato soup with fresh basil and a touch of cream.',
                'price': '7.99',
                'is_vegetarian': True,
                'spice_level': 0
            },
            {
                'name': 'Clam Chowder',
                'description': 'New England style creamy soup with clams, potatoes, and bacon.',
                'price': '9.99',
                'is_vegetarian': False,
                'spice_level': 0
            },
            {
                'name': 'Chicken Noodle Soup',
                'description': 'Classic comfort soup with chicken, vegetables, and egg noodles in savory broth.',
                'price': '8.99',
                'is_vegetarian': False,
                'spice_level': 0
            },
            {
                'name': 'Vegetable Minestrone',
                'description': 'Hearty Italian soup with seasonal vegetables, beans, and pasta in tomato broth.',
                'price': '7.99',
                'is_vegetarian': True,
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
        'name': 'Cocktails',
        'description': 'Handcrafted cocktails made with premium spirits.',
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
                'name': 'Old Fashioned',
                'description': 'Bourbon whiskey muddled with sugar, bitters, and a twist of orange.',
                'price': '14.99',
                'is_vegetarian': True,
                'spice_level': 0
            },
            {
                'name': 'Cosmopolitan',
                'description': 'Vodka, triple sec, cranberry juice, and fresh lime juice.',
                'price': '13.99',
                'is_vegetarian': True,
                'spice_level': 0
            },
            {
                'name': 'Piña Colada',
                'description': 'Rum blended with coconut cream and pineapple juice.',
                'price': '12.99',
                'is_vegetarian': True,
                'spice_level': 0
            },
            {
                'name': 'Espresso Martini',
                'description': 'Vodka, coffee liqueur, and freshly brewed espresso.',
                'price': '14.99',
                'is_vegetarian': True,
                'spice_level': 0
            }
        ]
    },
    {
        'name': 'Wine',
        'description': 'Curated selection of fine wines from around the world.',
        'items': [
            {
                'name': 'Cabernet Sauvignon',
                'description': 'Full-bodied red wine with notes of black currant, cedar, and vanilla.',
                'price': '12.99',
                'is_vegetarian': True,
                'spice_level': 0
            },
            {
                'name': 'Chardonnay',
                'description': 'Medium to full-bodied white wine with notes of apple, pear, and oak.',
                'price': '11.99',
                'is_vegetarian': True,
                'spice_level': 0
            },
            {
                'name': 'Pinot Noir',
                'description': 'Light to medium-bodied red wine with notes of cherry, raspberry, and earthy undertones.',
                'price': '13.99',
                'is_vegetarian': True,
                'spice_level': 0
            },
            {
                'name': 'Sauvignon Blanc',
                'description': 'Crisp white wine with notes of citrus, green apple, and tropical fruits.',
                'price': '10.99',
                'is_vegetarian': True,
                'spice_level': 0
            },
            {
                'name': 'Merlot',
                'description': 'Smooth red wine with notes of plum, black cherry, and chocolate.',
                'price': '11.99',
                'is_vegetarian': True,
                'spice_level': 0
            },
            {
                'name': 'Prosecco',
                'description': 'Sparkling white wine with notes of apple, pear, and white flowers.',
                'price': '14.99',
                'is_vegetarian': True,
                'spice_level': 0
            }
        ]
    },
    {
        'name': 'Beer',
        'description': 'Selection of craft and imported beers.',
        'items': [
            {
                'name': 'IPA',
                'description': 'India Pale Ale with hoppy, bitter flavor and citrus notes.',
                'price': '7.99',
                'is_vegetarian': True,
                'spice_level': 0
            },
            {
                'name': 'Stout',
                'description': 'Dark, rich beer with notes of coffee, chocolate, and roasted malt.',
                'price': '8.99',
                'is_vegetarian': True,
                'spice_level': 0
            },
            {
                'name': 'Pilsner',
                'description': 'Light, crisp lager with a clean, refreshing taste.',
                'price': '6.99',
                'is_vegetarian': True,
                'spice_level': 0
            },
            {
                'name': 'Wheat Beer',
                'description': 'Smooth, light beer with notes of citrus and coriander.',
                'price': '7.99',
                'is_vegetarian': True,
                'spice_level': 0
            },
            {
                'name': 'Amber Ale',
                'description': 'Medium-bodied beer with caramel malt flavor and moderate hop bitterness.',
                'price': '7.99',
                'is_vegetarian': True,
                'spice_level': 0
            }
        ]
    },
    {
        'name': 'Non-Alcoholic Beverages',
        'description': 'Refreshing non-alcoholic drinks and mocktails.',
        'items': [
            {
                'name': 'Fresh Lemonade',
                'description': 'Homemade lemonade with fresh lemons and a hint of mint.',
                'price': '4.99',
                'is_vegetarian': True,
                'spice_level': 0
            },
            {
                'name': 'Iced Tea',
                'description': 'Freshly brewed tea served over ice with lemon.',
                'price': '3.99',
                'is_vegetarian': True,
                'spice_level': 0
            },
            {
                'name': 'Fruit Smoothie',
                'description': 'Blend of seasonal fruits with yogurt and honey.',
                'price': '6.99',
                'is_vegetarian': True,
                'spice_level': 0
            },
            {
                'name': 'Virgin Mojito',
                'description': 'Mint, lime, sugar, and soda water - all the flavor without the alcohol.',
                'price': '5.99',
                'is_vegetarian': True,
                'spice_level': 0
            },
            {
                'name': 'Sparkling Water',
                'description': 'Carbonated water with a choice of fruit flavors.',
                'price': '3.99',
                'is_vegetarian': True,
                'spice_level': 0
            }
        ]
    },
    {
        'name': 'Coffee & Tea',
        'description': 'Premium hot beverages to enjoy with dessert or any time.',
        'items': [
            {
                'name': 'Espresso',
                'description': 'Strong, concentrated coffee served in a small cup.',
                'price': '3.99',
                'is_vegetarian': True,
                'spice_level': 0
            },
            {
                'name': 'Cappuccino',
                'description': 'Espresso with steamed milk and foam.',
                'price': '4.99',
                'is_vegetarian': True,
                'spice_level': 0
            },
            {
                'name': 'Latte',
                'description': 'Espresso with steamed milk and a light layer of foam.',
                'price': '4.99',
                'is_vegetarian': True,
                'spice_level': 0
            },
            {
                'name': 'Herbal Tea',
                'description': 'Selection of caffeine-free herbal teas.',
                'price': '3.99',
                'is_vegetarian': True,
                'spice_level': 0
            },
            {
                'name': 'Hot Chocolate',
                'description': 'Rich chocolate with steamed milk, topped with whipped cream.',
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
            admin_user = User.objects.create_superuser('admin', 'admin@example.com', 'admin123')
            # Set admin user's staff profile role to ADMIN
            if hasattr(admin_user, 'staff_profile'):
                admin_user.staff_profile.role = 'ADMIN'
                admin_user.staff_profile.save()
            self.stdout.write(self.style.SUCCESS('Admin user created with ADMIN role'))

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

        # Create inventory transactions
        self.create_inventory_transactions()

        # Create price history
        self.create_price_history()

        # Create sales summaries
        self.create_sales_summaries()

        self.stdout.write(self.style.SUCCESS('Database successfully populated!'))

    @transaction.atomic
    def create_users(self, num_users):
        self.stdout.write('Creating users...')

        # Create users
        users = []
        for _ in range(num_users):
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
                # Calculate cost price (60-80% of selling price)
                price = Decimal(item_data['price'])
                cost_percentage = Decimal(random.uniform(0.6, 0.8))
                cost_price = (price * cost_percentage).quantize(Decimal('0.01'))

                # Set random stock values
                current_stock = random.randint(10, 100)
                stock_alert_threshold = random.randint(5, 20)

                menu_item = MenuItem(
                    category=category,
                    name=item_data['name'],
                    description=item_data['description'],
                    price=price,
                    is_available=True,
                    is_featured=item_data.get('is_featured', False),
                    is_vegetarian=item_data.get('is_vegetarian', False),
                    spice_level=item_data.get('spice_level', 0),
                    current_stock=current_stock,
                    stock_alert_threshold=stock_alert_threshold,
                    cost_price=cost_price
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
                        order_item = OrderItem.objects.create(
                            order=order,
                            menu_item=item_data['menu_item'],
                            quantity=item_data['quantity'],
                            price=item_data['price'],
                            special_instructions=item_data['special_instructions'],
                            inventory_updated=False  # Will be updated by the save method
                        )

                        # The save method in OrderItem should handle inventory updates
                        # If the order is COMPLETED, make sure inventory is updated
                        if status == 'COMPLETED' and not order_item.inventory_updated:
                            # Force inventory update by saving again
                            order_item.inventory_updated = True
                            order_item.save(update_fields=['inventory_updated'])

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

    def create_inventory_transactions(self):
        self.stdout.write('Creating inventory transactions...')

        menu_items = list(MenuItem.objects.all())
        users = list(User.objects.filter(is_staff=True))
        admin_user = User.objects.filter(username='admin').first()

        if not users and admin_user:
            users = [admin_user]

        transaction_types = ['PURCHASE', 'ADJUSTMENT', 'WASTE', 'RETURN']
        transaction_count = 0

        # Create initial purchase transactions for all menu items
        for menu_item in menu_items:
            try:
                with transaction.atomic():
                    # Initial stock purchase
                    purchase_date = fake.date_time_between(
                        start_date='-90d',
                        end_date='-60d',
                        tzinfo=timezone.get_current_timezone()
                    )

                    purchase_quantity = menu_item.current_stock + random.randint(10, 50)

                    InventoryTransaction.objects.create(
                        menu_item=menu_item,
                        transaction_type='PURCHASE',
                        quantity=purchase_quantity,
                        unit_price=menu_item.cost_price,
                        total_price=menu_item.cost_price * purchase_quantity,
                        reference=f'Initial Purchase #{random.randint(1000, 9999)}',
                        notes='Initial inventory stock purchase',
                        created_by=random.choice(users) if users else None,
                        created_at=purchase_date
                    )
                    transaction_count += 1

                    # Add some random transactions
                    for _ in range(random.randint(0, 3)):
                        trans_type = random.choice(transaction_types)

                        # Determine quantity based on transaction type
                        if trans_type == 'PURCHASE':
                            quantity = random.randint(5, 30)
                        elif trans_type == 'WASTE' or trans_type == 'RETURN':
                            quantity = -random.randint(1, 5)
                        else:  # ADJUSTMENT
                            quantity = random.randint(-3, 5)

                        trans_date = fake.date_time_between(
                            start_date='-60d',
                            end_date='now',
                            tzinfo=timezone.get_current_timezone()
                        )

                        unit_price = menu_item.cost_price
                        total_price = unit_price * abs(quantity)

                        InventoryTransaction.objects.create(
                            menu_item=menu_item,
                            transaction_type=trans_type,
                            quantity=quantity,
                            unit_price=unit_price,
                            total_price=total_price,
                            reference=f'{trans_type} #{random.randint(1000, 9999)}',
                            notes=f'{trans_type} transaction for inventory management',
                            created_by=random.choice(users) if users else None,
                            created_at=trans_date
                        )
                        transaction_count += 1
            except Exception as e:
                self.stdout.write(self.style.WARNING(f'Error creating inventory transaction: {e}'))

        self.stdout.write(self.style.SUCCESS(f'Created {transaction_count} inventory transactions'))

    def create_price_history(self):
        self.stdout.write('Creating price history records...')

        menu_items = list(MenuItem.objects.all())
        users = list(User.objects.filter(is_staff=True))
        admin_user = User.objects.filter(username='admin').first()

        if not users and admin_user:
            users = [admin_user]

        history_count = 0

        # Create price history for some menu items
        for menu_item in random.sample(menu_items, int(len(menu_items) * 0.4)):
            try:
                with transaction.atomic():
                    # Get current price
                    current_price = menu_item.price

                    # Create 1-3 price history records
                    for _ in range(random.randint(1, 3)):
                        # Calculate old price (90-110% of current price)
                        price_factor = Decimal(random.uniform(0.9, 1.1))
                        old_price = (current_price * price_factor).quantize(Decimal('0.01'))

                        # Ensure old price is different from current price
                        if old_price == current_price:
                            old_price = current_price - Decimal('1.00')

                        # Create record with date in the past
                        change_date = fake.date_time_between(
                            start_date='-180d',
                            end_date='-30d',
                            tzinfo=timezone.get_current_timezone()
                        )

                        PriceHistory.objects.create(
                            menu_item=menu_item,
                            old_price=old_price,
                            new_price=current_price,
                            changed_by=random.choice(users) if users else None,
                            changed_at=change_date,
                            notes=f'Price adjustment due to {random.choice(["seasonal changes", "cost increases", "market demand", "promotional offer"])}'
                        )

                        # Set current price to old price for next iteration
                        current_price = old_price
                        history_count += 1
            except Exception as e:
                self.stdout.write(self.style.WARNING(f'Error creating price history: {e}'))

        self.stdout.write(self.style.SUCCESS(f'Created {history_count} price history records'))

    def create_sales_summaries(self):
        self.stdout.write('Creating sales summary records...')

        menu_items = list(MenuItem.objects.all())
        summary_count = 0

        # Create sales summaries for the past 30 days
        end_date = timezone.now().date()
        start_date = end_date - datetime.timedelta(days=30)

        for menu_item in menu_items:
            try:
                current_date = start_date
                while current_date <= end_date:
                    # Generate random sales data
                    quantity_sold = random.randint(0, 15)

                    # Skip days with no sales
                    if quantity_sold == 0 and random.random() < 0.3:
                        current_date += datetime.timedelta(days=1)
                        continue

                    revenue = menu_item.price * quantity_sold
                    cost = menu_item.cost_price * quantity_sold
                    profit = revenue - cost

                    SalesSummary.objects.create(
                        menu_item=menu_item,
                        date=current_date,
                        quantity_sold=quantity_sold,
                        revenue=revenue,
                        cost=cost,
                        profit=profit
                    )

                    summary_count += 1
                    current_date += datetime.timedelta(days=1)
            except Exception as e:
                self.stdout.write(self.style.WARNING(f'Error creating sales summary: {e}'))

        self.stdout.write(self.style.SUCCESS(f'Created {summary_count} sales summary records'))
