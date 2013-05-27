# Databases

# Redis

- Main 1flow database (comments, ratings…) is 0.
- Celery broker and results is 1.
    - except on preview, where is it 7. This allows eventually running production and preview on the same Redis server.
