release: python manage.py migrate
web: daphne rps_arena.asgi:application --port $PORT --bind 0.0.0.0 -v2
worker: daphne rps_arena.asgi:application --port 8001 --bind 0.0.0.0
