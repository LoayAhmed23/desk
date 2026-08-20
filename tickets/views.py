from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib import messages
from django.db.models import Q, Count
from django.utils import timezone

from .models import Ticket, Note, ActivityLog, Category
from .forms import (
    TicketCreateForm, TicketUpdateForm, TicketAssignForm,
    NoteForm, LoginForm, RegisterForm,
)


# ─── Authentication ─────────────────────────────────────────────────────

def login_view(request):
    """Employee email-based login."""
    if request.user.is_authenticated:
        return redirect('dashboard')

    form = LoginForm()
    if request.method == 'POST':
        form = LoginForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data['email']
            password = form.cleaned_data['password']
            # Find user by email
            try:
                user = User.objects.get(email=email)
            except User.DoesNotExist:
                messages.error(request, 'No account found with that email.')
                return render(request, 'tickets/login.html', {'form': form})

            user = authenticate(request, username=user.username, password=password)
            if user is not None:
                login(request, user)
                messages.success(request, f'Welcome back, {user.first_name}!')
                return redirect('dashboard')
            else:
                messages.error(request, 'Invalid credentials.')
    return render(request, 'tickets/login.html', {'form': form})


def register_view(request):
    """Demo registration for employees, agents, and managers."""
    if request.user.is_authenticated:
        return redirect('dashboard')

    form = RegisterForm()
    if request.method == 'POST':
        form = RegisterForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data['email']
            password = form.cleaned_data['password']
            first_name = form.cleaned_data['first_name']
            last_name = form.cleaned_data['last_name']
            role = form.cleaned_data['role']

            if User.objects.filter(email=email).exists():
                messages.error(request, 'An account with that email already exists.')
                return render(request, 'tickets/register.html', {'form': form})

            # Create username from email
            username = email.split('@')[0]
            if User.objects.filter(username=username).exists():
                username = f"{username}_{User.objects.count()}"

            user = User.objects.create_user(
                username=username,
                email=email,
                password=password,
                first_name=first_name,
                last_name=last_name,
            )

            # Set permissions based on role
            if role == 'agent':
                user.is_staff = True
                user.save()
            elif role == 'manager':
                user.is_staff = True
                user.is_superuser = True
                user.save()

            login(request, user)
            messages.success(request, f'Account created! Welcome, {first_name}.')
            return redirect('dashboard')
    return render(request, 'tickets/register.html', {'form': form})


def logout_view(request):
    logout(request)
    messages.info(request, 'You have been logged out.')
    return redirect('login')


# ─── Dashboard ───────────────────────────────────────────────────────────

@login_required
def dashboard(request):
    """Main dashboard — adapts based on user role."""
    user = request.user
    context = {'user': user}

    if user.is_superuser:
        # Manager dashboard
        context['role'] = 'manager'
        context['total_tickets'] = Ticket.objects.count()
        context['open_tickets'] = Ticket.objects.filter(status=Ticket.Status.OPEN).count()
        context['in_progress_tickets'] = Ticket.objects.filter(status=Ticket.Status.IN_PROGRESS).count()
        context['blocked_tickets'] = Ticket.objects.filter(status=Ticket.Status.BLOCKED).count()
        context['resolved_tickets'] = Ticket.objects.filter(
            status__in=[Ticket.Status.RESOLVED, Ticket.Status.CLOSED]
        ).count()
        context['unassigned_tickets'] = Ticket.objects.filter(assigned_to__isnull=True).exclude(
            status__in=[Ticket.Status.RESOLVED, Ticket.Status.CLOSED]
        ).count()
        context['recent_tickets'] = Ticket.objects.all()[:10]

        # Agent workload
        agents = User.objects.filter(is_staff=True).annotate(
            ticket_count=Count('assigned_tickets', filter=Q(
                assigned_tickets__status__in=[Ticket.Status.OPEN, Ticket.Status.IN_PROGRESS]
            ))
        )
        context['agents'] = agents

        # Category breakdown
        categories = Category.objects.annotate(
            ticket_count=Count('tickets')
        )
        context['categories'] = categories

    elif user.is_staff:
        # Agent dashboard
        context['role'] = 'agent'
        context['my_tickets'] = Ticket.objects.filter(assigned_to=user).exclude(
            status__in=[Ticket.Status.RESOLVED, Ticket.Status.CLOSED]
        )
        context['my_open'] = context['my_tickets'].filter(status=Ticket.Status.OPEN).count()
        context['my_in_progress'] = context['my_tickets'].filter(status=Ticket.Status.IN_PROGRESS).count()
        context['my_blocked'] = context['my_tickets'].filter(status=Ticket.Status.BLOCKED).count()
        context['unassigned_tickets'] = Ticket.objects.filter(assigned_to__isnull=True).exclude(
            status__in=[Ticket.Status.RESOLVED, Ticket.Status.CLOSED]
        )[:5]
    else:
        # Employee dashboard
        context['role'] = 'employee'
        context['my_tickets'] = Ticket.objects.filter(submitter=user)
        context['open_count'] = context['my_tickets'].filter(status=Ticket.Status.OPEN).count()
        context['in_progress_count'] = context['my_tickets'].filter(
            status=Ticket.Status.IN_PROGRESS
        ).count()
        context['resolved_count'] = context['my_tickets'].filter(
            status__in=[Ticket.Status.RESOLVED, Ticket.Status.CLOSED]
        ).count()

    return render(request, 'tickets/dashboard.html', context)


# ─── Ticket Views ────────────────────────────────────────────────────────

@login_required
def ticket_create(request):
    """Submit a new support request."""
    if request.method == 'POST':
        form = TicketCreateForm(request.POST)
        if form.is_valid():
            ticket = form.save(commit=False)
            ticket.submitter = request.user
            ticket.save()
            ActivityLog.objects.create(
                ticket=ticket, user=request.user,
                action=f'Ticket created with ID {ticket.request_id}'
            )
            messages.success(
                request,
                f'Request submitted! Your ticket ID is {ticket.request_id}. '
                f'A confirmation has been noted.'
            )
            return redirect('ticket_detail', request_id=ticket.request_id)
    else:
        form = TicketCreateForm()
    return render(request, 'tickets/ticket_create.html', {'form': form})


@login_required
def ticket_detail(request, request_id):
    """View ticket details, update status, add notes, assign."""
    ticket = get_object_or_404(Ticket, request_id=request_id)
    user = request.user

    # Permission check: submitter, assigned agent, or manager
    if not (user == ticket.submitter or user == ticket.assigned_to or
            user.is_staff or user.is_superuser):
        messages.error(request, 'You do not have permission to view this ticket.')
        return redirect('dashboard')

    update_form = TicketUpdateForm(instance=ticket) if user.is_staff else None
    assign_form = TicketAssignForm() if user.is_superuser else None
    note_form = NoteForm() if user.is_staff else None

    if request.method == 'POST':
        action = request.POST.get('action')

        if action == 'update_status' and user.is_staff:
            old_status = ticket.get_status_display()
            update_form = TicketUpdateForm(request.POST, instance=ticket)
            if update_form.is_valid():
                update_form.save()
                new_status = ticket.get_status_display()
                ActivityLog.objects.create(
                    ticket=ticket, user=user,
                    action=f'Status changed from "{old_status}" to "{new_status}"'
                )
                messages.success(request, f'Ticket status updated to {new_status}.')
                return redirect('ticket_detail', request_id=request_id)

        elif action == 'assign' and user.is_superuser:
            assign_form = TicketAssignForm(request.POST)
            if assign_form.is_valid():
                agent = assign_form.cleaned_data['assigned_to']
                ticket.assigned_to = agent
                if ticket.status == Ticket.Status.OPEN:
                    ticket.status = Ticket.Status.IN_PROGRESS
                ticket.save()
                ActivityLog.objects.create(
                    ticket=ticket, user=user,
                    action=f'Assigned to {agent.get_full_name() or agent.username}'
                )
                messages.success(request, f'Ticket assigned to {agent.get_full_name()}.')
                return redirect('ticket_detail', request_id=request_id)

        elif action == 'add_note' and user.is_staff:
            note_form = NoteForm(request.POST)
            if note_form.is_valid():
                note = note_form.save(commit=False)
                note.ticket = ticket
                note.author = user
                note.save()
                ActivityLog.objects.create(
                    ticket=ticket, user=user,
                    action='Internal note added'
                )
                messages.success(request, 'Note added.')
                return redirect('ticket_detail', request_id=request_id)

    notes = ticket.notes.all() if user.is_staff else None
    activity = ticket.activity_logs.all()

    return render(request, 'tickets/ticket_detail.html', {
        'ticket': ticket,
        'update_form': update_form,
        'assign_form': assign_form,
        'note_form': note_form,
        'notes': notes,
        'activity': activity,
    })


@login_required
def ticket_list(request):
    """List all tickets (agents/managers) or user's tickets (employees)."""
    user = request.user
    status_filter = request.GET.get('status', '')
    category_filter = request.GET.get('category', '')
    search = request.GET.get('q', '')

    if user.is_superuser:
        tickets = Ticket.objects.all()
    elif user.is_staff:
        tickets = Ticket.objects.filter(
            Q(assigned_to=user) | Q(assigned_to__isnull=True)
        )
    else:
        tickets = Ticket.objects.filter(submitter=user)

    if status_filter:
        tickets = tickets.filter(status=status_filter)
    if category_filter:
        tickets = tickets.filter(category_id=category_filter)
    if search:
        tickets = tickets.filter(
            Q(request_id__icontains=search) |
            Q(title__icontains=search) |
            Q(description__icontains=search)
        )

    categories = Category.objects.all()
    return render(request, 'tickets/ticket_list.html', {
        'tickets': tickets,
        'categories': categories,
        'status_choices': Ticket.Status.choices,
        'current_status': status_filter,
        'current_category': category_filter,
        'search_query': search,
    })


# ─── Knowledge Base ──────────────────────────────────────────────────────

@login_required
def knowledge_base(request):
    """Search resolved/closed tickets as a self-service knowledge base."""
    search = request.GET.get('q', '')
    category_filter = request.GET.get('category', '')

    resolved = Ticket.objects.filter(
        status__in=[Ticket.Status.RESOLVED, Ticket.Status.CLOSED]
    )

    if search:
        resolved = resolved.filter(
            Q(title__icontains=search) |
            Q(description__icontains=search) |
            Q(request_id__icontains=search)
        )
    if category_filter:
        resolved = resolved.filter(category_id=category_filter)

    categories = Category.objects.all()
    return render(request, 'tickets/knowledge_base.html', {
        'tickets': resolved,
        'categories': categories,
        'search_query': search,
        'current_category': category_filter,
    })


# ─── Manager Views ───────────────────────────────────────────────────────

@login_required
def manager_workload(request):
    """Manager view: agent workload overview."""
    if not request.user.is_superuser:
        messages.error(request, 'Access denied.')
        return redirect('dashboard')

    agents = User.objects.filter(is_staff=True).annotate(
        total_assigned=Count('assigned_tickets'),
        open_count=Count('assigned_tickets', filter=Q(assigned_tickets__status=Ticket.Status.OPEN)),
        in_progress_count=Count('assigned_tickets', filter=Q(assigned_tickets__status=Ticket.Status.IN_PROGRESS)),
        blocked_count=Count('assigned_tickets', filter=Q(assigned_tickets__status=Ticket.Status.BLOCKED)),
        resolved_count=Count('assigned_tickets', filter=Q(
            assigned_tickets__status__in=[Ticket.Status.RESOLVED, Ticket.Status.CLOSED]
        )),
    )

    return render(request, 'tickets/manager_workload.html', {'agents': agents})
