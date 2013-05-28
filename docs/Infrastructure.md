# Databases

# Redis

## Configuration

    databases 20

## Numbering and accesses

- Main 1flow database (comments, ratings…) is **0**.
    - on preview we could set it to **10**, to avoid mixing prod/preview, except
      if it's a desired behavior (cutting edge code on real data).

- Celery broker and results is **1**.
    - except on preview, where is it **11**. This allows eventually running production and preview on the same Redis server.

- Redis-sessions is **2**,
    - on preview, **12**.

