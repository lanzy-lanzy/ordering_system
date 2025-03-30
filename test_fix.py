# This is a simple test to verify our fix
from decimal import Decimal

def div(value, arg):
    """Divide the value by the arg."""
    try:
        if arg == 0:
            return 0
        return value / arg
    except (ValueError, TypeError, ZeroDivisionError):
        try:
            if Decimal(arg) == 0:
                return 0
            return Decimal(value) / Decimal(arg)
        except:
            return 0

# Test with the values that caused the error
total_spent = Decimal('115.91')
total_orders = 1

# Calculate average order value
avg_order = div(total_spent, total_orders)
print(f"Total spent: {total_spent}")
print(f"Total orders: {total_orders}")
print(f"Average order value: {avg_order}")

# Test with string values (similar to what might happen in templates)
total_spent_str = '115.91'
total_orders_str = '1'
avg_order_str = div(total_spent_str, total_orders_str)
print(f"\nTotal spent (string): {total_spent_str}")
print(f"Total orders (string): {total_orders_str}")
print(f"Average order value (string): {avg_order_str}")
