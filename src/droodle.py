
#!/usr/bin/env python
#
# Copyright 2007 Google Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
import os
path = os.path.join(os.path.dirname(__file__), 'templates')

import webapp2
import jinja2
jinja_environment = jinja2.Environment(
				loader = jinja2.FileSystemLoader(path))

from GetFetchHandler import FetchHandler, GradeFetchHandler
from api import getCourses, getAssignments, getAssignment 

class MainPageHandler(webapp2.RequestHandler):
    def get(self):
        template_values = {'last_updated': '15.1.12'}
        template = jinja_environment.get_template('index.html')
        self.response.out.write(template.render(template_values))

app = webapp2.WSGIApplication([('/', MainPageHandler),
							   ('/fetch',FetchHandler), 
							   ('/fetchGrade',GradeFetchHandler),
							   #('/api/getCourses', getCourses),
							   ])
