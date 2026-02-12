import logging

# Localhost port to communicate between Nginx and Gunicorn
bind = '127.0.0.1:8000'

# Maximum response time above which Gunicorn sends a timeout error
timeout = 60

# Number of requests before workers automatically restart
max_requests = 300

# Randomize worker restarts
max_requests_jitter = 50

# Maximum number of pending connections
backlog = 100

# Type of workers
worker_class = "uvicorn.workers.UvicornWorker"
workers = 2
threads = 1

# Log directory
errorlog = "./logs/fastapi.error.log"
accesslog = "./logs/fastapi.access.log"

# Whether to send output to the error log
capture_output = True

# How verbose the Gunicorn error logs should be
loglevel = "info"
enable_stdio_inheritance = True

# Add timestamp to access logs
access_log_format = '%(t)s %(h)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s"'

# Configure uvicorn access log to add timestamps
def post_worker_init(worker):
    access_logger = logging.getLogger("uvicorn.access")
    if access_logger.handlers:
        for handler in access_logger.handlers:
            handler.setFormatter(logging.Formatter(
                "%(asctime)s %(message)s",
                datefmt="%Y-%m-%d %H:%M:%S"
            ))
