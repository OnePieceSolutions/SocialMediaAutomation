from apscheduler.schedulers.background import BackgroundScheduler
from .tasks import run_campaign_scheduler

def start():
    scheduler = BackgroundScheduler()
    scheduler.add_job(run_campaign_scheduler, 'interval', seconds=20)
    scheduler.start()
