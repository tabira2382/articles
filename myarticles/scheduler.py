import logging
from apscheduler.schedulers.background import BackgroundScheduler
from myarticles.batch import fetch_and_cache_data

logger = logging.getLogger(__name__)

def start_scheduler():
    scheduler = BackgroundScheduler()
    scheduler.add_job(fetch_and_cache_data, 'interval', days=1)  # 1日ごとに実行
    scheduler.start()
    logger.info("Scheduler started")
