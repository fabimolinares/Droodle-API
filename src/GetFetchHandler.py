import ast
import demjson, json
import lxml
from lxml import html, etree
from base64 import decodestring
import webapp2
import urllib, Cookie
from google.appengine.api import urlfetch

class FetchHandler(webapp2.RequestHandler):
    
    """
    Fetch a student from moodle.

    JSON RESPONSE (in random order):

    {
        student:'John Smith',
        courses:[
            {   
                title:'History', 
                teacher:'Bob', 
                assignments:[
                    {
                        title:'Assignment'
                        status:'Submitted'
                        due:'Monday, 9 September 2001, 09:15 AM' 
                    },
                    {
                        ...
                    },
            
                ]
            },
            {
                ...
            },
    
        ]
    }
    
    """
    
    def post(self):
        
        USERNAME = decodestring( str( self.request.get('username') ) )
        PASSWORD = decodestring( str( self.request.get('password') ) )
        URL      = self.request.get('url') 
        COOKIE   = Cookie.SimpleCookie()

        MAP = """
        {
            student:"//div[contains(@class,'logininfo')]/a/text()",
            courses: {
                each:"//div[contains(@class,'box coursebox')]",
                course:"h3/a/text()",
        
                assignments: {
                    each:"div[contains(@class,'assignment')]",
                    grade:"div[contains(@class,'name')]/a/@href",
                    title:"div[contains(@class,'name')]/a/text()",
                    due:"div[contains(@class,'info')]/text()",
                    status:"div[contains(@class,'details')]/text()"
                }
            }    
        }
        """
    
        def trim_course_name(course):

            slash = course.rfind('-',0,-1)
        
            if slash == -1:    course_name = course
            else:              course_name = course[:slash].strip()

            return course_name
        
        def trim_teacher_name(course):
                
            slash = course.rfind('-',0,-1)
            if slash == -1:    return ''
            teacher_name = course[slash+1:].strip()

            return teacher_name

        def trim_due(due):

            colon    = due.find(':')
            due_date = due[colon+2:]

            return due_date

        def trim_status(status):

            bad = status.find('yet')
            if bad == -1: return status

            return status[:bad+3]
            
        #def get_grade(link, comment=False):
        #
        #	doc = fetchPage(link)
        #	
        #	try:
        #		if comment == False:
        #			return doc.xpath("//div[contains(@class,'grade')]/text()")[0].strip()
        #		else:
        #			return doc.xpath("//div[contains(@class,'comment')]/div/p/text()")[0].strip()
        #	except:
        #		return "None."
    
        PIPELINES = {
                     'course':trim_course_name,
                     'teacher':trim_teacher_name, 
                     'due':trim_due,
                     'status': trim_status,
                     #'grade':get_grade
                    }
    
        def extractData(map,doc):

            if not isinstance(doc,etree._Element):  doc = etree.HTML(doc)
            data = {}

            for k,v in map.iteritems():

                if isinstance(v,dict):
                    if 'each' not in v:
                        v = ast.literal_eval(demjson.encode(v))
                        v['each'] = "div[contains(@class,'assignment')]"
                        v = demjson.decode(json.dumps(v))
                    
                    val = doc.xpath(v['each'])
                    del v['each']
                    data[k] = []
            
                    for doc in val:    data[k].append( extractData(v,doc) ) 

                else:  
                    key = ast.literal_eval(demjson.encode(k))
                    val = doc.xpath(v)[0].strip()
                    if key not in PIPELINES.keys():    data[k] = val
                    else:    
                        data[k] = PIPELINES.get(key)(val) 
                        
                        if key == 'course':  data['teacher'] = PIPELINES.get('teacher')(val)
                        #elif key == 'grade': data['comment'] = PIPELINES.get('grade')(val, True)

            return data
    
        def makeCookieHeader():
			
			cookieHeader = ""
			for value in COOKIE.values():
				cookieHeader += "%s=%s; " % (value.key, value.value)
			return cookieHeader
        
        def getHeaders():
			
			headers = { 
			'Content-Type': 'application/x-www-form-urlencoded', 
			'User-agent':'Opera/9.20 (Windows NT 6.0; U; en)',
			'Cookie' : makeCookieHeader()
			}
				
			return headers
        
        def fetchPage(url, data = None):
			
			if data is None:
				method = urlfetch.GET
			else:
				method = urlfetch.POST
			
			while url is not None:
				response = urlfetch.fetch(
                                          url = url, 
										  method = method, 
										  payload = data, 
										  follow_redirects = False, 
										  allow_truncated = False, 
										  headers = getHeaders(), 
										  deadline=10
                                         )
				form_data = None
				method    = urlfetch.GET
				COOKIE.load(response.headers.get('set-cookie', ''))
				
				url = response.headers.get('location')
			
			c = response.content    
			tree = lxml.html.fromstring(c)

			return tree
			
        #MAIN
        doc = fetchPage( URL, urllib.urlencode({'username':USERNAME,'password':PASSWORD}) )
       
        try:
            data = extractData( demjson.decode(MAP), doc )
        except:
            self.abort(404)

        jsondata = demjson.encode(data)

        self.response.headers['Content-Type'] = 'json'
        self.response.headers['Cookie'] = makeCookieHeader()
        self.response.out.write(jsondata)