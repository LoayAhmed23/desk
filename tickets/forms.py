from django import forms
from django.contrib.auth.models import User
from .models import Ticket, Note, Category


class TicketCreateForm(forms.ModelForm):
    """Form for employees to submit a new support request."""

    class Meta:
        model = Ticket
        fields = ['title', 'description', 'category', 'priority']
        widgets = {
            'title': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': 'Brief summary of your issue...',
                'id': 'ticket-title',
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-textarea',
                'placeholder': 'Describe your issue in detail...',
                'rows': 5,
                'id': 'ticket-description',
            }),
            'category': forms.Select(attrs={
                'class': 'form-select',
                'id': 'ticket-category',
            }),
            'priority': forms.Select(attrs={
                'class': 'form-select',
                'id': 'ticket-priority',
            }),
        }


class TicketUpdateForm(forms.ModelForm):
    """Form for agents to update ticket status."""

    class Meta:
        model = Ticket
        fields = ['status', 'priority']
        widgets = {
            'status': forms.Select(attrs={
                'class': 'form-select',
                'id': 'ticket-status-update',
            }),
            'priority': forms.Select(attrs={
                'class': 'form-select',
                'id': 'ticket-priority-update',
            }),
        }


class TicketAssignForm(forms.Form):
    """Form for managers to assign a ticket to an agent."""
    assigned_to = forms.ModelChoiceField(
        queryset=User.objects.filter(is_staff=True),
        widget=forms.Select(attrs={
            'class': 'form-select',
            'id': 'ticket-assign',
        }),
        label='Assign to',
        empty_label='— Select Agent —',
    )


class NoteForm(forms.ModelForm):
    """Form for agents to add internal notes."""

    class Meta:
        model = Note
        fields = ['content']
        widgets = {
            'content': forms.Textarea(attrs={
                'class': 'form-textarea',
                'placeholder': 'Add an internal note (private, not visible to submitter)...',
                'rows': 3,
                'id': 'note-content',
            }),
        }
        labels = {
            'content': 'Internal Note',
        }


class LoginForm(forms.Form):
    """Employee email-based login form."""
    email = forms.EmailField(
        widget=forms.EmailInput(attrs={
            'class': 'form-input',
            'placeholder': 'you@company.com',
            'id': 'login-email',
            'autofocus': True,
        })
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-input',
            'placeholder': '••••••••',
            'id': 'login-password',
        })
    )


class RegisterForm(forms.Form):
    """Employee registration form (demo purposes)."""
    first_name = forms.CharField(
        max_length=30,
        widget=forms.TextInput(attrs={
            'class': 'form-input',
            'placeholder': 'First name',
            'id': 'register-first-name',
        })
    )
    last_name = forms.CharField(
        max_length=30,
        widget=forms.TextInput(attrs={
            'class': 'form-input',
            'placeholder': 'Last name',
            'id': 'register-last-name',
        })
    )
    email = forms.EmailField(
        widget=forms.EmailInput(attrs={
            'class': 'form-input',
            'placeholder': 'you@company.com',
            'id': 'register-email',
        })
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-input',
            'placeholder': 'Create a password',
            'id': 'register-password',
        })
    )
    role = forms.ChoiceField(
        choices=[
            ('employee', 'Employee'),
            ('agent', 'Support Agent'),
            ('manager', 'Manager'),
        ],
        widget=forms.Select(attrs={
            'class': 'form-select',
            'id': 'register-role',
        })
    )
