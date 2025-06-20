from django.apps import AppConfig

class ClientManagementConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'clientManagement'

    def ready(self):
        from . import scheduler
        scheduler.start()