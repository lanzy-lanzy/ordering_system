import random
import datetime
from decimal import Decimal
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from django.utils import timezone
from django.db import transaction
from ecommerce.models import (
    Category, MenuItem, InventoryTransaction, StaffProfile
)

# Restaurant categories and menu items
FOOD_CATEGORIES = [
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
            }
        ]
    },
    {
        'name': 'Salads',
        'description': 'Fresh and healthy salad options.',
        'items': [
            {
                'name': 'Caesar Salad',
                'description': 'Crisp romaine lettuce with Caesar dressing, croutons, and parmesan cheese.',
                'price': '10.99',
                'is_vegetarian': True,
                'spice_level': 0
            },
            {
                'name': 'Greek Salad',
                'description': 'Mixed greens with feta cheese, olives, tomatoes, cucumbers, and Greek dressing.',
                'price': '12.99',
                'is_vegetarian': True,
                'spice_level': 0
            },
            {
                'name': 'Cobb Salad',
                'description': 'Mixed greens topped with grilled chicken, bacon, avocado, blue cheese, and eggs.',
                'price': '14.99',
                'is_vegetarian': False,
                'spice_level': 0
            }
        ]
    },
    {
        'name': 'Main Courses',
        'description': 'Hearty and delicious main dishes.',
        'items': [
            {
                'name': 'Grilled Salmon',
                'description': 'Fresh salmon fillet grilled to perfection, served with seasonal vegetables and rice.',
                'price': '22.99',
                'is_vegetarian': False,
                'spice_level': 0,
                'is_featured': True
            },
            {
                'name': 'Filet Mignon',
                'description': '8oz tender beef filet, served with mashed potatoes and grilled asparagus.',
                'price': '29.99',
                'is_vegetarian': False,
                'spice_level': 0,
                'is_featured': True
            },
            {
                'name': 'Chicken Parmesan',
                'description': 'Breaded chicken breast topped with marinara sauce and mozzarella, served with pasta.',
                'price': '19.99',
                'is_vegetarian': False,
                'spice_level': 1
            },
            {
                'name': 'Vegetable Stir Fry',
                'description': 'Fresh vegetables stir-fried with tofu in a savory sauce, served with rice.',
                'price': '16.99',
                'is_vegetarian': True,
                'spice_level': 2
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
                'price': '16.99',
                'is_vegetarian': False,
                'spice_level': 1
            },
            {
                'name': 'Fettuccine Alfredo',
                'description': 'Fettuccine pasta in a creamy parmesan sauce.',
                'price': '15.99',
                'is_vegetarian': True,
                'spice_level': 0
            },
            {
                'name': 'Seafood Linguine',
                'description': 'Linguine with shrimp, mussels, and calamari in a white wine sauce.',
                'price': '21.99',
                'is_vegetarian': False,
                'spice_level': 1,
                'is_featured': True
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
                'price': '8.99',
                'is_vegetarian': True,
                'spice_level': 0
            },
            {
                'name': 'Chocolate Lava Cake',
                'description': 'Warm chocolate cake with a molten center, served with vanilla ice cream.',
                'price': '9.99',
                'is_vegetarian': True,
                'spice_level': 0,
                'is_featured': True
            },
            {
                'name': 'New York Cheesecake',
                'description': 'Creamy cheesecake with a graham cracker crust, topped with berry compote.',
                'price': '8.99',
                'is_vegetarian': True,
                'spice_level': 0
            }
        ]
    }
]

DRINK_CATEGORIES = [
    {
        'name': 'Wine',
        'description': 'Fine selection of red, white, and sparkling wines.',
        'items': [
            {
                'name': 'Cabernet Sauvignon',
                'description': 'Full-bodied red wine with notes of black currant, cedar, and spice.',
                'price': '12.99',
                'is_vegetarian': True,
                'spice_level': 0
            },
            {
                'name': 'Chardonnay',
                'description': 'Medium to full-bodied white wine with notes of apple, pear, and vanilla.',
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
                'description': 'Crisp, dry white wine with notes of citrus, green apple, and herbs.',
                'price': '10.99',
                'is_vegetarian': True,
                'spice_level': 0
            },
            {
                'name': 'Prosecco',
                'description': 'Sparkling Italian wine with notes of apple, pear, and white flowers.',
                'price': '9.99',
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
                'name': 'Pale Ale',
                'description': 'Balanced beer with moderate hop flavor and malty sweetness.',
                'price': '7.49',
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
                'description': 'Vodka, triple sec, cranberry juice, and lime juice.',
                'price': '13.99',
                'is_vegetarian': True,
                'spice_level': 0
            },
            {
                'name': 'Negroni',
                'description': 'Equal parts gin, Campari, and sweet vermouth.',
                'price': '14.99',
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
                'description': 'Refreshing carbonated water with a slice of lemon or lime.',
                'price': '2.99',
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
                'description': 'Rich, creamy hot chocolate topped with whipped cream.',
                'price': '4.99',
                'is_vegetarian': True,
                'spice_level': 0
            }
        ]
    }
]


class Command(BaseCommand):
    help = 'Populates the database with base data for the restaurant'

    def add_arguments(self, parser):
        parser.add_argument(
            '--staff',
            action='store_true',
            help='Create staff users (admin, manager, cashier)'
        )
        parser.add_argument(
            '--food',
            action='store_true',
            help='Create food categories and menu items'
        )
        parser.add_argument(
            '--drinks',
            action='store_true',
            help='Create drink categories and menu items'
        )
        parser.add_argument(
            '--all',
            action='store_true',
            help='Create all base data (staff, food, drinks)'
        )

    def handle(self, *args, **options):
        create_staff = options['staff'] or options['all']
        create_food = options['food'] or options['all']
        create_drinks = options['drinks'] or options['all']

        # If no specific options are provided, create everything
        if not (create_staff or create_food or create_drinks):
            create_staff = create_food = create_drinks = True

        self.stdout.write(self.style.SUCCESS('Starting to populate the database with base data...'))

        if create_staff:
            self.create_staff_users()

        if create_food:
            self.create_food_categories()

        if create_drinks:
            self.create_drink_categories()

        self.stdout.write(self.style.SUCCESS('Database successfully populated with base data!'))

    def create_staff_users(self):
        """Create admin, manager, and cashier users"""
        self.stdout.write('Creating staff users...')

        # Create admin user if it doesn't exist
        if not User.objects.filter(username='admin').exists():
            admin_user = User.objects.create_superuser(
                username='admin',
                email='admin@example.com',
                password='admin123',
                first_name='Admin',
                last_name='User'
            )

            # Update staff profile (it should already exist due to the signal)
            try:
                admin_user.refresh_from_db()  # Refresh to ensure we have the latest data
                admin_user.staff_profile.role = 'ADMIN'
                admin_user.staff_profile.phone = '09123456789'
                admin_user.staff_profile.save()
                self.stdout.write(self.style.SUCCESS('Admin staff profile updated'))
            except StaffProfile.DoesNotExist:
                self.stdout.write(self.style.WARNING('Admin staff profile not found, this is unusual'))
                # Only create if it doesn't exist (which shouldn't happen due to signals)
                StaffProfile.objects.create(
                    user=admin_user,
                    role='ADMIN',
                    phone='09123456789'
                )

            self.stdout.write(self.style.SUCCESS('Admin user created'))

        # Create manager user if it doesn't exist
        if not User.objects.filter(username='manager').exists():
            manager_user = User.objects.create_user(
                username='manager',
                email='manager@example.com',
                password='manager123',
                first_name='Restaurant',
                last_name='Manager',
                is_staff=True
            )

            # Update staff profile (it should already exist due to the signal)
            try:
                manager_user.refresh_from_db()  # Refresh to ensure we have the latest data
                manager_user.staff_profile.role = 'MANAGER'
                manager_user.staff_profile.phone = '09123456788'
                manager_user.staff_profile.save()
                self.stdout.write(self.style.SUCCESS('Manager staff profile updated'))
            except StaffProfile.DoesNotExist:
                self.stdout.write(self.style.WARNING('Manager staff profile not found, this is unusual'))
                # Only create if it doesn't exist (which shouldn't happen due to signals)
                StaffProfile.objects.create(
                    user=manager_user,
                    role='MANAGER',
                    phone='09123456788'
                )

            self.stdout.write(self.style.SUCCESS('Manager user created'))

        # Create cashier user if it doesn't exist
        if not User.objects.filter(username='cashier').exists():
            cashier_user = User.objects.create_user(
                username='cashier',
                email='cashier@example.com',
                password='cashier123',
                first_name='Restaurant',
                last_name='Cashier',
                is_staff=True
            )

            # Update staff profile (it should already exist due to the signal)
            try:
                cashier_user.refresh_from_db()  # Refresh to ensure we have the latest data
                cashier_user.staff_profile.role = 'CASHIER'
                cashier_user.staff_profile.phone = '09123456787'
                cashier_user.staff_profile.save()
                self.stdout.write(self.style.SUCCESS('Cashier staff profile updated'))
            except StaffProfile.DoesNotExist:
                self.stdout.write(self.style.WARNING('Cashier staff profile not found, this is unusual'))
                # Only create if it doesn't exist (which shouldn't happen due to signals)
                StaffProfile.objects.create(
                    user=cashier_user,
                    role='CASHIER',
                    phone='09123456787'
                )

            self.stdout.write(self.style.SUCCESS('Cashier user created'))

    def create_food_categories(self):
        """Create food categories and menu items"""
        self.stdout.write('Creating food categories and menu items...')

        created_categories = 0
        created_items = 0

        for category_data in FOOD_CATEGORIES:
            try:
                with transaction.atomic():
                    # Create or get the category
                    category, created = Category.objects.get_or_create(
                        name=category_data['name'],
                        defaults={
                            'description': category_data['description']
                        }
                    )

                    if created:
                        created_categories += 1

                    # Create menu items for this category
                    for item_data in category_data['items']:
                        # Calculate cost price (60-80% of selling price)
                        price = Decimal(item_data['price'])
                        cost_percentage = Decimal(random.uniform(0.6, 0.8))
                        cost_price = (price * cost_percentage).quantize(Decimal('0.01'))

                        # Set stock values
                        current_stock = random.randint(20, 100)
                        stock_alert_threshold = random.randint(5, 15)

                        # Check if item already exists
                        if not MenuItem.objects.filter(name=item_data['name'], category=category).exists():
                            menu_item = MenuItem.objects.create(
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

                            # Create initial inventory transaction
                            InventoryTransaction.objects.create(
                                menu_item=menu_item,
                                transaction_type='PURCHASE',
                                quantity=current_stock,
                                unit_price=cost_price,
                                total_price=cost_price * current_stock,
                                reference=f'Initial Stock #{random.randint(1000, 9999)}',
                                notes='Initial inventory stock purchase'
                            )

                            created_items += 1

            except Exception as e:
                self.stdout.write(self.style.ERROR(f'Error creating food category {category_data["name"]}: {e}'))

        self.stdout.write(self.style.SUCCESS(f'Created {created_categories} food categories and {created_items} menu items'))

    def create_drink_categories(self):
        """Create drink categories and menu items"""
        self.stdout.write('Creating drink categories and menu items...')

        created_categories = 0
        created_items = 0

        for category_data in DRINK_CATEGORIES:
            try:
                with transaction.atomic():
                    # Create or get the category
                    category, created = Category.objects.get_or_create(
                        name=category_data['name'],
                        defaults={
                            'description': category_data['description']
                        }
                    )

                    if created:
                        created_categories += 1

                    # Create menu items for this category
                    for item_data in category_data['items']:
                        # Calculate cost price (60-80% of selling price)
                        price = Decimal(item_data['price'])
                        cost_percentage = Decimal(random.uniform(0.6, 0.8))
                        cost_price = (price * cost_percentage).quantize(Decimal('0.01'))

                        # Set stock values
                        current_stock = random.randint(20, 100)
                        stock_alert_threshold = random.randint(5, 15)

                        # Check if item already exists
                        if not MenuItem.objects.filter(name=item_data['name'], category=category).exists():
                            menu_item = MenuItem.objects.create(
                                category=category,
                                name=item_data['name'],
                                description=item_data['description'],
                                price=price,
                                is_available=True,
                                is_featured=item_data.get('is_featured', False),
                                is_vegetarian=item_data.get('is_vegetarian', True),  # Most drinks are vegetarian
                                spice_level=item_data.get('spice_level', 0),
                                current_stock=current_stock,
                                stock_alert_threshold=stock_alert_threshold,
                                cost_price=cost_price
                            )

                            # Create initial inventory transaction
                            InventoryTransaction.objects.create(
                                menu_item=menu_item,
                                transaction_type='PURCHASE',
                                quantity=current_stock,
                                unit_price=cost_price,
                                total_price=cost_price * current_stock,
                                reference=f'Initial Stock #{random.randint(1000, 9999)}',
                                notes='Initial inventory stock purchase'
                            )

                            created_items += 1

            except Exception as e:
                self.stdout.write(self.style.ERROR(f'Error creating drink category {category_data["name"]}: {e}'))

        self.stdout.write(self.style.SUCCESS(f'Created {created_categories} drink categories and {created_items} menu items'))
