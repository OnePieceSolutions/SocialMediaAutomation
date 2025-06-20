from collections import defaultdict
from datetime import datetime, timezone
from django.utils.safestring import mark_safe
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.views import View
from django.contrib import messages
from .utils import PostSocialMedia, generate_with_openai, get_credentials
from .models import CampaignPost, Client, Post, ScheduledPost, UserCredential, Campaign
from content_creator.prompt_generator import SocialMediaPromptGenerator
from django.http import JsonResponse, HttpResponseBadRequest, HttpResponse
from django import forms
from django.contrib.auth.models import User
import requests
import json
from django.utils.dateparse import parse_datetime, parse_date
from django.utils.timezone import make_aware, is_naive
import secrets, hashlib, base64
from requests_oauthlib import OAuth1
from urllib.parse import quote

class CustomUserCreationForm(UserCreationForm):
    email = forms.EmailField(required=True)

    class Meta:
        model = User
        fields = ("username", "email", "password1", "password2")

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data["email"]
        if commit:
            user.save()
        return user

class SignupView(View):
    template_name = 'clientManagement/signup.html'

    def get(self, request):
        return render(request, self.template_name)

    def post(self, request):
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.email = request.POST.get('email', '')
            user.save()
            try:
                Client.objects.create(
                    user=user,
                    email_id=user.email,
                    company_name=request.POST.get('company_name', ''),
                    phone_number=request.POST.get('phone', ''),
                    address=request.POST.get('address', ''),
                    company_type=request.POST.get('companyType', ''),
                    target_audience=request.POST.get('targetAudience', ''),
                    platforms=request.POST.get('platform', ''),
                )
                login(request, user)
                messages.success(request, 'Signup successful!')
                return redirect('clientManagement:home')
            except Exception as e:
                messages.error(request, f'Signup failed: {str(e)}')
                return redirect('clientManagement:signup')
        return render(request, self.template_name, {'form': form})

class SigninView(View):
    template_name = 'clientManagement/signin.html'

    def get(self, request):
        return render(request, self.template_name, {'form': AuthenticationForm()})

    def post(self, request):
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            login(request, form.get_user())
            messages.success(request, 'Signin successful!')
            return redirect('clientManagement:home')
        return render(request, self.template_name, {'form': form})

class LogoutView(View):
    def get(self, request):
        logout(request)
        messages.success(request, 'Logged out successfully!')
        return redirect('clientManagement:signin')

class DashboardView(View):
    template_name = 'clientManagement/dashboard.html'

    def get(self, request):
        user = getattr(request.user, 'client', None)

        admin_data = {
            'Email': user.email_id if user else None,
            'Company Name': user.company_name if user else None,
            'Phone Number': user.phone_number if user else None,
            'Address': user.address if user else None
        }

        posts = Post.objects.filter(user=request.user).order_by('-created_on')
        scheduled = ScheduledPost.objects.filter(user=request.user)

        recent_posts = posts[:3]

        context = {
            'admin_data': admin_data,
            'post_count': posts.count(),
            'scheduled_count': scheduled.count(),
            'recent_posts': recent_posts,
            "publish_count": 0
        }
        return render(request, self.template_name, context)

class SettingsView(View):
    template_name = 'clientManagement/settings.html'

    def get(self, request):
        return render(request, self.template_name)

class MediaView(View):
    template_name = 'clientManagement/mediaManagement.html'

    def get(self, request):
        credentials = UserCredential.objects.filter(user=request.user)
        for cred in credentials:
            cred.api_json = mark_safe(json.dumps(cred.api_data or {}))
        credential_choices = UserCredential.PLATFORM_CHOICES
        existing_platforms = credentials.values_list('platform', flat=True)
        return render(request, self.template_name, {
            'credentials': credentials,
            'credential_choices': credential_choices,
            'existing_platforms': list(existing_platforms),
        })

class HomeView(View):
    template_name = 'clientManagement/home.html'

    def get(self, request):
        user = Client.objects.filter(user=request.user).first()
        user_data = {
            'username': request.user,
            'email': user.email_id,
            'companyName': user.company_name,
            'phone': user.phone_number,
            'address': user.address,
            'companyType': user.company_type,
            'targetAudience': user.target_audience,
            'platform': user.platforms
        }
        return render(request, self.template_name, {'user_data': user_data})

class LandingPageView(View):
    template_name = 'clientManagement/landing_page.html'

    def get(self, request):
        return render(request, self.template_name)

class PricingView(View):
    template_name = 'clientManagement/pricing.html'

    def get(self, request):
        return render(request, self.template_name)

class GeneratePromptsView(View):
    def get(self, request):
        user = Client.objects.filter(user=request.user).first()

        if not user:
            return redirect('clientManagement:signup')

        data = {
            "company_name": user.company_name,
            "company_type": user.company_type,
            "brand_tone": user.brand_tone,
            "target_audience": user.target_audience,
            "top_services_or_products": user.top_services_or_products,
            "platforms": user.platforms,
            "offers_or_promotions": user.offers_or_promotions,
        }

        generator = SocialMediaPromptGenerator(data)
        prompts = generator.generate_all()

        return JsonResponse({
            "text_prompt": prompts[0].get("text_prompt", ""),
            "image_prompt": prompts[0].get("image_prompt", "")
        })

class EditImageView(View):
    template_name = "clientManagement/edit_image.html"

    def get(self, request, post_id):
        post = get_object_or_404(Post, id=post_id, user=request.user)
        img_url = post.image_file.url if post.image_file else post.image_url
        print(img_url)
        return render(request, self.template_name, {
            "post": post,
            "image_url": img_url,
        })

def proxy_image(request):
    raw_url = request.GET.get('url')
    if raw_url.startswith('/'):
        raw_url = request.build_absolute_uri(raw_url)
    if not raw_url.startswith(('http://', 'https://')):
        return HttpResponseBadRequest("Invalid image URL")
    if not raw_url:
        return HttpResponseBadRequest("Missing image URL")
    try:
        response = requests.get(raw_url, stream=True)
        if response.status_code == 200:
            return HttpResponse(response.content, content_type=response.headers.get('Content-Type', 'image/png'))
        else:
            return HttpResponse(f"Failed to fetch image: {response.status_code}", status=502)
    except Exception as e:
        return HttpResponse(f"Error: {str(e)}", status=500)

class SingleImageView(View):
    template_name = "clientManagement/gallery.html"

    def post(self, request):
        text_prompt = request.POST.get("text_prompt", "")
        image_prompt = request.POST.get("image_prompt", "")

        # 1) Generate remote URL from OpenAI
        default_url = "/static/404.jpg"
        image_url = default_url
        if image_prompt:
            text_generated, generated_url = generate_with_openai(text_prompt,image_prompt)
            if generated_url:
                image_url = generated_url
            else:
                messages.warning(request, "Failed to generate image. Using default fallback.")

        post = Post.objects.create(
            user=request.user,
            text_prompt=text_prompt,
            image_prompt=image_prompt,
            image_url=image_url,
            text=text_generated if text_generated else "",
            platform="manual"
        )

        return render(request, self.template_name, {
            "post_id": post.id,
            "text_prompt": text_prompt,
            "image_prompt": image_prompt,
            "image": image_url,
            "text": text_generated if text_generated else "",
        })

REDIRECT_URI = "http://127.0.0.1:8000/twitter/callback/"
SCOPES = "tweet.read tweet.write users.read offline.access"
AUTH_URL = "https://twitter.com/i/oauth2/authorize"
TOKEN_URL = "https://api.twitter.com/2/oauth2/token"

class TwitterLogin(View):
    def get(self, request):
        verifier = secrets.token_urlsafe(100)[:128]
        request.session["pkce_verifier"] = verifier
        challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).decode().strip("=")
        CLIENT_ID = request.GET.get("client_id")
        if not CLIENT_ID:
            return JsonResponse({"success": False, "message": "Missing client_id in query params"})
        request.session["client_id"] = CLIENT_ID
        url = (
            f"{AUTH_URL}?response_type=code"
            f"&client_id={CLIENT_ID}"
            f"&redirect_uri={quote(REDIRECT_URI)}"
            f"&scope={quote(SCOPES)}"
            f"&state=twitter"
            f"&code_challenge={challenge}"
            f"&code_challenge_method=S256"
        )
        return redirect(url)

class TwitterCallback(View):
    def get(self, request):
        code = request.GET.get("code")
        verifier = request.session.get("pkce_verifier")

        if not code or not verifier:
            return JsonResponse({
                "success": False,
                "message": "Missing authorization code or verifier."
            })
        
        CLIENT_ID = request.session["client_id"]

        data = {
            "grant_type": "authorization_code",
            "client_id": CLIENT_ID,
            "code": code,
            "redirect_uri": REDIRECT_URI,
            "code_verifier": verifier,
        }

        headers = {
            "Content-Type": "application/x-www-form-urlencoded"
        }

        try:
            response = requests.post(TOKEN_URL, data=data, headers=headers)
            result = response.json()
        except requests.RequestException as e:
            return JsonResponse({
                "success": False,
                "message": f"Request error: {str(e)}"
            })

        if response.status_code != 200:
            return JsonResponse({
                "success": False,
                "message": result.get("error_description", response.text)
            })
        access_token = result.get("access_token")
        refresh_token = result.get("refresh_token")
        if not access_token:
            return JsonResponse({
                "success": False,
                "message": "Access token not found in response."
            })
        request.session["x_access_token"] = access_token
        request.session["x_refresh_token"] = refresh_token
        cred_obj = get_credentials(request.user, "twitter")
        if cred_obj:
            api_data = cred_obj.api_data or {}
            api_data.update({
                "bearer_token": access_token,
                "refresh_token": refresh_token
            })
            cred_obj.api_data = api_data
            cred_obj.save()
        else:
            return JsonResponse({
                "success": False,
                "message": "No credentials object found for this user."
            })

        return redirect("clientManagement:media")

class ContentLibraryView(View):
    template_name = 'clientManagement/content_library.html'

    def get(self, request):
        posts = Post.objects.filter(user=request.user).order_by('-created_on')
        return render(request, self.template_name, {
            'posts': posts,
        })
    
    def post(self, request):
        post_id = request.POST.get("post_id")
        post = get_object_or_404(Post, id=post_id, user=request.user)
        if post.image_file:
            post.image_file.delete(save=False)
        post.delete()
        messages.success(request, "Post deleted successfully.")
        return redirect('clientManagement:content_library')

class SchedulingView(View):
    template_name = 'clientManagement/scheduling.html'

    def get(self, request):
        posts = Post.objects.filter(user=request.user)
        now = timezone.now()
        ScheduledPost.objects.filter(user=request.user, scheduled_time__lt=now).delete()
        scheduled_posts = ScheduledPost.objects.filter(
            user=request.user,
            scheduled_time__gte=now
        ).select_related('post').order_by('-scheduled_time')

        return render(request, self.template_name, {
            'posts': posts,
            'scheduled_posts': scheduled_posts,
        })

class ScheduleSubmitView(View):
    def post(self, request):
        post_id = request.POST.get("post_id")
        schedule_time_str = request.POST.get("schedule_time_utc")
        platform = request.POST.get("platform", "manual")
        post_immediately = request.POST.get("post_immediately", "false") == "true"

        post = get_object_or_404(Post, id=post_id, user=request.user)

        if schedule_time_str:
            schedule_time = parse_datetime(schedule_time_str)
            if schedule_time and is_naive(schedule_time):
                schedule_time = make_aware(schedule_time)
        else:
            schedule_time = timezone.now()

        media = PostSocialMedia(post, schedule_time, post_immediately)
        if platform == "facebook":
            result = media.post_to_facebook()
            post.platform = "facebook"
        elif platform == "instagram":
            result = media.post_to_instagram()
            post.platform = "instagram"
        elif platform =="twitter":
            if not request.session.get("twitter_access_token"):
                return redirect("/twitter/login")
            result = media.post_to_twitter()
            post.platform = "twitter"
        elif platform == "reddit":
            result = media.post_to_reddit()
            post.platform = "reddit"

        if result.get("success"):
            post_url = result.get("post_url")
            post.external_post = post_url
            post.save()
            print("Post URL:", post_url)
        else:
            print("Post failed:", result.get("message"))

        ScheduledPost.objects.create(
            post=post,
            scheduled_time=schedule_time,
            platform=platform
        )

        messages.success(request, "Post scheduled successfully!")
        return redirect('clientManagement:schedule')

class ScheduleUpdateView(View):
    def post(self, request, pk):
        schedule = get_object_or_404(ScheduledPost, pk=pk, post__user=request.user)
        if request.POST.get("delete"):
            schedule.delete()
            messages.success(request, "Schedule deleted successfully!")
            return redirect('clientManagement:schedule')
        new_time = request.POST.get("schedule_time")
        platform = request.POST.get("platform", schedule.platform)

        if new_time:
            schedule.scheduled_time = new_time
        schedule.platform = platform
        schedule.save()

        messages.success(request, "Schedule updated successfully!")
        return redirect('clientManagement:schedule')

class NewPostView(View):
    template_name = 'clientManagement/new_post.html'

    def get(self, request):
        return render(request, self.template_name)

class ApplyEditView(View):
    def post(self, request, post_id):
        post = get_object_or_404(Post, id=post_id, user=request.user)
        edited_image = request.FILES.get("edited_image")
        if not edited_image:
            messages.error(request, "No edited image was uploaded.")
            return redirect('clientManagement:edit_image', post_id=post_id)

        # 1) Delete the old file if it exists
        if post.image_file:
            post.image_file.delete(save=False)

        # 2) Save the newly edited image under the same ImageField
        post.image_file.save(edited_image.name, edited_image, save=True)

        messages.success(request, "Image updated successfully.")
        return redirect("clientManagement:content_library")
    
class CampaignListView(View):
    template_name = 'clientManagement/campaignList.html'

    def get(self, request):
        campaigns = Campaign.objects.filter(user=request.user).prefetch_related('posts')
        return render(request, self.template_name, {
            'campaigns': campaigns
        })

class DeleteCredentialView(View):
    def post(self, request):
        try:
            body = json.loads(request.body)
            platform = body.get("platform")
            if not platform:
                return JsonResponse({'success': False, 'message': 'Platform not specified'})
            UserCredential.objects.filter(user=request.user, platform=platform).delete()
            return JsonResponse({'success': True})
        except Exception as e:
            return JsonResponse({'success': False, 'message': str(e)})
        
class DeleteCampaignView(View):
    def post(self, request, campaign_id):
        campaign = get_object_or_404(Campaign, id=campaign_id, user=request.user)
        campaign.delete()
        return JsonResponse({'success': True})

class CreateCampaignView(View):
    template_name = 'clientManagement/campaign.html'

    def get(self, request, campaign_id=None):
        credentials = UserCredential.objects.filter(user=request.user)
        platforms = list(credentials.values_list('platform', flat=True))
        campaign = None
        grouped_posts = defaultdict(lambda: defaultdict(list))

        if campaign_id:
            campaign = get_object_or_404(Campaign, id=campaign_id, user=request.user)
            posts = campaign.posts.all()
            for post in posts:
                grouped_posts[str(post.date)][post.platform].append({
                    'time': post.time.strftime('%H:%M') if post.time else '',
                    'content': post.text,
                    'target_audience': post.target_audience,
                    'keywords': post.keywords,
                    'tone': post.tone,
                    'length': post.length,
                    'call_to_action': post.call_to_action,
                    'image_prompt': post.image_prompt,
                })
        existing_posts_json = json.dumps(grouped_posts)

        return render(request, self.template_name, {
            'platforms': platforms,
            'campaign': campaign,
            'existing_posts': mark_safe(existing_posts_json)
        })

    def post(self, request, campaign_id=None):
        name = request.POST.get('name')
        description = request.POST.get('description')
        start_date = parse_date(request.POST.get('start_date'))
        end_date = parse_date(request.POST.get('end_date'))
        max_posts = int(request.POST.get('max_posts_per_day', 5))

        campaign_id = request.POST.get('campaign_id')
        if campaign_id:
            campaign = get_object_or_404(Campaign, id=campaign_id, user=request.user)
            campaign.name = name
            campaign.description = description
            campaign.start_date = start_date
            campaign.end_date = end_date
            campaign.max_posts_per_day = max_posts
            campaign.save()
            campaign.posts.all().delete()
        else:
            campaign = Campaign.objects.create(
                user=request.user,
                name=name,
                description=description,
                start_date=start_date,
                end_date=end_date,
                max_posts_per_day=max_posts
            )
        for key in request.POST:
            if key.startswith('schedule_'):
                slot_id = key.replace('schedule_', '')

                time = request.POST.get(f'schedule_{slot_id}')
                content = request.POST.get(f'content_{slot_id}')
                audience = request.POST.get(f'audience_{slot_id}')
                keywords = request.POST.get(f'keywords_{slot_id}')
                tone = request.POST.get(f'tone_{slot_id}')
                length = request.POST.get(f'length_{slot_id}')
                cta = request.POST.get(f'cta_{slot_id}')
                image_prompt = request.POST.get(f'image_prompt_{slot_id}', '')
                date_part, platform, _ = slot_id.rsplit('-', 2)
                utc_str = request.POST.get(f'utc_datetime_{slot_id}')
                if utc_str:
                    utc_dt = datetime.fromisoformat(utc_str.replace('Z', '+00:00')).astimezone(timezone.utc)
                    utc_date = utc_dt.date()
                    utc_time = utc_dt.time()

                    date_part, platform, _ = slot_id.rsplit('-', 2)

                    CampaignPost.objects.create(
                        user=request.user,
                        campaign=campaign,
                        content=content,
                        platform=platform,
                        date=utc_date,
                        time=utc_time,
                        target_audience=audience,
                        keywords=keywords,
                        tone=tone,
                        length=length,
                        call_to_action=cta,
                        image_prompt=image_prompt
                    )
        return redirect('clientManagement:campaign_list')
    
class VerifyMedia():
    def __init__(self, api_data):
        self.api_data = api_data

    def verify_facebook(self):
        access_token = self.api_data.get("access_token")
        page_id = self.api_data.get("page_id")

        if not access_token or not page_id:
            return JsonResponse({
                "success": False,
                "message": "Missing access token or page ID."
            })

        url = f"https://graph.facebook.com/v22.0/{page_id}?access_token={access_token}"

        try:
            response = requests.get(url)

            if response.status_code != 200:
                return JsonResponse({
                    "success": False,
                    "message": response.json().get("error", {}).get("message", "Unknown error.")
                })

            data = response.json()
            if data.get("id") == page_id:
                return JsonResponse({
                    "success": True,
                    "message": f"Verification successful. Page name: {data.get('name', 'N/A')}."
                })
            else:
                return JsonResponse({
                    "success": False,
                    "message": "Page ID mismatch."
                })

        except Exception as e:
            return JsonResponse({
                "success": False,
                "message": f"Exception occurred: {str(e)}"
            })
        
    def verify_instagram(self):
        try:
            access_token = self.api_data.get("access_token")
            page_id = self.api_data.get("page_id")

            if not access_token or not page_id:
                return JsonResponse({"success": False, "message": "Missing access token or page ID."})

            url = f"https://graph.facebook.com/v22.0/{page_id}?access_token={access_token}"
            response = requests.get(url)

            if response.status_code != 200:
                return JsonResponse({"success": False, "message": response.json().get("error", {}).get("message", "Unknown error")})
            return JsonResponse({"success": True, "message": "Verification successful."})

        except Exception as e:
            return JsonResponse({"success": False, "message": f"Exception occurred: {str(e)}"})

    def verify_twitter(self):
        try:
            auth = OAuth1(
                self.api_data["api_key"],
                self.api_data["api_secret_key"],
                self.api_data["access_token"],
                self.api_data["access_token_secret"]
            )

            response = requests.get("https://api.twitter.com/1.1/account/verify_credentials.json", auth=auth)

            if response.status_code != 200:
                return {"success": False, "message": response.text}

            user_info = response.json()
            expected_username = self.api_data.get("username")

            if expected_username and expected_username.lower() != user_info.get("screen_name", "").lower():
                return {"success": False, "message": "Twitter username does not match the token."}

            return {
                "success": True,
                "message": f"Twitter verification successful for @{user_info['screen_name']}."
            }

        except Exception as e:
            return {"success": False, "message": str(e)}
    
    def verify_reddit(self):
        try:
            auth = requests.auth.HTTPBasicAuth(
                self.api_data["client_id"],
                self.api_data["client_secret"]
            )

            data = {
                'grant_type': 'password',
                'username': self.api_data["username"],
                'password': self.api_data["password"]
            }

            headers = {'User-Agent': 'django-reddit-verification/0.1'}

            token_res = requests.post("https://www.reddit.com/api/v1/access_token",
                                      auth=auth, data=data, headers=headers)

            if token_res.status_code != 200:
                return {"success": False, "message": token_res.text}

            token_json = token_res.json()
            access_token = token_json.get("access_token")

            if not access_token:
                return {"success": False, "message": "No access token received."}

            user_headers = {
                "Authorization": f"bearer {access_token}",
                "User-Agent": "django-reddit-verification/0.1"
            }

            me_response = requests.get("https://oauth.reddit.com/api/v1/me", headers=user_headers)
            if me_response.status_code != 200:
                return {"success": False, "message": "Access token is invalid."}

            me_data = me_response.json()
            reddit_name = me_data.get("name")

            if reddit_name.lower() != self.api_data["username"].lower():
                return {"success": False, "message": "Username does not match the token."}

            return {"success": True, "message": "Reddit credentials verified."}

        except Exception as e:
            return {"success": False, "message": str(e)}

class VerifyAndSaveCredentialView(View):
    def post(self, request):
        try:
            body = json.loads(request.body)
            platform = body.get('platform')
            api_data = body.get('data')
            if not platform or not isinstance(api_data, dict):
                return JsonResponse({'success': False, 'message': 'Invalid data'})
            
            verifier = VerifyMedia(api_data)
            if platform == "facebook":
                verification_result = verifier.verify_facebook()
            elif platform == "instagram":
                verification_result = verifier.verify_instagram()
            elif platform == "twitter":
                verification_result = verifier.verify_twitter()
            elif platform=="reddit":
                verification_result = verifier.verify_reddit()
            else:
                return JsonResponse({'success': False, 'message': 'Unsupported platform'})
            
            if isinstance(verification_result, JsonResponse):
                if not verification_result.content.decode().startswith('{"success": true'):
                    return verification_result

            cred, created = UserCredential.objects.update_or_create(
                user=request.user,
                platform=platform,
                defaults={'api_data': api_data}
            )
            return JsonResponse({'success': True})
        except Exception as e:
            return JsonResponse({'success': False, 'message': str(e)})