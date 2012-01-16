
from lxml import html
from base64 import decodestring
from google.appengine.api import urlfetch
import json
import webapp2
import urllib, Cookie

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
            data = None
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
            URL += '/login/index.php'
        
        fetch = fetchPage(URL, 
                          urllib.urlencode({'username':USERNAME,'password':PASSWORD}), 
                          Cookie.SimpleCookie()
                         )
        tree = fetch[0]
        cookie = makeCookieHeader(fetch[1])
        data = {}
        
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
            data['courses'].append(course)  
        
        self.response.headers['Content-Type'] = 'json'
        self.response.headers['Cookie'] = cookie
        self.response.out.write(json.dumps(data))
        
class getAssignments(webapp2.RequestHandler):
     
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
    
    def post(self):
        
        URL = self.request.get('link')
        COOKIE = self.request.headers['Cookie']
    
        fetch = fetchPage(URL, None, COOKIE)
        tree = fetch[0]
        
        assignments = tree.xpath("//li[contains(@class,'assignment')]/div/a")
        data = { 'assignments':[] }
        
        for asm in assignments:
            assignment = { 'link' : asm.xpath("@href")[0],
                           'title': asm.xpath("span/text()")[0]  
                         }
            data['assignments'].append(assignment)
            
        self.response.headers['Content-Type'] = 'json'
        self.response.out.write(json.dumps(data))
        
class getAssignment(webapp2.RequestHandler):
     
    """
    {
        assignment:
            {
                description:'Bla'
                due:'Monday, 9 September 2001, 09:15 AM'
                available_from:'Yesterday'
                turned_in:'Today'
                grade:'A'
                comment:'Super fantastic.'
                status:'Submitted'
            },
    }
    
    """
    
    def post(self):
        
        URL = self.request.get('link')
        COOKIE = self.request.headers['Cookie']
    
        fetch = fetchPage(URL, None, COOKIE)
        tree = fetch[0]
        
        try:
            description = ""
            val = tree.xpath("//div[contains(@class,'no-overflow')]//text()")
            for v in val:
                description += v.strip() + " "
        except:
            description = "None"
            
        dates = tree.xpath("//td[contains(@class,'c1')]/text()")
        available_from = dates[0]
            
        try:
            due = dates[1]
        except:
            due = "None"
            
        try:
            tin = tree.xpath("//div[contains(@class,'reportlink')]/span")
            turned_in = tin[0].xpath("text()")
            status = "Done, " + tin[0].xpath("@class")
        except:
            turned_in = "Not turned in"
            status = "Not Done"
            
        if status != "Not Done":
        
            try:
                grade = tree.xpath("//div[contains(@class,'grade')]/text()")[0].strip()
            except:
                grade = "None"
                           
            try:
                comment = tree.xpath("//div[contains(@class,'comment')]/div/p/text()")[0].strip()
            except:
                comment = "None"
                
        else:
            grade = "None"
            comment = "None"
            
        data = { 
                 'description': description,
                 'grade': grade,
                 'comment': comment,
                 'available_from': available_from,
                 'due': due,
                 'turned_in': turned_in,
                 'status': status,
               }
        
        self.response.headers['Content-Type'] = 'json'
        self.response.out.write(json.dumps(data))  
        