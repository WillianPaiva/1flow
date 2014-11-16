
import redis
# from django.conf import settings

number = 1000


def average_obj_size(db_number):

    redis_conn = redis.StrictRedis(host='127.0.0.1', db=db_number)

    p = redis_conn.pipeline()

    # keys()
    # randomkey()
    # debug_object()

    for x in range(number):
        p.randomkey()

    keys = p.execute()

    for key in keys:
        p.debug_object(key)

    results = p.execute()

    sizes = tuple(r['serializedlength'] for r in results)

    average_obj_size = sum(sizes) / (number * 1.0)

    print '>> db', db_number, 'avg on', number, ':', average_obj_size

for db_number in range(30):
    average_obj_size(db_number)

# Value at:0x7fdfa6168420 refcount:1 encoding:raw serializedlength:2259 lru:979274 lru_seconds_idle:90
# redis-cli -n 5 keys ":1:template.cache.*" | sed -e 's/^.$"//' | tr -d '"' | head -n 10 | while read KEY
# do
# 	redis-cli -n 5 DEBUG OBJECT ${KEY}
# done
