from agent_base.processors import StandardWebhookProcessor
from django.utils import timezone
from django.conf import settings
from .models import SocialAdsGeneratorRequest, SocialAdsGeneratorResponse
import json


class SocialAdsGeneratorProcessor(StandardWebhookProcessor):
    """Webhook processor for Social Ads Generator agent"""
    
    agent_slug = 'social-ads-generator'
    webhook_url = settings.N8N_WEBHOOK_SOCIAL_ADS
    agent_id = 'social-ads'
    
    def prepare_message_text(self, **kwargs):
        """Prepare detailed social ads prompt for N8N webhook"""
        request_obj = kwargs.get('request_obj')
        if not request_obj:
            return "Create a social media advertisement"
        
        # Sanitize and validate description content
        sanitized_description = self.sanitize_user_input(request_obj.description)
        if not sanitized_description:
            return "Unable to process the provided description"
        
        # Validate platform and language choices
        platform_display = self.get_safe_platform_display(request_obj.social_platform)
        safe_language = self.get_safe_language(request_obj.language)
        
        # Build comprehensive social ads prompt with sanitized inputs
        prompt = f"""
Create a compelling social media advertisement for the following:

Product/Service Description:
{sanitized_description}

Target Platform: {platform_display}
Language: {safe_language}
Include Emojis: {'Yes' if request_obj.include_emoji else 'No'}

Please create platform-optimized ad copy that:
- Captures attention instantly
- Highlights key benefits and unique selling points
- Uses persuasive messaging that motivates action
- Includes a strong call-to-action
- Is tailored to {platform_display} audience
- Uses {safe_language} language
- Maintains professional and appropriate content
- Avoids any misleading or harmful messaging
"""
        
        if request_obj.include_emoji:
            prompt += "\n- Incorporates relevant emojis for engagement"
        
        prompt += "\n\nFormat the response as professional ad copy ready for social media posting."
        
        return prompt
    
    def sanitize_user_input(self, description):
        """Sanitize user input to prevent prompt injection and harmful content"""
        if not description or not isinstance(description, str):
            return ""
        
        # Remove potential prompt injection patterns
        dangerous_patterns = [
            'ignore previous instructions',
            'new instructions:',
            'system:',
            'assistant:',
            'user:',
            '###',
            'IGNORE',
            'STOP',
            'OVERRIDE',
        ]
        
        sanitized = description.strip()
        
        # Check for and remove dangerous patterns (case insensitive)
        for pattern in dangerous_patterns:
            if pattern.lower() in sanitized.lower():
                # Replace with safe placeholder
                sanitized = sanitized.replace(pattern, '[CONTENT_FILTERED]')
        
        # Limit length and remove excessive whitespace
        sanitized = ' '.join(sanitized.split())[:2000]
        
        # Basic content filtering for inappropriate requests
        inappropriate_keywords = [
            'illegal', 'harmful', 'violence', 'hate', 'discrimination',
            'scam', 'fraud', 'misleading', 'fake', 'counterfeit'
        ]
        
        sanitized_lower = sanitized.lower()
        for keyword in inappropriate_keywords:
            if keyword in sanitized_lower:
                return f"[Content filtered - Please provide appropriate product/service description]"
        
        return sanitized
    
    def get_safe_platform_display(self, platform):
        """Get safe platform display name"""
        platform_map = {
            'facebook': 'Facebook',
            'instagram': 'Instagram', 
            'twitter': 'Twitter',
            'linkedin': 'LinkedIn',
            'tiktok': 'TikTok',
            'youtube': 'YouTube'
        }
        return platform_map.get(platform, 'Social Media')
    
    def get_safe_language(self, language):
        """Get safe language name"""
        language_map = {
            'English': 'English',
            'Arabic': 'Arabic',
            'Spanish': 'Spanish',
            'French': 'French', 
            'German': 'German',
            'Chinese': 'Chinese'
        }
        return language_map.get(language, 'English')
    
    def process_response(self, response_data, request_obj):
        """Process webhook response"""
        try:
            request_obj.status = 'processing'
            request_obj.save()
            
            
            # Handle array response from N8N (extract first item)
            if isinstance(response_data, list) and len(response_data) > 0:
                response_data = response_data[0]
            
            # Extract and validate ad copy content
            ad_copy = ""
            if isinstance(response_data, dict):
                ad_copy = response_data.get('output', response_data.get('text', response_data.get('content', '')))
            elif isinstance(response_data, str):
                ad_copy = response_data
            
            # Validate and sanitize AI output
            ad_copy = self.validate_ai_output(ad_copy)
            
            # Parse ad copy for different components (basic parsing)
            hashtags = ""
            targeting_suggestions = ""
            formatted_ad = ad_copy
            
            # Simple extraction of hashtags if present
            if '#' in ad_copy:
                lines = ad_copy.split('\n')
                hashtag_lines = [line for line in lines if line.strip().startswith('#')]
                if hashtag_lines:
                    hashtags = ' '.join(hashtag_lines)
            
            # Determine success based on response
            success = response_data.get('success', False) if isinstance(response_data, dict) else bool(ad_copy.strip())
            
            # Create response object
            response_obj = SocialAdsGeneratorResponse.objects.create(
                request=request_obj,
                success=success,
                processing_time=response_data.get('processing_time', 0) if isinstance(response_data, dict) else 0,
                ad_copy=ad_copy,
                hashtags=hashtags,
                targeting_suggestions=targeting_suggestions,
                formatted_ad=formatted_ad,
                raw_response=response_data if isinstance(response_data, dict) else {'content': response_data}
            )
            
            # Only deduct wallet balance after successful processing
            if success:
                request_obj.user.deduct_balance(
                    request_obj.cost,
                    f"Social Ads Generator - {request_obj.get_social_platform_display()} ad for {request_obj.description[:50]}...",
                    'social-ads-generator'
                )
                print(f"{self.agent_slug}: Wallet deducted {request_obj.cost} AED for successful processing")
            
            # Update request as completed
            request_obj.status = 'completed' if success else 'failed'
            request_obj.processed_at = timezone.now()
            request_obj.save()
            
            return response_obj
            
        except Exception as e:
            # Handle error
            request_obj.status = 'failed'
            request_obj.save()
            
            # Create error response
            SocialAdsGeneratorResponse.objects.create(
                request=request_obj,
                success=False,
                error_message=str(e),
                processing_time=0
            )
            
            raise Exception(f"Failed to process Social Ads Generator response: {e}")
    
    def validate_ai_output(self, content):
        """Validate and sanitize AI-generated content"""
        if not content or not isinstance(content, str):
            return "Error: No content generated"
        
        # Limit output length for security
        content = content[:10000]
        
        # Remove any potential malicious content
        malicious_patterns = [
            '<script',
            'javascript:',
            'onclick=',
            'onerror=',
            'onload=',
            'eval(',
            'document.cookie',
            'window.location'
        ]
        
        for pattern in malicious_patterns:
            if pattern.lower() in content.lower():
                return "Content filtered for security reasons"
        
        # Basic content quality check
        if len(content.strip()) < 10:
            return "Generated content too short - please try again"
        
        return content.strip()