# Gunicorn configuration for Google Cloud Run
import os
import multiprocessing

# Server socket
bind = f"0.0.0.0:{os.environ.get('PORT', '8080')}"
backlog = 2048

# Worker processes
workers = 1  # Single worker for Cloud Run
worker_class = "sync"
worker_connections = 1000
timeout = 0  # No timeout for Cloud Run
keepalive = 2

# Performance tuning
max_requests = 1000
max_requests_jitter = 50
preload_app = True

# Logging
accesslog = "-"
errorlog = "-"
loglevel = os.environ.get('LOG_LEVEL', 'info').lower()
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s" %(D)s'

# Process naming
proc_name = "kindle-content-server"

# Security
limit_request_line = 4096
limit_request_fields = 100
limit_request_field_size = 8190

# Application
wsgi_app = "app:app"

# Graceful shutdown
graceful_timeout = 30

def when_ready(server):
    server.log.info("Kindle Content Server ready to serve requests")

def worker_int(worker):
    worker.log.info("Worker received INT or QUIT signal")

def pre_fork(server, worker):
    server.log.info("Worker spawned (pid: %s)", worker.pid)

def post_fork(server, worker):
    server.log.info("Worker spawned (pid: %s)", worker.pid)