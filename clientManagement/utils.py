import json
import os
import random
from urllib.parse import urlparse
import cloudinary
import cloudinary.uploader
from django.core.files.base import ContentFile
import requests
from requests_oauthlib import OAuth1
from .models import CampaignPost, Post, UserCredential
from dotenv import load_dotenv
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(os.path.join(BASE_DIR, '.env'))

cloudinary.config(
  cloud_name = os.getenv('CLOUD_NAME'),
  api_key = os.getenv('CLOUDINARY_API'),
  api_secret = os.getenv('CLOUDINARY_API_SECRET')
)

def generate_with_openai(text_prompt, image_prompt=None):
    api_key = os.getenv('CHATGPT_API')
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}"
    }

    payload_text = {
        "model": "gpt-3.5-turbo",
        "messages": [
            {"role": "user", "content": text_prompt}
        ],
        "max_tokens": 256,
        "temperature": 0.7
    }
    
    try:
        if image_prompt!=None:
            payload_image = {
                "model": "dall-e-3",
                "prompt": image_prompt,
                "n": 1,
                "size": "1024x1024"
            }
            response_image = requests.post(
                "https://api.openai.com/v1/images/generations",
                headers=headers,
                data=json.dumps(payload_image)
            )

        response_text = requests.post(
            "https://api.openai.com/v1/chat/completions",
            headers=headers,
            data=json.dumps(payload_text)
        )

        text_generated = ""
        if response_text.status_code == 200:
            text_data = response_text.json()
            if text_data.get("choices"):
                text_generated = text_data["choices"][0]["message"]["content"]
                if image_prompt==None:
                    return text_generated, None
            else:
                print("No text prompt generated.")
        else:
            print(f"Error generating text prompt: {response_text.status_code}, {response_text.text}")
            return text_generated,None

        if response_image.status_code == 200:
            data = response_image.json()
            return text_generated, data["data"][0]["url"]
        else:
            print(f"Error: {response_image.status_code}, {response_image.text}")
            return text_generated, None
    except Exception as e:
        print(f"Exception occurred: {e}")
        return text_generated, None

def build_prompt(post):
    return f"""You are an expert AI assistant for social media marketers.
        Generate two things based on the following campaign details:
        1. A text prompt that can be used to generate engaging social media post content.
        2. An image prompt that can be used to generate a visual for the post.

        Campaign Details:
        Platform: {post.platform}
        Target Audience: {post.target_audience}
        Keywords: {post.keywords}
        Tone: {post.tone}
        Post Length: {post.length}
        Call to Action: {post.call_to_action}

        Respond in this JSON format:
        {{
        "text_prompt": "...",
        "image_prompt": "..."
        }}
        """

def build_random_prompt():
    platforms = ["Instagram", "Twitter", "LinkedIn", "Facebook", "Reddit"]
    audiences = ["Teens", "Young Adults", "Working Professionals", "Parents", "Tech Enthusiasts"]
    keywords = [["fitness", "motivation"], ["AI", "future"], ["travel", "adventure"], ["productivity", "focus"], ["fashion", "style"]]
    tones = ["Inspirational", "Funny", "Professional", "Casual", "Bold"]
    lengths = ["Short", "Medium", "Long"]
    ctas = ["Visit our website", "Download now", "Join the movement", "Subscribe today", "Try it free"]

    platform = random.choice(platforms)
    target_audience = random.choice(audiences)
    keyword_set = random.choice(keywords)
    tone = random.choice(tones)
    length = random.choice(lengths)
    call_to_action = random.choice(ctas)

    return f"""You are an expert AI assistant for social media marketers.
            Generate two things based on the following **random** campaign details:
            1. A text prompt that can be used to generate engaging social media post content.
            2. An image prompt that can be used to generate a visual for the post.

            Campaign Details:
            Platform: {platform}
            Target Audience: {target_audience}
            Keywords: {', '.join(keyword_set)}
            Tone: {tone}
            Post Length: {length}
            Call to Action: {call_to_action}

            Respond in this JSON format:
            {{
            "text_prompt": "...",
            "image_prompt": "..."
            }}
            """



def generate_prompts_task(campaign_post_id):
    post = CampaignPost.objects.get(id=campaign_post_id)
    if not post.is_prompt_generated:
        prompts = build_prompt(post)
        text_prompt, _ = generate_with_openai(prompts)
        prompts_data = json.loads(text_prompt)
        post.text_prompt = prompts_data.get("text_prompt", "")
        post.image_prompt = prompts_data.get("image_prompt", "")
        post.is_prompt_generated = True
        post.save()

def generate_content_task(campaign_post_id):
    post = CampaignPost.objects.get(id=campaign_post_id)

    if post.is_prompt_generated and not post.is_content_generated:
        text, image_url = generate_with_openai(post.text_prompt, post.image_prompt)
        image_content_file = None

        try:
            response = requests.get(image_url)
            if response.status_code == 200:
                image_content = response.content
                parsed_url = urlparse(image_url)
                filename = os.path.basename(parsed_url.path) or "generated_image.png"

                image_content_file = ContentFile(image_content)
                post.image_file.save(filename, image_content_file, save=False)
            else:
                print(f"Failed to download image: {response.status_code}")
        except Exception as e:
            print(f"Error downloading image: {e}")

        post.image_url = image_url
        post.text = text
        post.is_content_generated = True
        post.save()

        post_obj = Post(
            user=post.campaign.user,
            text_prompt=post.text_prompt,
            image_prompt=post.image_prompt,
            text=text,
            image_url=image_url,
            platform=post.platform,
        )

        if image_content_file:
            post_obj.image_file.save(filename, image_content_file, save=False)

        post_obj.save()

def get_credentials(user, platform):
    try:
        return UserCredential.objects.get(user=user, platform=platform)
    except UserCredential.DoesNotExist:
        return None

class PostSocialMedia():
    def __init__(self, post, schedule_time=None, post_immediately=False):
        self.post = post
        self.message = self.post.text or "Check out this post!"
        self.schedule_time = int(schedule_time.timestamp()) if schedule_time else None
        self.post_immediately = post_immediately
        self.user = self.post.user

        # Facebook / Instagram
        fb_cred = get_credentials(self.user, "facebook")
        fb_data = fb_cred.api_data if fb_cred else {}
        self.access_token = fb_data.get("access_token")
        self.fb_page_id = fb_data.get("page_id")

        insta_cred = get_credentials(self.user, "instagram")
        fb_data = insta_cred.api_data if insta_cred else {}
        self.instagram_user_id = fb_data.get("page_id")

        # Twitter (X)
        tw_cred = get_credentials(self.user, "twitter")
        tw_data = tw_cred.api_data if tw_cred else {}
        # self.x_client_id = tw_data.get("client_id")
        self.x_api_key = tw_data.get("api_key")
        self.x_api_key_secret = tw_data.get("api_key_secret")
        self.x_access_token = tw_data.get("access_token")
        self.x_access_token_secret = tw_data.get("access_token_secret")
        self.x_bearer_token = tw_data.get("bearer_token")

        self.x_redirect_url = "http://127.0.0.1:8000/twitter/callback/"
        self.x_scopes = "tweet.write users.read offline.access"
        self.x_auth_url = "https://twitter.com/i/oauth2/authorize"
        self.x_token_url = "https://api.twitter.com/2/oauth2/token"

        # Reddit
        reddit_cred = get_credentials(self.user, "reddit")
        reddit_data = reddit_cred.api_data if reddit_cred else {}
        self.reddit_client_id = reddit_data.get("client_id")
        self.reddit_client_secret = reddit_data.get("client_secret")
        self.reddit_username = reddit_data.get("username")
        self.reddit_password = reddit_data.get("password")
        self.subreddit = reddit_data.get("subreddit", "test")

        # Store credential objects if needed for updates
        self.fb_cred = fb_cred
        self.tw_cred = tw_cred
        self.reddit_cred = reddit_cred


    def upload_image_and_get_url(self, image_file):
        response = cloudinary.uploader.upload(image_file, resource_type="image")
        return response.get('secure_url')

    def post_to_facebook(self):
        url = f"https://graph.facebook.com/{self.fb_page_id}/photos"
        print(self.fb_page_id)
        files = None
        data = {
            "access_token": self.access_token,
            "message": self.message,
        }
        if self.post_immediately:
            data["published"] = "true"
        else:
            data["published"] = "false"
            data["scheduled_publish_time"] = self.schedule_time
        try:
            if self.post.image_file:
                with self.post.image_file.open("rb") as image:
                    files = {"source": image}
                    response = requests.post(url, data=data, files=files)
            else:
                if self.post.image_url:
                    data["url"] = self.post.image_url
                response = requests.post(url, data=data)
            if response.status_code != 200:
                return {"success": False, "message": response.text}
            result = response.json()
            post_id = result.get("post_id")
            if not post_id:
                return {"success": False, "message": "No post ID returned from Facebook."}
            post_url = f"https://www.facebook.com/{post_id}"
            return {"success": True, "message": "Photo posted successfully.", "post_url": post_url}
        except Exception as e:
            return {"success": False, "message": str(e)}

    def post_to_instagram(self):
        if self.post_immediately:
            image_url = None
            if self.post.image_file:
                image_url = self.upload_image_and_get_url(self.post.image_file)
            elif self.post.image_url:
                image_url = self.post.image_url
            if not image_url:
                return {"success": False, "message": "No image URL available for Instagram post."}
            url = f'https://graph.facebook.com/v19.0/{self.instagram_user_id}/media'
            data = {
                "access_token": self.access_token,
                "image_url": image_url,
                "caption": self.message
            }
            try:
                response = requests.post(url, data=data)
                if response.status_code != 200:
                    return {"success": False, "message": response.text}
                result = response.json()
                creation_id = result.get("id")
                if not creation_id:
                    return {"success": False, "message": "No creation ID returned."}
                
                publish_url = f'https://graph.facebook.com/v19.0/{self.instagram_user_id}/media_publish'
                publish_data = {
                    "creation_id": creation_id,
                    "access_token": self.access_token
                }
                publish_res = requests.post(publish_url, data=publish_data)
                if publish_res.status_code != 200:
                    return {"success": False, "message": publish_res.text}
                pub_res = publish_res.json()
                post_id = pub_res.get("id")
                if not post_id:
                    return {"success": False, "message": "No post ID returned from publish."}
                post_url = f"https://www.instagram.com/p/{post_id}/"
                return {"success": True, "message": "Instagram post published immediately.", "post_url": post_url}
            except Exception as e:
                return {"success": False, "message": str(e)}
        else:
            print("scheduled")
            return {"success": True, "message": "Instagram post scheduled successfully.", "post_url": f"https://www.instagram.com/"}

    def post_to_twitter(self):
        if not self.post_immediately:
            return {"success": True,
                    "message": "Twitter post scheduled successfully.",
                    "post_url": "https://x.com/"}
        self.x_bearer_token
        auth = OAuth1(
            self.x_api_key,
            self.x_api_key_secret,
            self.x_access_token,
            self.x_access_token_secret
        )

        media_id = None
        if self.post.image_file:
            try:
                with open(self.post.image_file.path, "rb") as fp:
                    upload_resp = requests.post(
                        "https://upload.twitter.com/1.1/media/upload.json",
                        files={"media": fp},
                        auth=auth,
                        timeout=30
                    )
                upload_resp.raise_for_status()
                media_id = upload_resp.json().get("media_id_string")
            except Exception as exc:
                return {"success": False,
                        "message": f"Media upload failed: {exc}"}

        # payload = {"text": self.message}
        headers = {
                    "Authorization": f"Bearer {self.x_bearer_token}",
                    "Content-Type": "application/json"
                }

        payload = {"text": "Hello from python!!"}
        if media_id:
            payload["media"] = {"media_ids": [media_id]}

        print(payload)
        try:
            tweet_resp = requests.post(
                "https://api.twitter.com/2/tweets",
                json=payload, headers=headers
            )
            print(tweet_resp.json())
            tweet_resp.raise_for_status()
        except Exception as exc:
            return {"success": False, "message": f"Tweet failed: {exc}"}
        tweet_id = tweet_resp.json()["data"]["id"]
        user_resp = requests.get("https://api.twitter.com/2/users/me", headers=headers, timeout=10).json()
        username = user_resp["data"]["username"]
        post_url = f"https://x.com/{username}/status/{tweet_id}"

        return {"success": True,
                "message": "Tweet posted successfully",
                "post_url": post_url}

    def post_to_reddit(self):
        if self.post_immediately:
            auth = requests.auth.HTTPBasicAuth(self.reddit_client_id, self.reddit_client_secret)
            data = {
                'grant_type': 'password',
                'username': self.reddit_username,
                'password': self.reddit_password
            }
            headers = {'User-Agent': 'django-reddit-post-script/0.1'}

            try:
                token_res = requests.post("https://www.reddit.com/api/v1/access_token", auth=auth, data=data, headers=headers)
                if token_res.status_code != 200:
                    return {"success": False, "message": token_res.text}

                token = token_res.json().get("access_token")
                if not token:
                    return {"success": False, "message": "No access token returned from Reddit."}

                post_headers = {
                    "Authorization": f"bearer {token}",
                    "User-Agent": "django-reddit-post-script/0.1"
                }

                payload = {
                    "title": self.message[:300],
                    "sr": self.subreddit,
                    "resubmit": True,
                }

                # Handle image or text
                image_url = None
                if self.post.image_file:
                    image_url = self.upload_image_and_get_url(self.post.image_file)
                elif self.post.image_url:
                    image_url = self.post.image_url

                if image_url:
                    payload["kind"] = "link"
                    payload["url"] = image_url
                else:
                    payload["kind"] = "self"
                    payload["text"] = self.message

                response = requests.post("https://oauth.reddit.com/api/submit", headers=post_headers, data=payload)
                result = response.json()

                if response.status_code != 200:
                    return {"success": False, "message": response.text}

                post_id = result.get("json", {}).get("data", {}).get("id")
                if not post_id:
                    redirect_url = result.get("jquery", [])[10][3][0]
                    if redirect_url:
                        post_id = redirect_url.split("/comments/")[1].split("/")[0]
                        post_url = redirect_url
                    else:
                        return {"success": False, "message": "No post ID or redirect URL returned from Reddit."}
                else:
                    post_url = f"https://reddit.com/comments/{post_id}"

                return {"success": True, "message": "Posted to Reddit.", "post_url": post_url}

            except Exception as e:
                return {"success": False, "message": str(e)}
        else:
            return {"success": True, "message": "Reddit post scheduled successfully.", "post_url": "https://www.reddit.com/"}