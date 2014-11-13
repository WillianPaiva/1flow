
# Libs

https://github.com/tweepy/tweepy/
    + 

https://github.com/sixohsix/twitter
    - seems to handle everything, including posting with images, DMs…
    - quite reactive developer  

https://github.com/geduldig/TwitterAPI
    + lightweight & easy to use, easy to customize because it yields the JSON items.
    + a small handfull of issues and developper is listening / answering.

https://github.com/bear/python-twitter
    + feature complete, but not that customizable, probably too big.
    + a lot of open issues and no answer

# TODO

- integrate https://developer.yahoo.com/geo/geoplanet/ somewhere
    + Currently, users of this Service are limited to 2k queries per day.
- integrate http://tools.ietf.org/html/bcp47 into Language
- https://dev.twitter.com/streaming/overview/messages-types
    - Ensure that your parser is tolerant of unexpected message formats.
    - delete:
    - scrub_geo: (range…)
    - limit:
    - status_withheld
    - user_withheld
    - disconnect (see codes)
    - warning
        + FOLLOWS_OVER_LIMIT (10k)
    - friends
    - event
        + WOW todo…
- parsing:
    + unexpected fields
    + missing counts (-1)
        * use REST API to fetch
    + missing values (fields not present, or null value)
- provision for 3x the volume
-  Accept-Encoding: deflate, gzip 

- search : use the throttle mechanism from feeds.
- a lot of things to discover / auto-load (trends…):
    + https://dev.twitter.com/rest/public/rate-limits
A totally ordered timeline display may cause a user to miss some messages as out of order messages are inserted further down the timeline. Consider sorting a timeline only when out of focus and appending to the top when in focus.

Delete messages may be delivered before the original Tweet so implementations should be able to replay a local cache of unrecognized deletes.
    
    - create (id=…, is_active=False)
    - parser: get_or_update(id=…) and do not touch is_active


# Limits

- Search will be rate limited at 180 queries per 15 minute window
- HTTP Headers:
    - X-Rate-Limit-Limit: the rate limit ceiling for that given request
    - X-Rate-Limit-Remaining: the number of requests left for the 15 minute window
    - X-Rate-Limit-Reset: the remaining window before the rate limit resets in UTC epoch seconds
* HTTP 429 “Too Many Requests” 
* { "errors": [ { "code": 88, "message": "Rate limit exceeded" } ] }
* https://dev.twitter.com/rest/reference/get/application/rate_limit_status


# Twitter filters

- nr favs >=< …
- nr retweets …
- has link
- has picture
- has video
- mentions me
- mentions @…
- hashtag is…
- tweet matches “…” (contains, RE… + negs)


# Actions

- store the tweet as is
- crawl links
- store images
- store videos
- crawl & store everything


# Twitter behavior

- When transitioning from REST to a User Stream, perform a final REST API poll after a successful connection is established to ensure that there is no data loss.

## Things to cope with

- Honor deletion messages. If a following deletes a tweet, you must remove the tweet from display and any application/server storage.


## Regular

- Consider obtaining a list of blocked users from the REST API regularly using GET blocks / ids. Cache it. An update interval of 6 to 24 hours would be reasonable.


# Twitter API

https://dev.twitter.com/streaming/reference/get/user
?delimited=length or break on '\r\n' (but not '\n')
OK DEFAULT: with=followings
?replies=all
follow=
track=
OMGYES: locations=
