import multiprocessing
import os

bind = f"0.0.0.0:{os.getenv('PORT', '5001')}"
workers = int(os.getenv('GUNICORN_WORKERS', multiprocessing.cpu_count() // 2 or 1))
threads = int(os.getenv('GUNICORN_THREADS', '2'))
worker_class = os.getenv('GUNICORN_WORKER_CLASS', 'sync')
timeout = int(os.getenv('GUNICORN_TIMEOUT', '120'))
keepalive = int(os.getenv('GUNICORN_KEEPALIVE', '5'))
preload_app = False
accesslog = '-'
errorlog = '-'
loglevel = os.getenv('GUNICORN_LOG_LEVEL', 'info')
