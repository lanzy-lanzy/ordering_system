"""
Test script for the populate_restobar command.

This script shows how to run the command and what to expect.
"""

import os
import django
from django.core.management import call_command

# Set up Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'food_ordering.settings')
django.setup()

# Import models
from ecommerce.models import Category, MenuItem, Reservation, Order, Review, Cart
from django.contrib.auth.models import User

# Print current counts
print("Current database counts:")
print(f"Users: {User.objects.count()}")
print(f"Categories: {Category.objects.count()}")
print(f"Menu Items: {MenuItem.objects.count()}")
print(f"Reservations: {Reservation.objects.count()}")
print(f"Orders: {Order.objects.count()}")
print(f"Reviews: {Review.objects.count()}")
print(f"Carts: {Cart.objects.count()}")
print("\n")

# Run the command with custom parameters
print("Running populate_restobar command...")
call_command('populate_restobar', users=5, orders=10, reservations=8, reviews=15)

# Print updated counts
print("\nUpdated database counts:")
print(f"Users: {User.objects.count()}")
print(f"Categories: {Category.objects.count()}")
print(f"Menu Items: {MenuItem.objects.count()}")
print(f"Reservations: {Reservation.objects.count()}")
print(f"Orders: {Order.objects.count()}")
print(f"Reviews: {Review.objects.count()}")
print(f"Carts: {Cart.objects.count()}")

# Print sample data
print("\nSample Category:")
category = Category.objects.first()
print(f"- {category.name}: {category.description}")

print("\nSample Menu Items:")
for item in MenuItem.objects.filter(category=category)[:3]:
    print(f"- {item.name}: ${item.price} - {item.description[:50]}...")

print("\nSample Reservation:")
reservation = Reservation.objects.first()
print(f"- {reservation.name} on {reservation.date} at {reservation.time} for {reservation.party_size} people")

print("\nSample Order:")
order = Order.objects.first()
print(f"- Order #{order.id} by {order.user.username} for ${order.total_amount} ({order.status})")
print("  Items:")
for item in order.order_items.all()[:3]:
    print(f"  - {item.quantity}x {item.menu_item.name} (${item.price})")

print("\nSample Review:")
review = Review.objects.first()
print(f"- {review.user.username} rated {review.menu_item.name} {review.rating}/5 stars")
print(f"  \"{review.comment}\"")
