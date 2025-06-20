from django.utils import timezone
from datetime import timedelta, datetime
from .utils import generate_prompts_task, generate_content_task, PostSocialMedia
from .models import CampaignPost

def run_campaign_scheduler():
    print("Sceduler running")
    now = timezone.now()
    one_hour_from_now = now + timedelta(hours=1)
    thirty_minutes_from_now = now + timedelta(minutes=30)

    posts = CampaignPost.objects.filter(is_active=True, campaign__is_active=True)
    print(posts)
    for post in posts:
        scheduled_time = datetime.combine(post.date, post.time)
        scheduled_time = timezone.make_aware(scheduled_time)
        print(now, scheduled_time ,one_hour_from_now, post.is_prompt_generated)
        if not post.is_prompt_generated and now <= scheduled_time <= one_hour_from_now:
            print("Generating prompt")
            generate_prompts_task(str(post.id))

        if post.is_prompt_generated and not post.is_content_generated and now <= scheduled_time <= thirty_minutes_from_now:
            print("Generating Image")
            generate_content_task(str(post.id))

        if post.is_content_generated and not post.posted and now >= scheduled_time:
            print("Posting")
            try:
                platform = post.platform.lower()
                media = PostSocialMedia(post, scheduled_time, post_immediately=True)
                if platform == "facebook":
                    result = media.post_to_facebook()
                    post.platform = "facebook"
                elif platform == "instagram":
                    result = media.post_to_instagram()
                    post.platform = "instagram"
                elif platform =="twitter":
                    result = media.post_to_twitter()
                    post.platform = "twitter"
                elif platform == "reddit":
                    result = media.post_to_reddit()
                    post.platform = "reddit"
                if result.get("success"):
                    post_url = result.get("post_url")
                    post.posted = True
                    post.save()
                    print("Post URL:", post_url)
                else:
                    print("Post failed:", result.get("message"))
            except Exception as e:
                print(f"Error posting CampaignPost ID {post.id}: {e}")