from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.core.mail import send_mail
from django.conf import settings
from django_ratelimit.decorators import ratelimit
from django_ratelimit import UNSAFE
from agent_base.models import BaseAgent
from .models import ContactSubmission
from django.db import connection
import logging
import re
import time

logger = logging.getLogger(__name__)
@ratelimit(key='ip', rate='60/m', method='GET', block=False)
def homepage_view(request):
    """Homepage view with agent system and rate limiting"""
    # Check if rate limited
    if getattr(request, 'limited', False):
        logger.warning(f"Homepage rate limit exceeded for IP {request.META.get('REMOTE_ADDR')}")
        messages.warning(request, 'Too many requests. Please wait a moment before refreshing.')
    
    try:
        # Get featured agents for homepage with safe querying
        featured_agents = BaseAgent.objects.filter(is_active=True).order_by('name')[:6]
        
        context = {
            'user_balance': request.user.wallet_balance if request.user.is_authenticated else 0,
            'featured_agents': featured_agents,
        }
        
        return render(request, 'core/homepage.html', context)
        
    except Exception as e:
        logger.error(f"Homepage view error: {e}")
        messages.error(request, 'Unable to load homepage. Please try again.')
        return render(request, 'core/homepage.html', {'featured_agents': [], 'user_balance': 0})
@ratelimit(key='ip', rate='60/m', method='GET', block=False)
def pricing_view(request):
    """Pricing page for non-logged-in users with rate limiting"""
    # Check if rate limited
    if getattr(request, 'limited', False):
        logger.warning(f"Pricing page rate limit exceeded for IP {request.META.get('REMOTE_ADDR')}")
        messages.warning(request, 'Too many requests. Please wait a moment before refreshing.')
    
    # If user is already logged in, redirect to wallet top-up
    if request.user.is_authenticated:
        return redirect('wallet:wallet_topup')
    
    try:
        # Get sample agents to show pricing context with safe querying
        sample_agents = BaseAgent.objects.filter(is_active=True).order_by('name')[:4]
        
        context = {
            'sample_agents': sample_agents,
        }
        
        return render(request, 'core/pricing.html', context)
        
    except Exception as e:
        logger.error(f"Pricing view error: {e}")
        messages.error(request, 'Unable to load pricing page. Please try again.')
        return render(request, 'core/pricing.html', {'sample_agents': []})


@ratelimit(key='ip', rate='60/m', method='GET', block=False)
def digital_branding_view(request):
    """Digital branding services page with rate limiting"""
    # Check if rate limited
    if getattr(request, 'limited', False):
        logger.warning(f"Digital branding page rate limit exceeded for IP {request.META.get('REMOTE_ADDR')}")
        messages.warning(request, 'Too many requests. Please wait a moment before refreshing.')
    
    try:
        context = {
            'user_balance': request.user.wallet_balance if request.user.is_authenticated else 0,
        }
        
        return render(request, 'core/digital_branding.html', context)
        
    except Exception as e:
        logger.error(f"Digital branding view error: {e}")
        messages.error(request, 'Unable to load digital branding page. Please try again.')
        return render(request, 'core/digital_branding.html', {'user_balance': 0})


def validate_contact_input(name, email, message, company=""):
    """Validate and sanitize contact form input"""
    errors = []
    
    # Name validation
    if not name or len(name.strip()) < 2:
        errors.append("Name must be at least 2 characters long")
    elif len(name) > 100:
        errors.append("Name must be less than 100 characters")
    elif not re.match(r'^[a-zA-Z\s\-\.\']+$', name):
        errors.append("Name contains invalid characters")
    
    # Email validation (Django handles basic format)
    if not email or len(email) > 254:
        errors.append("Please provide a valid email address")
    
    # Message validation
    if not message or len(message.strip()) < 10:
        errors.append("Message must be at least 10 characters long")
    elif len(message) > 1000:
        errors.append("Message must be less than 1000 characters")
    
    # Company validation (optional)
    if company and len(company) > 100:
        errors.append("Company name must be less than 100 characters")
    
    # Check for potential spam indicators
    spam_keywords = ['viagra', 'casino', 'lottery', 'winner', 'congratulations', 'million dollars']
    message_lower = message.lower()
    if any(keyword in message_lower for keyword in spam_keywords):
        errors.append("Message contains prohibited content")
    
    return errors


def send_contact_notification(submission):
    """Send notification email for new contact submission"""
    try:
        subject = f'New Contact Form Submission from {submission.name}'
        message = f'''
New contact form submission received:

Name: {submission.name}
Email: {submission.email}
Company: {submission.company or 'Not provided'}
IP Address: {submission.ip_address}
Submitted: {submission.created_at.strftime('%Y-%m-%d %H:%M:%S UTC')}

Message:
{submission.message}

---
This is an automated notification from Quantum Tasks AI contact form.
        '''
        
        # Send to admin email
        admin_email = getattr(settings, 'ADMIN_EMAIL', 'abhay@quantumtaskai.com')
        
        send_mail(
            subject=subject,
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[admin_email],
            fail_silently=False,
        )
        
        logger.info(f"Contact notification sent for submission from {submission.email}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to send contact notification: {e}")
        return False


@ratelimit(key='ip', rate='3/m', method='POST', block=False)
def contact_form_view(request):
    """Handle contact form submission with security and rate limiting"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Method not allowed'}, status=405)
    
    # Check if rate limited
    if getattr(request, 'limited', False):
        logger.warning(f"Contact form rate limit exceeded for IP {request.META.get('REMOTE_ADDR')}")
        return JsonResponse({
            'success': False, 
            'error': 'Too many contact form submissions. Please try again in a few minutes.'
        }, status=429)
    
    try:
        # Get form data
        name = request.POST.get('name', '').strip()
        email = request.POST.get('email', '').strip()
        company = request.POST.get('company', '').strip()
        message = request.POST.get('message', '').strip()
        
        # Validate input
        validation_errors = validate_contact_input(name, email, message, company)
        if validation_errors:
            logger.warning(f"Contact form validation failed from IP {request.META.get('REMOTE_ADDR')}: {validation_errors}")
            return JsonResponse({
                'success': False,
                'error': 'Please correct the following errors: ' + ', '.join(validation_errors)
            }, status=400)
        
        # Check for duplicate submissions (same email/IP in last hour)
        from django.utils import timezone
        from datetime import timedelta
        
        recent_submission = ContactSubmission.objects.filter(
            ip_address=request.META.get('REMOTE_ADDR'),
            created_at__gte=timezone.now() - timedelta(hours=1)
        ).first()
        
        if recent_submission:
            logger.warning(f"Duplicate contact submission attempted from IP {request.META.get('REMOTE_ADDR')}")
            return JsonResponse({
                'success': False,
                'error': 'You have already submitted a contact form recently. Please wait before submitting again.'
            }, status=429)
        
        # Create submission
        submission = ContactSubmission.objects.create(
            name=name,
            email=email,
            company=company,
            message=message,
            ip_address=request.META.get('REMOTE_ADDR', ''),
            user_agent=request.META.get('HTTP_USER_AGENT', '')[:500]  # Truncate user agent
        )
        
        # Send notification email
        email_sent = send_contact_notification(submission)
        
        logger.info(f"Contact form submitted successfully from {email} (IP: {request.META.get('REMOTE_ADDR')})")
        
        return JsonResponse({
            'success': True,
            'message': 'Thank you for your message! We will get back to you within 24 hours.',
            'email_sent': email_sent
        })
        
    except Exception as e:
        logger.error(f"Contact form processing error: {e}")
        return JsonResponse({
            'success': False,
            'error': 'Unable to process your message at this time. Please try again later.'
        }, status=500)


@ratelimit(key='ip', rate='60/m', method='GET', block=False)
def health_check_view(request):
    """Simplified health check endpoint - no database dependency for startup"""
    start_time = time.time()
    health_data = {
        'status': 'healthy',
        'timestamp': int(time.time()),
        'version': '1.0',
        'app': 'quantum-tasks-ai',
        'checks': {}
    }
    
    # Basic application status - always healthy if we reach this point
    health_data['checks']['application'] = {
        'status': 'healthy',
        'django_ready': True,
        'server_running': True
    }
    
    # Try database connection but don't fail health check if it's down
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            health_data['checks']['database'] = {
                'status': 'healthy',
                'response_time_ms': round((time.time() - start_time) * 1000, 2)
            }
            
        # If database is working, try to get agent count
        try:
            agent_count = BaseAgent.objects.filter(is_active=True).count()
            health_data['checks']['agents'] = {
                'status': 'healthy',
                'active_count': agent_count
            }
        except Exception as e:
            health_data['checks']['agents'] = {
                'status': 'warning',
                'error': 'Could not query agents',
                'message': str(e)[:100]
            }
            
    except Exception as e:
        # Database connection failed - log it but don't fail health check
        health_data['checks']['database'] = {
            'status': 'warning',
            'error': 'Database connection failed',
            'message': str(e)[:100]
        }
        health_data['checks']['agents'] = {
            'status': 'skipped',
            'reason': 'database_unavailable'
        }
    
    # Environment check
    health_data['checks']['environment'] = {
        'status': 'healthy',
        'debug_mode': getattr(settings, 'DEBUG', True),
        'secret_key_configured': bool(getattr(settings, 'SECRET_KEY', None))
    }
    
    # Overall response time
    health_data['response_time_ms'] = round((time.time() - start_time) * 1000, 2)
    
    # Always return 200 - we're healthy if Django is running
    return JsonResponse(health_data, status=200)
