from django.core.cache import cache
from django.core.paginator import Paginator, EmptyPage, InvalidPage
from django.core.urlresolvers import reverse
from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import render_to_response
from django.template import RequestContext

import hashlib
import re
import time, datetime
import urllib,urllib2
from urllib2 import HTTPError
from xml.sax.saxutils import unescape

import simplejson as json
import twitter
from twnkl.twitpic import twitpic
from twnkl.app.models import *

#
# logging code
# 

import logging
LOG_FILENAME = '/home/sites/twnkl.txt'
logging.basicConfig(filename=LOG_FILENAME,level=logging.DEBUG,)

# logging.debug('This message should go to the log file')


#
# helper and data collection functions
#

def logentry(logtext):
    logging.debug(logtext)

def loginrequired(target):

    def wrapper(*args, **kargs):
	request = args[0] if (len(args) > 0) else None
	if request:
	    if request.session.get('u',default=None):
    	        return target(*args, **kargs)
	    else:
	    	return HttpResponseRedirect(reverse('twnkl.app.views.index'))
	else:
	    return HttpResponseRedirect(reverse('twnkl.app.views.index'))
	    
    return wrapper

def auth(request):
    '''
    helper function to obtain an authenticated api object
    also ensures that the current session has the users preferences loaded
    '''
    if request.session.get('u',None):
        # logged in, so:
        if request.session.get('options',None):
    	    request.session['options'] = TwitterUser.objects.filter(username=hash(request.session['u']))[0] 

        api = twitter.Api(username=request.session['u'],password=request.session['p'])
        return api
    else:
        return render_to_response('login.html')

def trimApi(url):
    '''
    helper function for short urls
    ''' 
    try:
        jsondata = urllib2.urlopen(url).read()
        data = json.loads(jsondata)
        resp = '/'.join(('http://u.twnkl.org',data.get('code',None)))
    except HTTPError:
        resp = None
        
    return resp

def mobyApi(url):
    '''
    helper function for mobypic urls
    '''
    resp = cache.get(url,None)
    if not resp:
        f = urllib2.urlopen(url)
        resp = f.read()
        cache.set(url,resp,3600)
        
    return resp
    
def shortUrls(source):
    '''
    finds and replaces urls with short ones - memcached
    '''
    re1='.*?'	# Non-greedy match on filler
    re2='((?:http|https)(?::\\/{2}[\\w]+)(?:[\\/|\\.]?)(?:[^\\s"]*))'	# HTTP URL 1

    urls = re.findall(re1+re2, source)
    if urls:
        for url in urls:
            if not 'twitpic' in url:
                surl = trimApi('http://u.twnkl.org/generate.json?'+urllib.urlencode({'href':url}))
                if surl.startswith("http://u.twnkl.org/"):
                	source = re.sub(url, surl, source)

    return source

def twitPics(source):
    '''
    finds and marks up twitpics
    '''
    re1='.*?'	# Non-greedy match on filler
    re2='((?:\\/[\\w\\.\\-]+)+)'	# Unix Path 1

    rg = re.compile(re1+re2,re.IGNORECASE|re.DOTALL)
    m = rg.search(source)
    if m:
        unixpath1=m.group(1)
        if unixpath1[:12] == "/twitpic.com":
            thumb = "http://twitpic.com/show/thumb/" + unixpath1[13:]
	    return '<a href="http:/' + unixpath1 + '" target=_new><img src="' + thumb + '" height=75 width=75 border=0></a>'
        else:
            return None
    else:
        return None

def mobyPics(source):
    ''' 
    finds and marks up mobypics - memcached
    '''
    re1='.*?'	# Non-greedy match on filler
    re2='((?:http|https)(?::\\/{2}[\\w]+)(?:[\\/|\\.]?)(?:[^\\s"]*))'	# HTTP URL 1

    rg = re.compile(re1+re2,re.IGNORECASE|re.DOTALL)
    m = rg.search(source)
    if m:
        httpurl1=m.group(1)
	if httpurl1[:24] == 'http://mobypicture.com/?':
	    thumb = mobyApi(''.join(('http://api.mobypicture.com?action=getThumbUrl&t=',httpurl1[24:],'&s=small&k=Chr1stwnklorg&format=plain')))
	    return '<a href="' + httpurl1 + '" target=_new><img src="' + thumb + '" height=75 width=75 border=0></a>'
	else:
	    return None
    else:
        return None

def procstatuses(statuses):
    '''
    this will do all the generic status processing stuff
    including fixing dates, identifying pics etc.
    '''
    for s in statuses:
            parsed_date = time.strptime(s.created_at, "%a %b %d %H:%M:%S +0000 %Y")
            s.created_at = datetime.datetime(*parsed_date[:6])
	    s.twitpic = twitPics(s.text)
	    s.mobypic = mobyPics(s.text)
    	    s.text = unescape(s.text)

    return statuses
        
def getStatuses(request,sTemplate,sFunction,sParams, count=None):
    '''
    returns a non-paginated thing of statuses
    '''
    if count:
	statuses = sFunction(sParams, count=count)
    else:
        statuses = sFunction(sParams)

    blockedusers = {}
    for bu in TwitterUser.objects.filter(username=hash(request.session['u']))[0].block_set.all():
        blockedusers[bu.username] = True
  
    try:
        statuses = procstatuses(statuses)        
    except TypeError:
	statuses = []
	statuses.append(sFunction(sParams))
        statuses = procstatuses(statuses)

    rubbishbin = []
    for s in statuses:
	if blockedusers.get(s.user.screen_name,False):
	    rubbishbin.append(s)
    for trash in rubbishbin:
        statuses.remove(trash)

    return render_to_response(sTemplate, locals(), RequestContext(request))

def getStatusesPage(request,sTemplate,sFunction,sParams, myurl="/", page=1, count=None):
    '''
    returns a paginated thing of statuses
    minus any tweets from a blocked user
    '''
    
    if count:
	statuses = sFunction(sParams, count=count)
    else:
        statuses = sFunction(sParams)

    try:
        statuses = Paginator(statuses,20).page(page)
    except (EmptyPage,InvalidPage):
        statuses = Paginator(statuses,20).page(1)

    blockedusers = {}
    for bu in TwitterUser.objects.filter(username=hash(request.session['u']))[0].block_set.all():
        blockedusers[bu.username] = True

    rubbishbin = []
    for s in statuses.object_list:
	if blockedusers.get(s.user.screen_name,False):
	    rubbishbin.append(s)
    for trash in rubbishbin:
	statuses.object_list.remove(trash)

    statuses.object_list = procstatuses(statuses.object_list)
    return render_to_response(sTemplate, locals(), RequestContext(request))

def getUsers(request,sTemplate,sFunction,sParams):
    '''
    returns a list of users
    '''
    users = sFunction(sParams)
    return render_to_response(sTemplate, locals(), RequestContext(request))

def hash(textToHash=None):
    '''
    returns an md5 hash of a username
    '''
    return hashlib.md5(textToHash).hexdigest()        

#
# twitpic helper functions
#

def tp(request,f):
    '''
    helper function to handle the uploaded file, save it to tmp, and twitpic it using
    twitpic api
    '''
    tmpfile = '/tmp/'+request.session['u']+"."+f.name
    destination = open(tmpfile, 'wb+')
    for chunk in f.chunks():
        destination.write(chunk)
    destination.close()
    twit = twitpic.TwitPicAPI(request.session['u'], request.session['p'])
    twitpic_url = twit.upload(tmpfile,post_to_twitter=True,message=request.POST.get('message',''))
    return twitpic_url