from django.shortcuts import render_to_response
from django.http import HttpResponse, HttpResponseRedirect
from django.core.urlresolvers import reverse
from django.template import RequestContext
from django.core.paginator import Paginator, EmptyPage, InvalidPage

import time, datetime
import hashlib
import re
import urllib,urllib2
from urllib2 import HTTPError
from xml.sax.saxutils import unescape

# my modules
import datetime
import twitter
import twnkl.twitpic
from twnkl.app.models import *
from twnkl.app.helpers import *
from twnkl.app.thread import *
  
#
# account management and about stuff
#

def login(request):
    '''
    handles the login.
    if something wierd happens, it throws the user back to the logins creen
    '''
    if request.POST:
        api = twitter.Api(username=request.POST['u'], password=request.POST['p'])
        try:
            tmp = api.GetUser(request.POST['u'])
            request.session['u']=request.POST['u']
            request.session['p']=request.POST['p']
            request.session['tz']=float(request.POST['tz'])

	    if TwitterUser.objects.filter(username=hash(request.session['u'])).count() == 0:
                newuser = TwitterUser(username=hash(request.session['u']), script=1, sound=2)
                request.session['options']=newuser
                newuser.save()
                logentry('New user %s has signed in at %s.' % (request.session['u'],datetime.datetime.today()))
	    else:
	        logentry('Existing user %s has signed in at %s.' % (request.session['u'],datetime.datetime.today()))
                
            response = HttpResponseRedirect(reverse('twnkl.app.views.index'))
	    # response.set_cookie('tz',float(request.POST['tz']))
	    return response
        except HTTPError:
            return HttpResponse('Not authenticated.')
    else:
        request.session['u']=None
        request.session['p']=None
        #request.session['tz']=None
        
        return HttpResponseRedirect(reverse('twnkl.app.views.index'))

def logout(request):
    '''
    clears the session entries and logs the user out
    '''
    request.session['u']=None
    request.session['p']=None
    #request.session['tz']=None

    return HttpResponseRedirect(reverse('twnkl.app.views.index'))

def index(request, page=1):
    '''
    shows the index (paginated) or the login screen
    '''
    if request.session.get('u',None):
        return getStatusesPage(request,'friendstimeline.html',auth(request).GetFriendsTimeline,request.session['u'], "/", page, 100)
    else:
        return render_to_response('login.html',locals(), RequestContext(request))

def about(request):
    '''
    shows the about page
    '''
    import sys   
    from django import get_version
    sys.path.append('/usr/share/cherokee/admin')
    from configured import VERSION

    pyver = sys.version
    djver = get_version()
    chver = VERSION

    return render_to_response('about.html', locals())

#
# status rendering stuff
#

@loginrequired
def dothread(request, status):
    '''
    renders a thread
    '''
    statuses = getThread(auth(request), status)
    return render_to_response('thread.html',locals(),RequestContext(request))
    
@loginrequired
def replies(request):
    ''' 
    shows the users @ reples
    '''
    return getStatuses(request,'replies.html',auth(request).GetReplies,None)

@loginrequired
def status(request, status_id):
    '''
    renders an individual status
    '''
    return getStatuses(request,'status.html',auth(request).GetStatus,status_id)

@loginrequired
def public(request):
    '''
    shows the public timeline
    '''
    statuses = procstatuses(auth(request).GetPublicTimeline())
    
    for status in statuses:
	status.in_reply_to_screen_name = auth(request).GetUser(status.in_reply_to_user_id).screen_name

    return render_to_response('public.html',locals(), RequestContext(request))

#
# direct message functions
#

@loginrequired
def directs(request, sent=None):
    '''
    displays either the inbox or sent items box
    '''
    if sent:
        messages_type = "Sent"
        messages = auth(request).GetDirectMessagesSent()
    else:
    	messages_type = "Received"
        messages = auth(request).GetDirectMessages()
        
    for m in messages:
        parsed_date = time.strptime(m.created_at, "%a %b %d %H:%M:%S +0000 %Y")
        m.created_at = datetime.datetime(*parsed_date[:6])
    return render_to_response('directs.html',locals(),RequestContext(request))

@loginrequired
def directs_reply(request, **kwargs):
    ''' 
    either processes a direct message and sends it (if posted), or 
    displays a response form
    '''
    if request.POST:
        replyto = kwargs.get('replyto',None)
        if not replyto:
            replyto = request.POST['rto']

        try:
            messages = [auth(request).PostDirectMessage(replyto,request.POST['message'])]
            request.flash.put(message= 'Direct message sent.')
	except HTTPError:
	    messages = []
            request.flash.put(message='Direct message not sent.')

        messages_type ="Sent"
        for m in messages:
            parsed_date = time.strptime(m.created_at, "%a %b %d %H:%M:%S +0000 %Y")
            m.created_at = datetime.datetime(*parsed_date[:6])        
        return render_to_response('directs.html',locals(),RequestContext(request))
    else:
        replyto = kwargs.get('replyto',None)
        # display reply form
        return render_to_response('directs_compose.html',locals(),RequestContext(request))

#
# userinfo stuff
#
@loginrequired
def userinfo(request,user, **kwargs):
    '''
    displays information about a user, including their statuses and block
    status
    '''
    # this function can be called with a tweet_id - grab it if possible
    try:
        tweet = kwargs['tweet_id']
    except KeyError:
        tweet = None
    # get the user object, and work out if they're blocked
    tuser = auth(request).GetUser(user)
    if TwitterUser.objects.filter(username=hash(request.session['u']))[0].block_set.filter(username=user).count() > 0:
    	userblocked = True
    else:
    	userblocked = False
    statuses = procstatuses(auth(request).GetUserTimeline(user))
    return render_to_response('user.html', locals(), RequestContext(request))

#
# update/rt functions
#

@loginrequired
def update(request):
    '''
    handles a posted update
    '''
    if request.POST:
        api = auth(request)
        api.SetSource('twnkl')
        api.PostUpdate(shortUrls(request.POST['status']),request.POST.get('in_reply_to_id',None))
        request.flash.put(message='Tweet posted!')
	if request.POST.get('postback',None):
	    return HttpResponseRedirect(request.META.get('HTTP_REFERER', '/'))
	else:
	    return HttpResponseRedirect(reverse('twnkl.app.views.index'))

@loginrequired
def retweet(request,tweet):
    '''
    retweets a tweet.
    '''
    # get original tweet
    orig = auth(request).GetStatus(tweet)
    tweeter = orig.user.screen_name
    tweetext = orig.text
    # render form
    return render_to_response('retweet.html', locals(), RequestContext(request))

#
# searching routines
#

@loginrequired
def search(request, query, saved=None):
    '''
    does the actual searching (as called by dosearch, below)
    '''
    results = auth(request).GetSearch(query)

    blockedusers = {}
    for bu in TwitterUser.objects.filter(username=hash(request.session['u']))[0].block_set.all():
        blockedusers[bu.username] = True

    rubbishbin = []
    for r in results:
        if blockedusers.get(r['from_user'],False):
	    rubbishbin.append(r)
	else:
    	    r['twitpic'] = twitPics(r['text'])
            r['mobypic'] = mobyPics(r['text'])

    for trash in rubbishbin:
        results.remove(trash)
    rubbishbin = []

    return render_to_response('searchresults.html',locals(),RequestContext(request))

@loginrequired
def savesearch(request,query):
    '''
    saves a search
    '''
    thisuser = TwitterUser.objects.filter(username=hash(request.session['u']))[0]
    thisuser.favourite_set.create(channel=query)
    thisuser.save()    
    request.flash.put(message='Search for ' + query + ' saved!')
    return HttpResponseRedirect(reverse('twnkl.app.views.dosearch'))

@loginrequired
def delsearch(request,query):
    '''
    Deletes a saved search
    '''
    thisuser = TwitterUser.objects.filter(username=hash(request.session['u']))[0]
    thischan = thisuser.favourite_set.filter(channel=query)[0]
    thischan.delete()    
    request.flash.put(message='Search for ' + query + ' removed!')
    return HttpResponseRedirect(reverse('twnkl.app.views.dosearch'))

@loginrequired
def dosearch(request):
    '''
    This function processes a search request if its posted, or alternatively 
    displays a search form.  Also includes saved searches on teh search form.
    '''
    if request.POST:
        # form submitted
        return search(request,request.POST['query'])
    else:
        try:
	    if TwitterUser.objects.filter(username=hash(request.session['u']))[0].favourite_set.count() > 0:
                savedsearches = TwitterUser.objects.filter(username=hash(request.session['u']))[0].favourite_set.all().order_by('channel')
            else:
                savedsearches = None
	except IndexError:
		savedsearches = None
		
        return render_to_response('searchform.html',locals(),RequestContext(request))

#
# followers and friends stuff
#
    
@loginrequired
def followers(request, user=None):
    ''' 
    returns a list of users who follow this user
    '''
    return getUsers(request,'followers.html',auth(request).GetFollowers,user)

@loginrequired        
def friends(request, user=None):
    ''' 
    returns a list of people who the user follows
    '''
    return getUsers(request,'friends.html',auth(request).GetFriends,user)
    
@loginrequired
def follow(request,action,user):
    '''
    Another multi use function to follow or unfollow someone.
    '''
    if request.session.get('u',default=None):
        # logged in, so decide whether to add or remove user
        if action == 'add':
            #follow them
            auth(request).CreateFriendship(user)
            request.flash.put(message='Followed user ' + user + '!')
        if action == 'remove':
            #unfollow
            auth(request).DestroyFriendship(user)
            request.flash.put(message='Unfollowed user ' + user + '!')
        return HttpResponseRedirect(reverse('twnkl.app.views.userinfo', kwargs={'user': user}))
    else:
        # not logged in, so do nothing
        return render_to_response('login.html')

#
# options and blocked user functions
#

@loginrequired
def options(request):
    '''
    This function shows a list of the users who are blocked.  Again, Twitter API
    doesnt give us this, so its only done based on our local db.
    
    It also shows the user options incl script and sound effects
    '''
    thisuser = TwitterUser.objects.filter(username=hash(request.session['u']))[0]

    try:
	if thisuser.block_set.count() > 0:
            usersblocked = thisuser.block_set.all()
        else:
            usersblocked = None
    except IndexError:
	usersblocked = None

    if request.POST:
        userform = UserForm(request.POST)
        if userform.is_valid():
            # update the user database
            thisuser.script = userform.cleaned_data['script']
            thisuser.sound = userform.cleaned_data['sound']
            # apply some business logic - no scripting = no sound
            if thisuser.script==2: thisuser.sound=2
            thisuser.save()
            # populate the session variable - quicker than db access
            request.session['options']=thisuser
            # populate the user form to reflect any changes imposed by business logic
            userform = UserForm(instance=thisuser)
    else:
        userform = UserForm(instance=thisuser)
    
    return render_to_response('optionform.html',locals(),RequestContext(request))

@loginrequired
def block(request,action,user):
    '''
    This multi-use function deals with blocking and unblocking users.
    As the Twitter API doesnt give a way of working out whether a user
    is blocked, that is stored (hashed) in our db.  This is used to hide
    posts from those users and to exclude them from search results.
    Again, takes an 'add' or 'remove' flag to tell it what to do.
    '''
    if request.session.get('u',default=None):
        # logged in, so decide whether to add or remove user
        if action == 'add':
            #follow them
            auth(request).CreateBlock(user)
            t = TwitterUser.objects.filter(username=hash(request.session['u']))[0].block_set.create(username=user)
            request.flash.put(message='Blocked user ' + user + '!')
            t.save()
        if action == 'remove':
            #unfollow
            auth(request).DestroyBlock(user)
            theuser = TwitterUser.objects.filter(username=hash(request.session['u']))[0].block_set.filter(username=user)[0]
            request.flash.put(message='Unblocked user ' + user + '!')
            theuser.delete()
        return HttpResponseRedirect(reverse('twnkl.app.views.userinfo', kwargs={'user': user}))
    else:
        # not logged in, so do nothing
        return render_to_response('login.html')

#
# favourite functions
#
@loginrequired        
def faves(request):
    '''
    This function simply returns a list of statuses marked as favourite by the user.
    '''
    return getStatuses(request,'faves.html',auth(request).GetFavorites,None)

@loginrequired    
def faves_mod(request,action,status):
    '''
    This multi-use function is called to either mark a status as a favourite, or to unmark a favourite.
    Its called from the urlconf with either a 'add' or 'remove' flag which tells the action what to do.
    '''
    if action=='add':
        auth(request).CreateFavorite(status)
        request.flash.put(message='Flagged post ' + status + ' as favourite!')
    if action=='del':
        auth(request).DestroyFavorite(status)
        request.flash.put(message='Removed flagged post ' + status + ' as favourite!')
        
    return HttpResponseRedirect(reverse('twnkl.app.views.faves'))
    
#
# twitpic stuff
#

@loginrequired    
def twit_pic(request):
    ''' 
    processes an uploaded picture through twitpic
    alternatively displays the upload form
    '''
    if request.POST:
        if request.session.get('u',default=None):
            # logged in, so process upload and twitpic it:
            tp(request,request.FILES['media'])
            request.flash.put(message='Picture twitpicd!')
            
            return HttpResponseRedirect(reverse('twnkl.app.views.index'))
        else:
            # not logged in, so do nothing
            return render_to_response('login.html')
    else:
        # no post data, so show the form
        return render_to_response('twitpic.html',locals(),RequestContext(request))