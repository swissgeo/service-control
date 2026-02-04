from environ import Env

env = Env()
bind = [f"0.0.0.0:{env.int('HTTP_PORT', 8000)}"]
workers = env.int("HYPERCORN_WORKERS", 1)
keep_alive_timeout = env.int("HYPERCORN_KEEPALIVE", 2)
