class MturkIDHandler(webapp.RequestHandler):
	def get(self):
		doRender(self, 'mturkid.htm',
			{'error':0})

	def post(self):
		ID=self.request.get('ID')
		acct=ID ##no reason

		form_fields = {
			"ID": ID,
			"ClassOfStudies": 'Cory Experiment 3',
			"StudyNumber": 1
			}

		form_data = urllib.urlencode(form_fields)
		url="http://www.mturk-qualify.appspot.com"
		result = urlfetch.fetch(url=url,
								payload=form_data,
								method=urlfetch.POST,
								headers={'Content-Type': 'application/x-www-form-urlencoded'})

		if result.content=="0":
			#self.response.out.write("ID is in global database.")
			doRender(self, 'do_not_qualify.htm')
		
		elif result.content=="1":
			# Check if the user already exists
			que = db.Query(User).filter('account =',ID)
			results = que.fetch(limit=1)
		
			logging.info('test')

			# Allows username 'ben' to pass. You can't just allow other names to pass - it needs to be changed in http://www.mturk-qualify.appspot.com too
			if (len(results) > 0) & (ID!='ben'):   
				doRender(self, 'do_not_qualify.htm')

			# If user is qualified (http://www.mturk-qualify.appspot.com returns 1)
			else:
				#Create the User object and log the user in.
				usernum = create_or_increment_NumOfUsers()

				browser = self.request.get('browser')
				logging.info('BROWSER: '+browser)
				#Make the data that this subject will see.
				#It is made once and stored both in self.session and in database				

				# datasets, if this applies...
				datalist = [1,2,3,4]

				datasetOrder = [0,1,2,3]
				random.shuffle(datasetOrder)

				# sets of variables
				sets = [1,2,3,1] # if we have a 4th dataset, I'll need to make another set of variables
				random.shuffle(sets)
				# randomize order of trials in each set
				trialOrders = []

				lengths = [58, 54, 55, 55]

				for i in range(0,4):
					test = []
					for j in range(0, lengths[i]):
						test.append(j)

					random.shuffle(test)
					trialOrders.append(test)

				flat_trialOrders = []
				for i in range(0, len(trialOrders)):
					for j in range(0, len(trialOrders[i])):
						flat_trialOrders.append(trialOrders[i][j])

				newuser = User(account=acct, 
					usernum=usernum, 
					browser=browser, 
					datalist=datalist, 
					sets=sets, 
					trialOrder=flat_trialOrders,
					datasetOrder=datasetOrder);

				# dataframe modeling, but I'm not sure what exactly
				userkey = newuser.put()
				# this stores the new user in the datastore
				newuser.put()

				# store these variables in the session
				self.session=get_current_session() #initialize sessions
				self.session['usernum']			= usernum
				self.session['username']		= acct
				self.session['userkey']			= userkey
				self.session['scenario']		= 0
				self.session['datalist']		= datalist
				self.session['sets']			= sets
				self.session['trialOrders'] 	= trialOrders
				self.session['datasetOrder']	= datasetOrder
				self.session['datasetLengths']	= lengths
				doRender(self, 'qualify.htm')


		# If got no response back from http://www.mturk-qualify.appspot.com
		else:
		  error="The server is going slowly. Please reload and try again."
		  self.response.out.write(result.content)