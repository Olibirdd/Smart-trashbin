from functools import wraps
from django.shortcuts import render, get_object_or_404, redirect
from bson.objectid import ObjectId
from django.contrib import messages
from django.utils import timezone
from django.contrib.auth.hashers import make_password, check_password
from django.core.paginator import Paginator
from .models import User, ActivityLog, Voucher

# ------------------------------
# Session-based decorators
# ------------------------------
def login_required_session(view_func):
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.session.get('user_id'):
            messages.error(request, "You must log in first.")
            return redirect('login')
        return view_func(request, *args, **kwargs)
    return wrapper

def admin_required_session(view_func):
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if request.session.get('role') != 'admin':
            messages.error(request, "Access denied.")
            return redirect('login')
        return view_func(request, *args, **kwargs)
    return wrapper

# ------------------------------
# Helper to get current user
# ------------------------------
def get_current_user(request):
    user_id = request.session.get('user_id')
    if not user_id:
        return None
    try:
        # Use _id to find the user
        return User.objects.get(_id=ObjectId(user_id))
    except (User.DoesNotExist, Exception):
        return None


# ------------------------------
# Registration
# ------------------------------
def register(request):
    if request.method == "POST":
        username = request.POST.get("username")
        email = request.POST.get("email")
        password = request.POST.get("password")
        confirm = request.POST.get("confirmPassword")
        print(username, email, password, confirm)

        if password != confirm:
            messages.error(request, "Passwords do not match.")
            return redirect("register")

        if User.objects.filter(username=username).exists():
            messages.error(request, "Username already exists.")
            return redirect("register")

        if User.objects.filter(email=email).exists():
            messages.error(request, "Email already exists.")
            return redirect("register")

        User.objects.create(
            username=username,
            email=email,
            password=make_password(password),
            role="user",
            created_at=timezone.now()
        )

        messages.success(request, "Account created successfully! Please log in.")
        return redirect("login")

    return render(request, "registration/register.html")

# ------------------------------
# Login
# ------------------------------
def login_view(request):
    if request.method == "POST":
        username = request.POST.get("username", "").strip()
        password = request.POST.get("password", "").strip()

        if not username or not password:
            messages.error(request, "Please enter both username and password.")
            return redirect("login")

        try:
            # Fetch the user from MongoDB
            user = User.objects.get(username=username)

            # Check hashed password
            if check_password(password, user.password):
                # Set session - use _id instead of id
                request.session['user_id'] = str(user._id)  # Convert ObjectId to string
                request.session['username'] = user.username
                request.session['role'] = user.role

                messages.success(request, f"Welcome {user.username}!")

                # Redirect based on role
                if user.role.lower() == "admin":
                    return redirect("admin_dashboard")
                else:
                    return redirect("dashboard")
            else:
                messages.error(request, "Invalid username or password.")

        except User.DoesNotExist:
            messages.error(request, "Invalid username or password.")

        return redirect("login")  # Always redirect after POST

    # GET request
    return render(request, "registration/login.html")


# ------------------------------
# Logout
# ------------------------------
def logout_view(request):
    request.session.flush()
    messages.success(request, "Logged out successfully.")
    return redirect("login")

# ------------------------------
# Dashboard
# ------------------------------
@login_required_session
def dashboard(request):
    user = get_current_user(request)
    
    # FIX: Use redeemed_by_email instead of redeemed_by
    vouchers = Voucher.objects.filter(redeemed_by_email=user.email).order_by('-created_at')
    transactions = ActivityLog.objects.filter(email=user.email).order_by('-timestamp')

    # Count vouchers based on ActivityLog for this user
    redeemed_vouchers_count = ActivityLog.objects.filter(email=user.email).count()
    total_duration_minutes = redeemed_vouchers_count * 5

    context = {
        'user': user,
        'vouchers': vouchers,
        'transactions': transactions,
        'redeemed_vouchers': redeemed_vouchers_count,
        'total_duration_minutes': total_duration_minutes
    }
    
    return render(request, 'users/dashboard.html', context)



# ------------------------------
# Admin Views
# ------------------------------
@login_required_session
def admin_dashboard(request):
    vouchers = ActivityLog.objects.all().order_by('-timestamp')[:10]
    redeemed_vouchers_count = ActivityLog.objects.filter(action='redeem').count()
    total_users = User.objects.count()
    total_vouchers = ActivityLog.objects.values('voucher_code').count()

    context = {
        'vouchers': vouchers,
        'redeemed_vouchers': redeemed_vouchers_count,
        'total_users': total_users,
        'total_vouchers': total_vouchers
    }
    return render(request, "admin/admin_dashboard.html", context)

@admin_required_session
def admin_users(request):
    all_users = User.objects.all().order_by('-created_at')
    paginator = Paginator(all_users, 10)

    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'admin/admin_users.html', {
        'users': page_obj, 
        'title': 'Users Management - Smart Wi-Fi Bin'
    })

@admin_required_session
def admin_add_user(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        email = request.POST.get('email')
        password = request.POST.get('password')
        confirm_password = request.POST.get('confirmPassword')
        role = request.POST.get('role', 'user')

        # Validate password confirmation
        if password != confirm_password:
            messages.error(request, 'Passwords do not match.')
            return redirect('admin_users')

        if User.objects.filter(username=username).exists():
            messages.error(request, 'Username already exists.')
        elif User.objects.filter(email=email).exists():
            messages.error(request, 'Email already exists.')
        else:
            User.objects.create(
                username=username,
                email=email,
                password=make_password(password),
                role=role,
                created_at=timezone.now()
            )
            messages.success(request, f'User {username} created successfully.')

    return redirect('admin_users')

@admin_required_session
def admin_edit_user(request, user_id):
    try:
        # Use _id field with ObjectId conversion
        user = User.objects.get(_id=ObjectId(user_id))
    except User.DoesNotExist:
        messages.error(request, "User not found.")
        return redirect('admin_users')
    except Exception as e:
        messages.error(request, f"Error: {str(e)}")
        return redirect('admin_users')

    if request.method == 'POST':
        new_username = request.POST.get('username')
        email = request.POST.get('email')
        password = request.POST.get('password')
        role = request.POST.get('role', 'user')

        # More strict validation
        if new_username != user.username:
            if User.objects.filter(username=new_username).exists():
                messages.error(request, f'Username "{new_username}" already exists.')
                return redirect('admin_users')
        
        # Use _id in exclude clause
        if User.objects.filter(email=email).exclude(_id=ObjectId(user_id)).exists():
            messages.error(request, 'Email already exists.')
            return redirect('admin_users')

        user.username = new_username
        user.email = email
        user.role = role
        if password:
            user.password = make_password(password)
        user.save()
        messages.success(request, f'User {new_username} updated successfully.')

    return redirect('admin_users')

@admin_required_session
def admin_delete_user(request, user_id):
    current_user = get_current_user(request)
    print("Current user:", current_user.username if current_user else "None")
    print("User to delete ID:", user_id)

    try:
        # Use _id field with ObjectId conversion
        user = User.objects.get(_id=ObjectId(user_id))
    except User.DoesNotExist:
        messages.error(request, "User not found.")
        return redirect('admin_users')
    except Exception as e:
        print(f"Error: {e}")
        messages.error(request, "Error finding user.")
        return redirect('admin_users')

    # Debug info
    print("Found user:", user.username)
    print("Found user _id:", user._id)

    # Prevent deleting yourself
    if str(user._id) == str(current_user._id):
        messages.error(request, "You cannot delete your own account.")
        return redirect('admin_users')

    username = user.username
    user.delete()
    messages.success(request, f"User {username} deleted successfully.")
    return redirect('admin_users')

@admin_required_session
def admin_edit_user(request, user_id):
    try:
        # Use _id field with ObjectId conversion
        user = User.objects.get(_id=ObjectId(user_id))
    except User.DoesNotExist:
        messages.error(request, "User not found.")
        return redirect('admin_users')
    except Exception as e:
        messages.error(request, f"Error: {str(e)}")
        return redirect('admin_users')

    if request.method == 'POST':
        new_username = request.POST.get('username')
        email = request.POST.get('email')
        password = request.POST.get('password')
        role = request.POST.get('role', 'user')

        # More strict validation
        if new_username != user.username:
            if User.objects.filter(username=new_username).exists():
                messages.error(request, f'Username "{new_username}" already exists.')
                return redirect('admin_users')
        
        if User.objects.filter(email=email).exclude(_id=ObjectId(user_id)).exists():
            messages.error(request, 'Email already exists.')
            return redirect('admin_users')

        user.username = new_username
        user.email = email
        user.role = role
        if password:
            user.password = make_password(password)
        user.save()
        messages.success(request, f'User {new_username} updated successfully.')

    return redirect('admin_users')


@admin_required_session
def admin_vouchers(request):
    vouchers = Voucher.objects.all().order_by('-created_at')
    paginator = Paginator(vouchers, 10)

    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    return render(request, 'admin/admin_vouchers.html', {
        'vouchers': page_obj,
        'title': 'Vouchers Management - Smart Wi-Fi Bin'
    })

@admin_required_session
def admin_add_voucher(request):
    if request.method == 'POST':
        import random, string

        code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
        duration_minutes = request.POST.get('duration_minutes')

        while Voucher.objects.filter(code=code).exists():
            code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))

        Voucher.objects.create(code=code, duration_minutes=duration_minutes)
        messages.success(request, f'Voucher {code} created successfully.')

    return redirect('admin_vouchers')

@admin_required_session
def admin_delete_voucher(request, voucher_id):
    voucher = Voucher.objects.get(_id=ObjectId(voucher_id))
    code = voucher.voucher_code
    voucher.delete()
    messages.success(request, f'Voucher {code} deleted successfully.')
    return redirect('admin_vouchers')

