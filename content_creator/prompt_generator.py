class Profile:
    def __init__(self, company_name, company_type, brand_tone=None, target_audience=None,
                 top_services_or_products=None, platforms=None, offers_or_promotions=None):
        self.company_name = company_name
        self.company_type = company_type
        self.brand_tone = brand_tone
        self.target_audience = target_audience
        self.top_services_or_products = top_services_or_products or []
        self.platforms = platforms or []
        self.offers_or_promotions = offers_or_promotions or []

class SocialMediaPromptGenerator:
    def __init__(self, prompt):
        self.profile = Profile(
            company_name=prompt['company_name'],
            company_type=prompt['company_type'],
            brand_tone=prompt['brand_tone'] or "friendly",
            target_audience=prompt['target_audience'] or "young urban dwellers",
            top_services_or_products=prompt['top_services_or_products'] or "handcrafted wooden furniture",
            platforms=prompt['platforms'] or "Instagram",
            offers_or_promotions=prompt['offers_or_promotions']
        )

    def generate_category_prompts(self, category_list):
        company = self.profile.company_name
        tone = self.profile.brand_tone or "professional"
        audience = self.profile.target_audience or "your audience"
        service = self.profile.top_services_or_products[0] if self.profile.top_services_or_products else "your services"
        platform = self.profile.platforms[0] if self.profile.platforms else "Instagram"

        prompts = []

        for category in category_list:
            if category.lower() == "morning":
                prompts.append({
                    "category": "Morning Motivation",
                    "text_prompt": f"Write a {tone} morning post for {platform} from {company}, offering encouragement and tying in the benefits of {service}. Target audience: {audience}.",
                    "image_prompt": "Bright morning-themed image with motivational text and subtle branding."
                })
            elif category.lower() == "afternoon":
                prompts.append({
                    "category": "Afternoon Tip",
                    "text_prompt": f"Share a helpful midday tip related to {service}, provided by {company}, in a casual and engaging tone.",
                    "image_prompt": "Minimalist design with a quick productivity or service tip."
                })
            elif category.lower() == "night":
                prompts.append({
                    "category": "Evening Recap",
                    "text_prompt": f"Create a thoughtful evening post for {company} reflecting on tech/industry progress, client impact, or something motivational. Audience: {audience}.",
                    "image_prompt": "Dark-themed calm visual with space for reflection or quote."
                })
            elif category.lower() == "funfacts":
                prompts.append({
                    "category": "Fun Fact",
                    "text_prompt": f"Write a fun, surprising fact relevant to the {self.profile.company_type} space, and link it back to how {company} can help.",
                    "image_prompt": "An infographic or visual surprise related to a fun tech/business stat."
                })
            elif category.lower() == "news":
                prompts.append({
                    "category": "Industry News",
                    "text_prompt": f"Create a trending news update or opinion post for {company} in the {self.profile.company_type} industry. Make it thought-provoking for {audience}.",
                    "image_prompt": "Modern, sleek news-style graphic with bold headline area."
                })
            elif category.lower() == "advertising":
                prompts.append({
                    "category": "Advertising",
                    "text_prompt": f"Write an eye-catching promotional caption for {company} highlighting {service} and encouraging new clients to inquire.",
                    "image_prompt": "High-contrast ad graphic with bold CTA and brand colors."
                })
            elif category.lower() == "limited time deals":
                offer = self.profile.offers_or_promotions[0] if self.profile.offers_or_promotions else "an exclusive offer"
                prompts.append({
                    "category": "Limited Time Deal",
                    "text_prompt": f"Announce {offer} from {company}. Make it urgent, attractive, and tailored for {audience}.",
                    "image_prompt": "Urgency-themed image with a ticking clock and offer badge."
                })
        return prompts

    def generate_all(self):
        categories = ["morning", "afternoon", "night", "funfacts", "news", "advertising", "limited time deals"]
        prompts = self.generate_category_prompts(categories)
        return prompts
