#turn it in webapp.
# Jose M Vidal <jmvidal@gmail.com>

from google.appengine.api import users
from google.appengine.ext import webapp 
from google.appengine.ext import db 
from google.appengine.ext.webapp.util import run_wsgi_app 
import re
from datetime import tzinfo, timedelta, datetime #@UnresolvedImport
#from time import strptime, mktime #@UnresolvedImport
import urllib 
import os
from google.appengine.ext.webapp import template

#the list of teachers are the only ones that can create classes and homeworks and see everyone's submissions and grade them
teachers = ['jmvidal@gmail.com']

#The Database objects
class Class(db.Model):
    name = db.StringProperty()
    owner = db.UserProperty()
    
class Homework(db.Model):
    className = db.ReferenceProperty(Class)
    name = db.StringProperty()
    title = db.StringProperty()
    dueDate = db.DateTimeProperty()
    
class Upload(db.Model):
    className = db.ReferenceProperty(Class)
    hwName = db.ReferenceProperty(Homework)
    owner = db.UserProperty() #the logged-in user, the one who uploaded it
    ownerNickname = db.StringProperty()
    date = db.DateTimeProperty() #time of submission
    file = db.BlobProperty() # the file
    fileName = db.StringProperty()

#Database utility functions    
def getClassNamed(name):
    query = Class.all()
    query.filter('name =',name)
    if (query.count(1) < 1):
        return ''
    return query.fetch(1)[0]

def getHwNamed(className, hwName):
    theClass = getClassNamed(className)
    if theClass == '':
        return ''
    query = Homework.all()
    query.filter('name =',hwName).filter('className =',theClass)
    if query.count(1) < 1:
        return ''
    return query.fetch(1)[0]

# A complete implementation of current DST rules for major US time zones.
ZERO = timedelta(0)
HOUR = timedelta(hours=1)
# A UTC class.
class UTC(tzinfo):
    """UTC"""

    def utcoffset(self, dt):
        return ZERO

    def tzname(self, dt):
        return "UTC"

    def dst(self, dt):
        return ZERO

utc = UTC()

def first_sunday_on_or_after(dt):
    days_to_go = 6 - dt.weekday()
    if days_to_go:
        dt += timedelta(days_to_go)
    return dt

# In the US, DST starts at 2am (standard time) on the first Sunday in April.
DSTSTART = datetime(1, 4, 1, 2)
# and ends at 2am (DST time; 1am standard time) on the last Sunday of Oct.
# which is the first Sunday on or after Oct 25.
DSTEND = datetime(1, 10, 25, 1)

class USTimeZone(tzinfo):

    def __init__(self, hours, reprname, stdname, dstname):
        self.stdoffset = timedelta(hours=hours)
        self.reprname = reprname
        self.stdname = stdname
        self.dstname = dstname

    def __repr__(self):
        return self.reprname

    def tzname(self, dt):
        if self.dst(dt):
            return self.dstname
        else:
            return self.stdname

    def utcoffset(self, dt):
        return self.stdoffset + self.dst(dt)

    def dst(self, dt):
        if dt is None or dt.tzinfo is None:
            # An exception may be sensible here, in one or both cases.
            # It depends on how you want to treat them.  The default
            # fromutc() implementation (called by the default astimezone()
            # implementation) passes a datetime with dt.tzinfo is self.
            return ZERO
        assert dt.tzinfo is self

        # Find first Sunday in April & the last in October.
        start = first_sunday_on_or_after(DSTSTART.replace(year=dt.year))
        end = first_sunday_on_or_after(DSTEND.replace(year=dt.year))

        # Can't compare naive to aware objects, so strip the timezone from
        # dt first.
        if start <= dt.replace(tzinfo=None) < end:
            return HOUR
        else:
            return ZERO

Eastern  = USTimeZone(-5, "Eastern",  "EST", "EDT")
Central  = USTimeZone(-6, "Central",  "CST", "CDT")
Mountain = USTimeZone(-7, "Mountain", "MST", "MDT")
Pacific  = USTimeZone(-8, "Pacific",  "PST", "PDT")

#TODO: Instead of always assuming Eastern time zone, we should be using the browsers' timezone.
def fixTimezone(d):
    """Returns string that represents this UTC date d in Eastern and looks pretty."""
    return d.replace(tzinfo=utc).astimezone(Eastern).strftime("%Y-%m-%d %I:%M:%S %p")
 
#Our one and only request handler    
class MainPage(webapp.RequestHandler):
    def get(self):
        user = users.get_current_user()
#        self.response.headers['Content-Type'] = 'text/plain'
        if user:
            userInfo = ('<b>%s</b> <a href="%s">logout</a>') % (user.nickname(), users.create_logout_url('/'))
        else:
            self.response.out.write(('<html><body><p>You must <a href="%s">login</a> first.</p></body></html>') % (users.create_login_url(self.request.uri)))
            return
        #TODO: all this stuff should be moved to a template
#        self.response.out.write("""<html><head>
#        <link type="text/css" href="/prettify/prettify.css" rel="stylesheet"/>
#        <link type="text/css" href="/js/css/ui-lightness/jquery-ui-1.8.6.custom.css" rel="stylesheet"/>
#        <script type="text/javascript" src="/prettify/prettify.js"></script>
#        <script type="text/javascript" src="/js/jquery-1.4.2.min.js"></script>
#        <script type="text/javascript" src="/js/development-bundle/ui/jquery-ui-1.8.6.custom.js"></script>
#        <script type="text/javascript" src="/js/jquery-ui-timepicker-addon.min.js"></script>
#        <script type="text/javascript" src="/js/scripts.js"></script>
#        </head>""")
#        self.response.out.write('<body onload="prettyPrint()"><div class="userinfo">%s</div>' % userInfo)
        templateValues ={'userInfo' : userInfo}
        #if at / then show classes 
        pathList = re.split('/',self.request.path) # / => ['',''], /145 => ['','145'], /145/hw1 => ['','145','hw1']
        if (self.request.path == '/'): #at /
            classes = Class.all() #TODO: should these two dbase calls be made just once? 
            classes.filter('owner !=', user)
            templateValues['title'] = 'Turn It In'
            templateValues['classes'] = classes
            myClasses = Class.all().filter('owner =', user)
            templateValues['myClasses'] = myClasses
            templateValues['isTeacher'] = (user.email() in teachers)
            path = os.path.join(os.path.dirname(__file__), 'index.html')
            self.response.out.write(template.render(path, templateValues))
            return           
        #if at /classname then show create-hw button, if teacher. Show list of hw links to everyone.
        elif (len(pathList) == 2):
            className = pathList[1]
            query = Class.all().filter('name =',className)
            if (query.count() < 1):
                self.response.set_status(404)
                self.redirect('/')
                return
            theClass = query.fetch(1)[0]
            homeworks = Homework.all().filter('className =', theClass)
            templateValues['title'] = className
            templateValues['className'] = className
            templateValues['homeworks'] = homeworks
            templateValues['isClassTeacher'] = user.email() in teachers and theClass.owner == user
            path = os.path.join(os.path.dirname(__file__), 'class.html')
            self.response.out.write(template.render(path, templateValues))
            return           
        elif len(pathList) == 3: #at /classname/hwx, let user upload file, list user's uploaded files, owner of class sees list of ALL uploaded files
            className = pathList[1]
            hwName = pathList[2]
            query = Upload.all()
            theClass = getClassNamed(className)
            theHw = getHwNamed(className, hwName)
            if theHw == '' or theClass == '':
                self.response.set_status(404)
                self.redirect('/')
                return
            query.filter('className =', theClass).filter('hwName =', theHw).order('owner')
            self.response.out.write('<h2><a href="/%s">%s</a>: %s : %s</h2>' % (className,className,hwName, theHw.title))
            self.response.out.write('<h3>Due %s</h3>' % fixTimezone(theHw.dueDate))
            if theClass.owner == user: #class owner, show all the uploads for this hw.
                query.order('owner')
                self.response.out.write('<table><thead><tr><th>User</th><th>Filename</th><th>Submit Time</th></tr></thead><tbody>')
                lastStudent = ""
                for up in query:
                    currentStudent = up.owner.nickname() 
                    if currentStudent == lastStudent:
                        student = ""
                    else:
                        student = currentStudent
                    if up.date <= theHw.dueDate:
                        self.response.out.write('<tr><td><a href="%s/%s">%s</a></td><td>%s</td><td>%s</td></tr>' %
                                                (hwName, urllib.quote(up.owner.nickname()) , student, urllib.quote(up.fileName), fixTimezone(up.date)))
                    else:
                        self.response.out.write('<tr><td><a href="%s/%s">%s</a></td><td>%s</td><td style="color:red">%s</td></tr>' %
                                                (hwName, urllib.quote(up.owner.nickname()) , student, urllib.quote(up.fileName), fixTimezone(up.date)))
                    lastStudent = currentStudent
                self.response.out.write('</tbody></table>')
            else: #not owner of class so show only his uploads
                query.filter('owner =', user)
                self.response.out.write("""
                <form enctype="multipart/form-data" method="post" action="/%s/%s">
                <input type="file" name="file" />
                <input type="submit" title="Upload another file." value="Upload"/>
                </form>""" % (className, hwName))
                self.response.out.write('<ul>')
                for up in query:
                    self.response.out.write("""<li>%s<br/><em>Submitted: %s</em><br/>
                    <form action="/%s/%s/%s" method="post"><input type="submit" title="Delete this file." value="Delete"/>
                    <input type="hidden" name="action" value="delete" /></form>
                    <pre class="prettyprint linenums">%s</pre> 
                    </li>""" % (up.fileName, fixTimezone(up.date), className, hwName, up.fileName, up.file))
                self.response.out.write('</ul>')
        else: #/class/hw1/test@example.com
            className = pathList[1]
            theClass = getClassNamed(className)
            if theClass == '' or theClass.owner != user:
                self.response.set_status(403) #forbidden. cannot see submitted homeworks unless you are the class.owner
                self.redirect('/%s' % className)
                return
            hwName = pathList[2]
            studentNickname = urllib.unquote(pathList[3])
            query = Upload.all()
            theHw = getHwNamed(className, hwName)
            if theHw == '' or theClass == '':
                self.response.set_status(404)
                self.redirect('/')
                return
            self.response.out.write('<h2><a href="/%s">%s</a>: <a href="/%s/%s">%s</a></h2>' % (className,className,className,hwName,hwName))
            query.filter('className =', theClass).filter('hwName =', theHw).filter('ownerNickname =',studentNickname)
            self.response.out.write('<h2>%s</h2>' % studentNickname)
            self.response.out.write('<ul>')
            for up in query:
                self.response.out.write('<li>%s<br/><em>Submitted: %s</em><br><pre class="prettyprint linenums">%s</pre></li>' %
                                            (up.fileName, fixTimezone(up.date) , up.file))
            self.response.out.write('</ul>')          
        self.response.out.write('</body></html>')
        
    def post(self):
        user = users.get_current_user()
        if not user:
            self.redirect('/')
            return
        if self.request.get('action') == 'delete': #use action=delete as HTTP DELETE, so it works from all browsers
            self.delete()
            return
        pathList = re.split('/',self.request.path) # / => ['',''], /145 => ['','145'], /145/hw1 => ['','145','hw1']
        if (self.request.path == '/'): #if at / then create a new class
            name = self.request.get('name')
            if not re.match('^[a-zA-Z0-9]*$',name): #class names must be just letters and numbers, so they work nicely as url
                self.response.set_status(403)
                self.redirect('/')
                return
            newClass =  Class()
            newClass.owner = user
            newClass.name = self.request.get('name')
            newClass.put()
            self.redirect('/')
        elif (len(pathList) == 2): #at /classname so create a new hw for this class.
            className = pathList[1]
            theClass = getClassNamed(className)
            if theClass == '' or theClass.owner != user:
                self.response.set_status(403) #forbidden. cannot add a homework unless you are the owner of the class and it exists.
                self.redirect('/%s' % className)
                return
            newHw = Homework()
            newHw.className = getClassNamed(className)
            newHw.name = self.request.get('name') 
            newHw.title = self.request.get('title')
#            newHw.dueDate = datetime.fromtimestamp(mktime(strptime(self.request.get('date'),'%m/%d/%Y %H:%M')))
            newHw.dueDate = datetime.strptime(self.request.get('date'),'%m/%d/%Y %H:%M').replace(tzinfo=Eastern)
            newHw.put()
            self.redirect('/%s' % className)
        elif (len(pathList) == 3): #/class/hw, add the file as an upload
            className = pathList[1]
            hwName = pathList[2]
            theClass = getClassNamed(className)
            theHw = getHwNamed(className, hwName)
            newup = Upload()
            newup.className = theClass
            newup.hwName = theHw
            newup.date = datetime.now(Eastern)
            newup.owner = user
            newup.ownerNickname = user.nickname()
            file = self.request.get('file')
            newup.fileName = self.request.POST[u'file'].filename
            newup.file = db.Blob(file)
            newup.put()
            self.redirect('/%s/%s' % (className, hwName))
            return
        self.response.out.write('<html><body>You wrote:<pre>')
        self.response.out.write(self.request.get('name'))
        self.response.out.write('</pre></body></html>')

    def delete(self):
        user = users.get_current_user()
        if not user: #only logged in users can delete
            self.redirect('/')
            return
        pathList = re.split('/',self.request.path) # / => ['',''], /145 => ['','145'], /145/hw1 => ['','145','hw1']
        if (self.request.path == '/'):
            self.redirect('/')
            return
        className = pathList[1]
        theClass = getClassNamed(className)
        if theClass == '':
            self.response.set_status(403) #forbidden
            self.redirect('/%s' % className)
            return
        if len(pathList) == 2: #/classname, delete this class if owner
            #first, delete all its homeworks, and all their uploads
            if theClass.owner != user:
                self.response.set_status(403) #forbidden
                self.redirect('/%s' % className)
                return
            query = Homework.all()
            query.filter('className =',theClass)
            for hw in query:
                hw.delete()
            query = Upload.all().filter('className =',theClass)
            for up in query:
                up.delete()
            theClass.delete()
            self.redirect('/')
            return
        if len(pathList) == 3: #/class/hw, delete this homework an its uploads
            if theClass.ownser != user:
                self.response.set_status(403) #forbidden
                self.redirect('/%s' % className)
                return
            hwName = pathList[2]
            theHw = getHwNamed(className, hwName)
            query = Upload.all().filter('className =',theClass).filter('hwName =',theHw)
            for up in query:
                up.delete()
            theHw.delete()
            self.redirect('/%s' % className)
            return
        if len(pathList) == 4: #/class/hw/fileName, make sure user owns the fileName upload
            hwName = pathList[2]
            fileName = pathList[3]
            theHw = getHwNamed(className, hwName)
            query = Upload.all().filter('className =',theClass).filter('hwName =',theHw).filter('owner =', user).filter('fileName =', fileName)
            for up in query:
                up.delete()
            self.redirect('/%s/%s' % (className,hwName))
            return
            
application = webapp.WSGIApplication( [('/.*', MainPage)], debug=True)

def main():
    run_wsgi_app(application)

if __name__ == "__main__":
    main()
