from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
import logging
from django.contrib import messages
from django.http import JsonResponse
from agent_base.models import BaseAgent
from .models import SocialAdsGeneratorRequest, SocialAdsGeneratorResponse
from .processor import SocialAdsGeneratorProcessor


@login_required
def social_ads_generator_detail(request):
    """Detail page for Social Ads Generator agent"""
    try:
        agent = BaseAgent.objects.get(slug='social-ads-generator')
    except BaseAgent.DoesNotExist:
        messages.error(request, 'Social Ads Generator agent not found.')
        return redirect('core:homepage')
    
    if request.method == 'POST':
        # Handle AJAX requests
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            if not request.user.is_authenticated:
                return JsonResponse({'error': 'Authentication required'}, status=401)
            
            # Check wallet balance
            if not request.user.has_sufficient_balance(agent.price):
                return JsonResponse({'error': 'Insufficient wallet balance'}, status=400)
            
            try:
                # Validate and sanitize input data
                description = request.POST.get('description', '').strip()
                social_platform = request.POST.get('social_platform', 'facebook')
                include_emoji = request.POST.get('include_emoji') == 'yes'
                language = request.POST.get('language', 'English')
                
                # Server-side validation
                validation_errors = []
                
                # Validate description
                if not description:
                    validation_errors.append('Description is required')
                elif len(description) < 10:
                    validation_errors.append('Description must be at least 10 characters long')
                elif len(description) > 5000:
                    validation_errors.append('Description must be less than 5000 characters')
                
                # Validate social platform
                valid_platforms = ['facebook', 'instagram', 'twitter', 'linkedin', 'tiktok', 'youtube']
                if social_platform not in valid_platforms:
                    validation_errors.append('Invalid social media platform selected')
                
                # Validate language
                valid_languages = ['English', 'Arabic', 'Spanish', 'French', 'German', 'Chinese']
                if language not in valid_languages:
                    validation_errors.append('Invalid language selected')
                
                # Return validation errors if any
                if validation_errors:
                    return JsonResponse({'error': '; '.join(validation_errors)}, status=400)
                
                # Create request object (no wallet deduction yet)
                agent_request = SocialAdsGeneratorRequest.objects.create(
                    user=request.user,
                    agent=agent,
                    cost=agent.price,
                    description=description,
                    social_platform=social_platform,
                    include_emoji=include_emoji,
                    language=language,
                )
                
                # Process request
                processor = SocialAdsGeneratorProcessor()
                result = processor.process_request(
                    request_obj=agent_request,
                    user_id=request.user.id,
                )
                
                # Refresh user from database to get updated wallet balance
                request.user.refresh_from_db()
                
                return JsonResponse({
                    'success': True,
                    'request_id': str(agent_request.id),
                    'message': 'Social ads generation started',
                    'wallet_balance': float(request.user.wallet_balance)
                })
                
            except Exception as e:
                # Log detailed error for debugging (server-side only)
                logger = logging.getLogger(__name__)
                logger.error(f"Social ads generation failed for user {request.user.id}: {str(e)}", exc_info=True)
                
                # Return generic error message to client
                return JsonResponse({'error': 'Processing failed. Please try again later.'}, status=500)
        
        # Regular form submission (redirect to avoid resubmission)
        return redirect('social_ads_generator:detail')
    
    # GET request - show form
    context = {
        'agent': agent,
    }
    return render(request, 'social_ads_generator/detail.html', context)




@login_required
def social_ads_generator_status(request, request_id):
    """Get status for a specific request (for polling)"""
    try:
        agent_request = SocialAdsGeneratorRequest.objects.get(
            id=request_id,
            user=request.user
        )
        
        if hasattr(agent_request, 'response'):
            response = agent_request.response
            # Refresh user to get current wallet balance
            request.user.refresh_from_db()
            
            ad_copy = getattr(response, 'ad_copy', None)
            raw_response = getattr(response, 'raw_response', None)
            
            
            json_response = {
                'success': response.success,
                'status': agent_request.status,
                'content': ad_copy,
                'ad_copy_content': ad_copy,
                'hashtags': getattr(response, 'hashtags', None),
                'targeting_suggestions': getattr(response, 'targeting_suggestions', None),
                'formatted_ad': getattr(response, 'formatted_ad', None),
                'raw_response': raw_response,
                'processing_time': float(response.processing_time) if response.processing_time else None,
                'error_message': response.error_message,
                'wallet_balance': float(request.user.wallet_balance)
            }
            
            return JsonResponse(json_response)
        else:
            return JsonResponse({
                'success': False,
                'status': agent_request.status,
                'message': 'Processing in progress...'
            })
            
    except SocialAdsGeneratorRequest.DoesNotExist:
        return JsonResponse({'error': 'Request not found'}, status=404)
    except Exception as e:
        # Log detailed error for debugging (server-side only)
        logger = logging.getLogger(__name__)
        logger.error(f"Social ads status check failed for request {request_id}: {str(e)}", exc_info=True)
        
        # Return generic error message to client
        return JsonResponse({'error': 'Unable to retrieve status. Please try again later.'}, status=500)