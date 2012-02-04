
import webapp2
from lxml import html
from base64 import decodestring
from google.appengine.api import urlfetch
import urllib
import json, Cookie

def makeCookieHeader(cookie):
    
    cookieHeader = ""
    for value in cookie.values():
        cookieHeader += "%s=%s; " % (value.key, value.value)
    return cookieHeader
        
def getHeaders(cookie):
    
    headers = { 
    'Content-Type': 'application/x-www-form-urlencoded', 
    'User-agent':'Opera/8.10 (Windows NT 5.0; U; en)',
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
     
        if  URL.endswith('/'):
            URL  = URL[:-1]
        if  not URL.endswith('/login/index.php'): 
            URL  += '/login/index.php'
        
        fetch = fetchPage(URL, 
                          urllib.urlencode({'username':USERNAME,'password':PASSWORD}), 
                          Cookie.SimpleCookie()
                         )
        
        tree    = fetch[0]
        cookie  = makeCookieHeader(fetch[1])
        
        student = tree.xpath("//div[contains(@class,'logininfo')]/a")
        
        if len(student) == 0: self.abort(404) #bad url or credentials
        
        data       = { 'courses': [], 'student': student[0].xpath("text()")[0] }     
        
        fetch      = fetchPage(student[0].xpath("@href")[0],
                               None,
                               cookie
                              )
        tree       = fetch[0]
        student    = None
        rawcourses = tree.xpath("//td[contains(@class,'info c1')]/a")
        
        for crs in rawcourses:
            s = crs.xpath("@href")[0]
            if s.rfind('course=') == -1: continue
            link   = (s[:s.find('=')]+s[s.rfind('='):]).replace('user','course')
            course = { 'title':crs.xpath("text()")[0].strip(),
                       'link': link, 
                     }
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
        
        URL    = self.request.get('link')
        COOKIE = self.request.headers['Cookie']
        
        fetch = fetchPage(URL, None, COOKIE)
        tree  = fetch[0]
        
        rawassignments = tree.xpath("//li[contains(@class,'assignment')]/div/a")
        assignments    = []
        
        for assignment in rawassignments:
            assignments.append(
                               {'title': assignment.xpath("span/text()")[0].strip(),
                                'link' : assignment.xpath("@href")[0], 
                               }
                              )
        
        self.response.headers['Content-Type'] = 'json'
        self.response.out.write(json.dumps(assignments))
        
class getAssignment(webapp2.RequestHandler):
     
    """
    {
        description:'Bla',
        due:'Monday, 9 September 2001, 09:15 AM',
        available_from:'Sunday, 8 September 2001, 09:15 AM',
        turned_in:'Tuesday, 10 September 2001, 09:15 AM',
        grade:'B',
        comment:'Good, but late.',
        status:'Submitted, late'
    }
    
    """
    
    def post(self):
    
        URL    = self.request.get('link')
        COOKIE = self.request.headers['Cookie']
        
        fetch = fetchPage(URL, None, COOKIE)
        tree  = fetch[0]
        assignment = {}
        
        try:
            assignment['description'] = ""
            val = tree.xpath("//div[contains(@class,'no-overflow')]//text()")
            for v in val:
                assignment['description'] += v.strip() + " "
        except:
            assignment['description'] = "None"
        
        dates = tree.xpath("//td[contains(@class,'c1')]/text()")    
        
        try:
            assignment['available_from'] = dates[0]
        except:
            assignment['available_from'] = "None"
        
        try:
            assignment['due'] = dates[1]
        except:
            assignment['due'] = "None"
            
        try:
            tin = tree.xpath("//div[contains(@class,'reportlink')]/span")
            assignment['turned_in'] = tin[0].xpath("text()")[0]
            assignment['status'] = "Done, " + tin[0].xpath("@class")[0]
        except:
            assignment['turned_in'] = "Not turned in"
            assignment['status'] = "Not Done"
            
        if assignment['status'] != "Not Done":
        
            try:
                assignment['grade'] = tree.xpath("//div[contains(@class,'grade')]/text()")[0].strip()
            except:
                assignment['grade'] = "None"
                           
            try:
                assignment['comment'] = ""
                val = tree.xpath("//div[contains(@class,'comment')]/div//text()")
                for v in val:
                    assignment['comment'] += v.strip() + " "
            except:
                assignment['comment'] = "None"
                
        else:
            assignment['grade'] = "None"
            assignment['comment'] = "None"
            
        self.response.headers['Content-Type'] = 'json'
        self.response.out.write(json.dumps(assignment))
        