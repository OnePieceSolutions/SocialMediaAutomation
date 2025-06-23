app_name = 'clientManagement'

from django.urls import path
from .views import DeleteCredentialView, SignupView, SigninView, LogoutView, DashboardView, HomeView, GeneratePromptsView, SingleImageView, EditImageView, ApplyEditView, CampaignListView, PricingView, SchedulingView, SettingsView, NewPostView,ContentLibraryView, ScheduleSubmitView, ScheduleUpdateView, proxy_image, TwitterLogin, TwitterCallback, MediaView, CreateCampaignView, VerifyAndSaveCredentialView, DeleteCampaignView, UpdateProfileView, ChangePasswordView, DeleteAccountView

urlpatterns = [
    path('', HomeView.as_view(), name='home'),
    path('signup/', SignupView.as_view(), name='signup'),
    path('signin/', SigninView.as_view(), name='signin'),
    path('logout/', LogoutView.as_view(), name='logout'),
    path('dashboard/', DashboardView.as_view(), name='dashboard'),
    path('generate_prompts/', GeneratePromptsView.as_view(), name='generate_prompts'),
    path(
        "edit_image/<post_id>/",
        EditImageView.as_view(),
        name="edit_image"
    ),
    path('image-proxy/', proxy_image, name='proxy_image'),
    path(
        "apply-edit/<post_id>/",
        ApplyEditView.as_view(),
        name="apply_edit"
    ),
    path('post/', SingleImageView.as_view(), name='post'),
    path('pricing/', PricingView.as_view(), name='pricing'),
    path('schedule/', SchedulingView.as_view(), name='schedule'),
    path('settings/', SettingsView.as_view(), name='settings'),
    path('settings/update/', UpdateProfileView.as_view(), name='update_profile'),
    path('settings/change-password/', ChangePasswordView.as_view(), name='change_password'),
    path('settings/delete-account/', DeleteAccountView.as_view(), name='delete_account'),
    path('new-post/', NewPostView.as_view(), name='new_post'),
    path('content-library/', ContentLibraryView.as_view(), name='content_library'),
    path('schedule/submit/', ScheduleSubmitView.as_view(), name='schedule_submit'),
    path('schedule/update/<int:pk>/', ScheduleUpdateView.as_view(), name='schedule_update'),
    path("twitter/login/", TwitterLogin.as_view(), name="twitter_login"),
    path("twitter/callback/", TwitterCallback.as_view(), name="twitter_callback"),
    path('media/', MediaView.as_view(), name='media'),
    path('campaigns/', CampaignListView.as_view(), name='campaign_list'),
    path('create-campaign/', CreateCampaignView.as_view(), name='create_campaign'),
    path('edit-campaign/<campaign_id>/', CreateCampaignView.as_view(), name='edit_campaign'),
    path('delete-campaign/<campaign_id>/', DeleteCampaignView.as_view(), name='delete_campaign'),
    path('verify-and-save/', VerifyAndSaveCredentialView.as_view(), name='verify_and_save_credential'),
    path('delete-credential/', DeleteCredentialView.as_view(), name='delete_credential'),
]
