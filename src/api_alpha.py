
import webapp2
from lxml import html
from base64 import decodestring
from google.appengine.api import urlfetch
import urllib
import json, Cookie
import threading

def makeCookieHeader(cookie):
    
    cookieHeader = ""
    for value in cookie.values():
        cookieHeader += "%s=%s; " % (value.key, value.value)
    return cookieHeader
        
def getHeaders(cookie):
    
    headers = { 
    'Content-Type': 'application/x-www-form-urlencoded', 
    'User-agent':'Opera/9.20 (Windows NT 6.0; U; en)',
    'Cookie' : makeCookieHeader(cookie)
    }

    return headers

def fetchPage(url, data, cookie):

    if data is None:
        response = urlfetch.fetch(
                                  url = url, 
                                  method = urlfetch.GET, 
                                  headers = {
                                             'User-agent':'Opera/9.20 (Windows NT 6.0; U; en)',
                                             'Cookie':cookie
                                            },
                                  deadline=10
                                 )
    else:
        method = urlfetch.POST

        while url is not None:
            response = urlfetch.fetch(
                                      url = url, 
                                      method = method, 
                                      payload = data, 
                                      follow_redirects = False, 
                                      headers = getHeaders(cookie), 
                                      deadline=10
                                     )
            data   = None
            method = urlfetch.GET
            cookie.load(response.headers.get('set-cookie', ''))
            
            url = response.headers.get('location')

    c = response.content    
    tree = html.fromstring(c)

    return (tree,cookie)

class getCourses(webapp2.RequestHandler):
    
    """
    {
        student: 'Richard Tiutiun'
        courses:[
            {
                title:'AP World History - Adam Thornton'
                link:'http://kis.net.ua/study/course/view.php?id=91'
            },
        ]
    }
    
    """
    
    def post(self):
        
        USERNAME = decodestring( str( self.request.get('username') ) )
        PASSWORD = decodestring( str( self.request.get('password') ) )
        URL      = self.request.get('url') 
        
        if not URL.endswith('/login/index.php') and not URL.endswith('/login/index.php/'): 
            URL  += '/login/index.php'
        
        fetch = fetchPage(URL, 
                          urllib.urlencode({'username':USERNAME,'password':PASSWORD}), 
                          Cookie.SimpleCookie()
                         )
        tree = fetch[0]
        cookie = makeCookieHeader(fetch[1])
        data = {}
        threads = []
        
        student = tree.xpath("//div[contains(@class,'logininfo')]/a")
        
        if len(student) == 0: self.abort(404) #bad url or credentials
            
        data['student'] = student[0].xpath("text()")[0]
        data['courses'] = []
        
        fetch = fetchPage(student[0].xpath("@href")[0],
                         None,
                         cookie
                         )
        tree = fetch[0]
        student = None
        courses = tree.xpath("//td[contains(@class,'info c1')]/a")
        courses.pop(0)
        
        for crs in courses:
            course = { 'title':crs.xpath("text()")[0].strip(), }
            s = crs.xpath("@href")[0]
            if s.rfind('tag') != -1: continue #sometimes there are 'tags', not courses
            link = (s[:s.find('=')]+s[s.rfind('='):]).replace('user','course')
            course['link'] = link
            course['assignments'] = []
            thread = getAssignments(course, cookie)
            thread.start()
            threads.append(thread)
              
        for thread in threads:
            course = thread.COURSE
            for t in thread.THREADS:
                assignment = t.ASSIGNMENT
                course['assignments'].append(assignment)
            data['courses'].append(course)
            
        self.response.headers['Content-Type'] = 'json'
        self.response.out.write(json.dumps(data))
        
class getAssignments(threading.Thread):
     
    """
    {
        assignments:[
            {
                link = 'http://kis.net.ua/study/mod/assignment/view.php?id=3770'
                title = 'Bantu Migrations.'
            },
        ]
    }
    
    """
    
    def __init__(self, course, cookie):
        
        self.COURSE = course
        self.COOKIE = cookie
        threading.Thread.__init__(self)
    
    def run(self):
        
        fetch = fetchPage(self.COURSE['link'], None, self.COOKIE)
        tree  = fetch[0]
        
        assignments = tree.xpath("//li[contains(@class,'assignment')]/div/a")
        self.DATA   = { 'assignments':[] }
        self.THREADS = []
        
        for asm in assignments:
            assignment = { 'title': asm.xpath("span/text()")[0] }
            thread = getAssignment(asm.xpath("@href")[0], self.COOKIE, assignment)
            thread.start()
            self.THREADS.append(thread)
        
class getAssignment(threading.Thread):
     
    """
    {
        title:'Bla',
        description:'Bla',
        due:'Monday, 9 September 2001, 09:15 AM',
        available_from:'Sunday, 8 September 2001, 09:15 AM',
        turned_in:'Tuesday, 10 September 2001, 09:15 AM',
        grade:'B',
        comment:'Good, but late.',
        status:'Submitted, late'
    }
    
    """
    def __init__(self, url, cookie, assignment):
        self.URL = url
        self.COOKIE = cookie
        self.ASSIGNMENT = assignment
        threading.Thread.__init__(self)
    
    def run(self):
    
        fetch = fetchPage(self.URL, None, self.COOKIE)
        tree = fetch[0]
        
        try:
            self.ASSIGNMENT['description'] = ""
            val = tree.xpath("//div[contains(@class,'no-overflow')]//text()")
            for v in val:
                self.ASSIGNMENT['description'] += v.strip() + " "
        except:
            self.ASSIGNMENT['description'] = "None"
            
        dates = tree.xpath("//td[contains(@class,'c1')]/text()")
        
        try:
            self.ASSIGNMENT['available_from'] = dates[0]
        except:
            self.ASSIGNMENT['available_from'] = "None"
        
        try:
            self.ASSIGNMENT['due'] = dates[1]
        except:
            self.ASSIGNMENT['due'] = "None"
            
        try:
            tin = tree.xpath("//div[contains(@class,'reportlink')]/span")
            self.ASSIGNMENT['turned_in'] = tin[0].xpath("text()")
            self.ASSIGNMENT['status'] = "Done, " + tin[0].xpath("@class")
        except:
            self.ASSIGNMENT['turned_in'] = "Not turned in"
            self.ASSIGNMENT['status'] = "Not Done"
            
        if self.ASSIGNMENT['status'] != "Not Done":
        
            try:
                self.ASSIGNMENT['grade'] = tree.xpath("//div[contains(@class,'grade')]/text()")[0].strip()
            except:
                self.ASSIGNMENT['grade'] = "None"
                           
            try:
                self.ASSIGNMENT['comment'] = tree.xpath("//div[contains(@class,'comment')]/div/p/text()")[0].strip()
            except:
                self.ASSIGNMENT['comment'] = "None"
                
        else:
            self.ASSIGNMENT['grade'] = "None"
            self.ASSIGNMENT['comment'] = "None"
        