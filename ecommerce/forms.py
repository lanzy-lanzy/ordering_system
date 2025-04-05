from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from .models import CustomerProfile, Order, Payment, Reservation, ReservationPayment
from django.utils import timezone

class RegistrationForm(UserCreationForm):
    """Form for user registration"""
    email = forms.EmailField(required=True)
    first_name = forms.CharField(max_length=30, required=True)
    last_name = forms.CharField(max_length=30, required=True)
    phone = forms.CharField(max_length=20, required=False)
    address = forms.CharField(widget=forms.Textarea(attrs={'rows': 3}), required=False)
    city = forms.CharField(max_length=100, required=False)
    state = forms.CharField(max_length=100, required=False)
    zip_code = forms.CharField(max_length=20, required=False)

    class Meta:
        model = User
        fields = ('username', 'first_name', 'last_name', 'email', 'password1', 'password2')

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data['email']
        user.first_name = self.cleaned_data['first_name']
        user.last_name = self.cleaned_data['last_name']
        user.is_staff = False  # Ensure the user is not staff

        if commit:
            user.save()

            # Make sure the customer profile exists and update it
            from .models import CustomerProfile
            profile, created = CustomerProfile.objects.get_or_create(user=user)
            profile.phone = self.cleaned_data.get('phone', '')
            profile.address = self.cleaned_data.get('address', '')
            profile.city = self.cleaned_data.get('city', '')
            profile.state = self.cleaned_data.get('state', '')
            profile.zip_code = self.cleaned_data.get('zip_code', '')
            profile.save()

        return user


class CheckoutForm(forms.ModelForm):
    """Form for checkout process"""
    first_name = forms.CharField(max_length=100, required=True, widget=forms.HiddenInput())
    last_name = forms.CharField(max_length=100, required=True, widget=forms.HiddenInput())
    email = forms.EmailField(required=True, widget=forms.HiddenInput())
    phone = forms.CharField(max_length=20, required=True, widget=forms.HiddenInput())
    order_type = forms.ChoiceField(
        choices=Order.ORDER_TYPE_CHOICES,
        initial='PICKUP',
        required=True,
        widget=forms.RadioSelect(),
        help_text="Select how you'd like to receive your order"
    )
    table_number = forms.CharField(
        max_length=20,
        required=False,
        widget=forms.HiddenInput(),
        help_text="Table number for dine-in orders"
    )
    number_of_guests = forms.IntegerField(
        min_value=1,
        max_value=20,
        initial=2,
        required=False,
        help_text="Number of guests for dine-in orders"
    )
    special_instructions = forms.CharField(
        widget=forms.Textarea(attrs={'rows': 3}),
        required=False,
        help_text="Add any special instructions for your order here."
    )

    class Meta:
        model = Order
        fields = ('order_type', 'table_number', 'number_of_guests', 'special_instructions')

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)

        # Set payment method to GCash by default
        self.instance.payment_method = 'GCASH'
        # Set order type to PICKUP by default (can be changed by user)
        self.instance.order_type = 'PICKUP'

        # Pre-fill form with user data if available
        if user and user.is_authenticated and hasattr(user, 'customer_profile'):
            profile = user.customer_profile
            self.fields['first_name'].initial = user.first_name
            self.fields['last_name'].initial = user.last_name
            self.fields['email'].initial = user.email
            self.fields['phone'].initial = profile.phone


class GCashPaymentForm(forms.ModelForm):
    """Form for GCash payment verification"""
    reference_number = forms.CharField(max_length=100, required=True,
                                      help_text="Enter the GCash reference number from your transaction")
    payment_proof = forms.ImageField(required=True,
                                    help_text="Upload a screenshot of your GCash payment confirmation")

    class Meta:
        model = Payment
        fields = ('reference_number', 'payment_proof')


class ReservationPaymentForm(forms.ModelForm):
    """Form for reservation payment"""
    PAYMENT_TYPE_CHOICES = [
        ('FULL', 'Full Payment'),
        ('DEPOSIT', 'Deposit (50%)')
    ]

    payment_type = forms.ChoiceField(
        choices=PAYMENT_TYPE_CHOICES,
        widget=forms.RadioSelect,
        initial='DEPOSIT',
        help_text="Choose whether to pay the full amount or a 50% deposit"
    )
    reference_number = forms.CharField(
        max_length=100,
        required=True,
        help_text="Enter the GCash reference number from your transaction"
    )
    payment_proof = forms.ImageField(
        required=True,
        help_text="Upload a screenshot of your GCash payment confirmation"
    )

    class Meta:
        model = ReservationPayment
        fields = ('payment_type', 'reference_number', 'payment_proof')


class ReservationForm(forms.ModelForm):
    """Form for making reservations"""
    date = forms.DateField(
        widget=forms.DateInput(attrs={'type': 'date'}),
        help_text="Select the date for your reservation"
    )
    time = forms.TimeField(
        widget=forms.TimeInput(attrs={'type': 'time'}),
        help_text="Select the time for your reservation"
    )
    party_size = forms.IntegerField(
        min_value=1,
        max_value=20,
        help_text="Number of guests (maximum 20)"
    )
    special_requests = forms.CharField(
        widget=forms.Textarea(attrs={'rows': 3}),
        required=False,
        help_text="Any special requests or notes for your reservation"
    )

    class Meta:
        model = Reservation
        fields = ('name', 'email', 'phone', 'date', 'time', 'party_size', 'special_requests')

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)

        # Pre-fill form with user data if available
        if user and user.is_authenticated and hasattr(user, 'customer_profile'):
            profile = user.customer_profile
            self.fields['name'].initial = f"{user.first_name} {user.last_name}".strip()
            self.fields['email'].initial = user.email
            self.fields['phone'].initial = profile.phone

    def clean(self):
        cleaned_data = super().clean()
        date = cleaned_data.get('date')
        time = cleaned_data.get('time')

        # Check if date and time are provided
        if not date:
            self.add_error('date', "Reservation date is required")
            return cleaned_data
        if not time:
            self.add_error('time', "Reservation time is required")
            return cleaned_data

        # Check if date is in the past
        if date < timezone.now().date():
            self.add_error('date', "Reservation date cannot be in the past")
            return cleaned_data

        # Check if time is in the past for today's reservations
        # Only check if the date is today
        if date == timezone.now().date():
            # Add a buffer of 30 minutes to allow for immediate reservations
            current_time = timezone.now()
            buffer_time = current_time + timezone.timedelta(minutes=30)
            if time < buffer_time.time():
                self.add_error('time', "Reservation time must be at least 30 minutes in the future")
                # Log for debugging
                print(f"Time validation failed: Current time: {current_time.time()}, Buffer time: {buffer_time.time()}, Selected time: {time}")

        return cleaned_data
