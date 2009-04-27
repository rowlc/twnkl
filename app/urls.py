from django.conf.urls.defaults import *
from twnkl.app.views import *

urlpatterns = patterns('twnkl.app.views',
    # Example:

    (r'^$', index),
    (r'^page/(?P<page>\d+)/$', index),

    (r'^atyou/$', replies),
    
    (r'^thread/(?P<status>\d+)/$', dothread),

    (r'^about/$', about),
    (r'^login/$', login),
    (r'^logout/$', logout),
    (r'^update/$', update),

    (r'^fav/$', faves),
    (r'^fav/(?P<action>[-\w]+)/(?P<status>\d+)/$', faves_mod),
    
    (r'^twitpic/$', twit_pic),
    (r'^public/$', public),

    (r'^options/$', options),
    (r'^block/(?P<action>[-\w]+)/(?P<user>[-\w]+)/$', block),

    (r'^friend/(?P<action>[-\w]+)/(?P<user>[-\w]+)/$', follow),
    (r'^fans/$', followers),
    (r'^fans/(?P<user>[-\w]+)/$', followers),
    (r'^pals/(?P<user>[-\w]+)/$', friends),
    (r'^pals/$', friends),

    (r'^u/(?P<user>[-\w]+)/$', userinfo),
    (r'^u/(?P<user>[-\w]+)/reply/(?P<tweet_id>\d+)/$', userinfo),

    (r'^rt/(?P<tweet>\d+)/$', retweet),

    (r'^id/(?P<status_id>\d+)/$', status),

    # these ones can't be changed
    (r'^search/$', dosearch),
    (r'^search/(?P<query>[\#a-zA-Z0-9\ ]+)/ns/$', search, {'saved':True}),
    (r'^search/(?P<query>[\#a-zA-Z0-9\ ]+)/$', search),
    (r'^search/add/(?P<query>[\#a-zA-Z0-9\ ]+)/$', savesearch),
    (r'^search/del/(?P<query>[\#a-zA-Z0-9\ ]+)/$', delsearch),

    (r'^directs/sent/$', directs, {'sent':True}),    
    (r'^directs/$', directs),
    (r'^directs/compose/$', directs_reply),
    (r'^directs/reply/(?P<replyto>[-\w]+)/$', directs_reply),

    )