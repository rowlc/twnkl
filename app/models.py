from django.db import models
from django.forms import ModelForm
from django.contrib import admin

# Create your models here.
class TwitterUser(models.Model):
    username = models.CharField(max_length=100, editable=False)

    STATUS_CHOICES = ((1,'Active'),(2,'Inactive'))

    script = models.IntegerField(	choices=STATUS_CHOICES, 
    					default=1,
    					blank=False,
    					verbose_name='Enable script actions')
    sound = models.IntegerField(	choices=STATUS_CHOICES, 
    					default=1, 
    					blank=False,
    					verbose_name='Enable sound effects')

    def __unicode__(self):
        return self.username

class UserForm(ModelForm):
    class Meta:
        model=TwitterUser

class Favourite(models.Model):
    channel = models.CharField(max_length=100)
    twitteruser = models.ForeignKey(TwitterUser)
    
    def __unicode__(self):
        return '/'.join((self.twitteruser.username,self.channel))

class Block(models.Model):
    username = models.CharField(max_length=100)
    twitteruser = models.ForeignKey(TwitterUser)
    
    def __unicode__(self):
        return self.username

class FavouriteInline(admin.TabularInline):
    model = Favourite
    extra = 1

class BlockInline(admin.TabularInline):
    model = Block
    extra = 1

class TUAdmin(admin.ModelAdmin):
    inlines = [FavouriteInline, BlockInline]
            
admin.site.register(TwitterUser, TUAdmin)