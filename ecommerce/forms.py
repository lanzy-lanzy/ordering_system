from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from .models import CustomerProfile, Order, Payment

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
    special_instructions = forms.CharField(widget=forms.Textarea(attrs={'rows': 3}), required=False,
                                         help_text="Add any special instructions for your order here.")

    class Meta:
        model = Order
        fields = ('special_instructions',)

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)

        # Set payment method to GCash by default
        self.instance.payment_method = 'GCASH'
        # Set order type to PICKUP by default
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
