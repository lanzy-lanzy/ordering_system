"""
Script to run the populate_restobar command directly.
"""
import os
import sys
import django

# Set up Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'food_ordering.settings')
django.setup()

# Import the command
from django.core.management import call_command

# Run the command with custom parameters
if __name__ == "__main__":
    # Get command line arguments
    args = sys.argv[1:]
    
    # Default values
    kwargs = {
        'users': 10,
        'orders': 30,
        'reservations': 20,
        'reviews': 50
    }
    
    # Parse arguments
    for arg in args:
        if '=' in arg:
            key, value = arg.split('=')
            if key.startswith('--'):
                key = key[2:]  # Remove -- prefix
                if key in kwargs and value.isdigit():
                    kwargs[key] = int(value)
    
    print(f"Running populate_restobar with parameters: {kwargs}")
    
    # Call the command
    call_command('populate_restobar', **kwargs)
    
    print("Done!")
