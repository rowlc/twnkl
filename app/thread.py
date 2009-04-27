from django.core.cache import cache

import feedparser
from twitter import Status

import time, datetime

def getThread(api,status):

    d = feedparser.parse("http://search.twitter.com/search/thread/%d.atom" % int(status))

    tstatuses = []

    # generates a list of tuples that look like [(date,statusObject),(date,statusObject),etc] which will then sort correctly on the date field
    for entry in d['entries']:
        userkey = ''.join(('TWNKL-USER-KEY-',entry.author_detail.href[19:]))
        tempUser = cache.get(userkey, None)
        if not tempUser:
        	tempUser = api.GetUser(entry.author_detail.href[19:])
        	cache.set(userkey,tempUser,3600)
	tempTime = datetime.datetime.fromtimestamp(time.mktime(entry.published_parsed))
        tempStatus = Status(created_at=tempTime, id=int(entry['id'][28:]), text=entry['title'], user=tempUser)
	tempTuple = (tempTime, tempStatus)

	tstatuses.append(tempTuple)

    # listcomp to extract the status objects from the list of tuples and throw them in statuses, which is returned to the calling function
    statuses = [x[1] for x in sorted(tstatuses)]
    statuses.reverse()
    
    return statuses