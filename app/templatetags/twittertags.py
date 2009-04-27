from django import template
from django.core.urlresolvers import reverse

import datetime
import re

register = template.Library()

@register.filter('clean_tags')
def clean_tags(source):
    aliases = re.findall('\B@([\_a-zA-Z0-9]+)', source)
    if aliases:
        for a in aliases:
            source = re.sub('@'+a, '@<a href="' + reverse('twnkl.app.views.userinfo',kwargs={'user':a})+'">'+a+'</a>', source)

    #aliases = re.findall('\B#(\S+)', source)
    aliases = re.findall('\B#([a-zA-Z][a-zA-Z0-9]+)', source)
    if aliases:
        for a in aliases:
            source = re.sub('#'+a, '#<a href="'+ reverse('twnkl.app.views.search',kwargs={'query':a}) +'">'+a+'</a>', source)
    return source
    
@register.filter
def timezone ( date, time_zone_offset ):
        if time_zone_offset is None:
           time_zone_offset = 0 
        offset = datetime.timedelta(hours=time_zone_offset)
        return date+offset