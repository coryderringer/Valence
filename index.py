import os, logging, wsgiref.handlers, datetime, random, math, string, urllib, csv, json

from google.appengine.ext import webapp, db
from google.appengine.ext.webapp.util import run_wsgi_app
from google.appengine.ext.webapp import template 
from gaesessions import get_current_session
from google.appengine.api import urlfetch

LengthOfData = 48
LengthOfPractice=30
NumScenarios=2






###############################################################################
###############################################################################
######################## Data Classes for Database ############################
###############################################################################
###############################################################################

class User(db.Model):
	usernum =			db.IntegerProperty()
	account = 			db.StringProperty()
	browser =			db.StringProperty()
	sex =				db.IntegerProperty()
	ethnicity =			db.IntegerProperty()
	race =				db.IntegerProperty()
	age = 				db.IntegerProperty()
	bonusAmt =			db.IntegerProperty()
	testOrder =			db.IntegerProperty() # 0 is memory first, 1 is causal first
	

class ScenarioData(db.Model):
	user  =				db.ReferenceProperty(User)
	account = 			db.StringProperty()
	usernum =			db.IntegerProperty()
	scenario = 			db.IntegerProperty()
	
	trialTime = 		db.IntegerProperty()
	attentionFails =	db.IntegerProperty()
	trialNumber = 		db.IntegerProperty()
	trialGuess = 		db.StringProperty()
	trialCorrect = 		db.StringProperty()
	profitImpact = 		db.IntegerProperty()
	condition = 		db.StringProperty()
	
class FinalJudgmentData(db.Model):
	user  =				db.ReferenceProperty(User)
	account = 			db.StringProperty()
	usernum =			db.IntegerProperty()
	scenario = 			db.IntegerProperty()
	condition = 		db.StringProperty()

	leftDrugName =		db.StringProperty()
	rightDrugName =		db.StringProperty()
	leftDrugRarity =	db.StringProperty()
	rightDrugRarity =	db.StringProperty()
	leftDrugColor = 	db.StringProperty()
	rightDrugColor = 	db.StringProperty()
	leftNumberBad =		db.IntegerProperty() # number of bad outcomes for each drug
	rightNumberBad =	db.IntegerProperty()
	goodOutcomesLeft =	db.IntegerProperty() # given a good outcome, how many got the left drug?
	goodOutcomesRight =	db.IntegerProperty()
	badOutcomesLeft =	db.IntegerProperty()
	badOutcomesRight = 	db.IntegerProperty()
	causalJudgment =	db.IntegerProperty() # which drug is worse? higher numbers mean the right side is worse
	judgmentOrder =		db.IntegerProperty() # will have to make a code for this, list possible orders, assign one
	


#This stores the current number of participants who have ever taken the study.
#see https://developers.google.com/appengine/docs/pythondatastore/transactions
#could also use get_or_insert
#https://developers.google.com/appengine/docs/pythondatastore/modelclass#Model_get_or_insert
class NumOfUsers(db.Model):
	counter = db.IntegerProperty(default=0)


#Increments NumOfUsers ensuring strong consistency in the datastore
@db.transactional
def create_or_increment_NumOfUsers():
	obj = NumOfUsers.get_by_key_name('NumOfUsers', read_policy=db.STRONG_CONSISTENCY)
	if not obj:
		obj = NumOfUsers(key_name='NumOfUsers')
	obj.counter += 1
	x=obj.counter
	obj.put()
	return(x)



###############################################################################
###############################################################################
########################### From Book Don't Touch #############################
###############################################################################
###############################################################################
# One line had to be updated for Python 2.7
#http://stackoverflow.com/questions/16004135/python-gae-assert-typedata-is-stringtype-write-argument-must-be-string
# A helper to do the rendering and to add the necessary
# variables for the _base.htm template
def doRender(handler, tname = 'index.htm', values = { }):
	temp = os.path.join(
			os.path.dirname(__file__),
			'templates/' + tname)
	if not os.path.isfile(temp):
		return False
	# Make a copy of the dictionary and add the path and session
	newval = dict(values)
	newval['path'] = handler.request.path
#   handler.session = Session()
#   if 'username' in handler.session:
#      newval['username'] = handler.session['username']

	outstr = template.render(temp, newval)
	handler.response.out.write(unicode(outstr))  #### Updated for Python 2.7
	return True


###############################################################################
###############################################################################
###################### Handlers for Individual Pages ##########################
###############################################################################
###############################################################################

###############################################################################
################################ Ajax Handler #################################
###############################################################################

class AjaxHandler(webapp.RequestHandler):
	def get(self):
		que=db.Query(ScenarioData)
		que.order("usernum").order("trialNumber")
		d=que.fetch(limit=10000)
		doRender(self, 'ajax.htm',{'d':d})

	def post(self):
		self.session=get_current_session()
		# message=str(self.request.get('message'))
		
		# <input id="timeInput" name="timeInput" type="hidden">
  #       <input id="attentionFailsInput" name="attentionFailsInput" type="hidden">
  #       <input id="trialInput" name="trialInput" type="hidden">
  #       <input id="guessInput" name="guessInput" type="hidden">
  #       <input id="correctInput" name="correctInput" type="hidden">
  #       <input id="profitImpactInput" name="profitImpactInput" type="hidden">

  		trialTime = int(self.request.get('timeInput'))
  		attentionFails = int(self.request.get('attentionFailsInput'))
		trialNumber = int(self.request.get('trialInput')) 
		trialGuess = str(self.request.get('guessInput'))
		trialCorrect = str(self.request.get('correctInput')) # gives the correct answer (A or B)
		profitImpact = int(self.request.get('profitImpactInput'))
		totalBonus = int(self.request.get('runningBonusInput'))

		logging.info('BONUS!!!!!! '+str(totalBonus))

		
		if self.session['scenario'] == 0:
			self.session['BonusOne'] = totalBonus
		else:
			self.session['BonusTwo'] = totalBonus

		logging.info('BONUS TEST!' + str(self.session['BonusOne']))
		logging.info('SCENARIO IS '+str(self.session['scenario']))

		# how to check if there are example rows in the datastore
		que = db.Query(ScenarioData).filter('usernum =', self.session['usernum']).filter('scenario =', self.session['scenario']).filter('trialNumber =', trialNumber)
		results = que.fetch(limit=1000)
		
		# make all of the data items into 3-value arrays, then make a loop to put them in the datastore
		if (len(results) == 0):   
			newajaxmessage = ScenarioData(
				user=self.session['userkey'],
				usernum = self.session['usernum'],
				account = self.session['account'],
				scenario = self.session['scenario'],
				trialTime = trialTime,
				attentionFails = attentionFails,
				trialNumber = trialNumber,
				trialGuess = trialGuess,
				trialCorrect = trialCorrect,
				profitImpact = profitImpact,
				condition = self.session['conditions'][self.session['scenario']]);
		

			newajaxmessage.put()
			self.response.out.write(json.dumps(({'blah': 'blah'}))) # not sure what this does?

		else:
			obj = que.get()
			obj.user=self.session['userkey']
			obj.usernum = self.session['usernum']
			obj.account = self.session['account']
			obj.scenario = self.session['scenario'],
			obj.trialTime = trialTime
			obj.attentionFails = attentionFails
			obj.trialNumber = trialNumber
			obj.trialGuess = trialGuess
			obj.trialCorrect = trialCorrect
			obj.profitImpact = profitImpact
			obj.condition = self.session['conditions'][self.session['scenario']]

			obj.put()
			self.response.out.write(json.dumps(({'blah': 'blah'}))) # ?

		que2 = db.Query(User).filter('usernum =', self.session['usernum'])
		results = que2.fetch(limit=10000)

		obj = que2.get()
		
		obj.bonusAmt = self.session['BonusOne']+self.session['BonusTwo']
		
		obj.put()
		self.response.out.write(json.dumps(({'blah': 'blah'}))) # ?

# class AjaxOutcomeMemoryHandler(webapp.RequestHandler):
# 	def get(self):
# 		que=db.Query(FinalJudgmentData)
# 		que.order("usernum").order("scenario").order("judgmentNumber")
# 		d=que.fetch(limit=10000)
# 		doRender(self, 'ajaxTest.htm',{'d':d})

# 	def post(self):
# 		self.session=get_current_session()
		

#   		drug = str(self.request.get('drugInput')) # left (A) or right (B)
  		
#   		drugName = str(self.request.get('drugNameInput'))
# 		drugColor = str(self.request.get('drugColorInput')) 
# 		drugJudgment = int(self.request.get('judgmentInput'))
		
# 		judgmentNumber = int(self.request.get('judgmentNumberInput'))
# 		scenario = self.session['scenario']

# 		# how to check if there are example rows in the datastore
# 		que = db.Query(FinalJudgmentData).filter('usernum =', self.session['usernum']).filter('scenario =', scenario).filter('judgmentNumber =', judgmentNumber)
# 		results = que.fetch(limit=1000)
		
# 		# make all of the data items into 3-value arrays, then make a loop to put them in the datastore
# 		if (len(results) == 0):   
# 			newajaxmessage = FinalJudgmentData(
# 				# user properties
# 				user=self.session['userkey'],
# 				usernum = usernum,
# 				account = self.session['account'],				
# 				# scenario properties
# 				scenario = scenario,
# 				condition = self.session['conditions'][self.session['scenario']],
# 				# drug properties
# 				leftDrugName = drugA_Name,
# 				rightDrugName = drugB_Name,
# 				leftDrugRarity = leftDrugRarity, # DO THESE
# 				rightDrugRarity = rightDrugRarity,
# 				leftDrugColor = leftDrugColor,
# 				rightDrugColor = rightDrugColor,
# 				leftNumberBad = leftNumberBad, 
# 				rightNumberBad = rightNumberBad, 
# 				# goodOutcomesLeft = goodOutcomesLeft, Not this handler
# 				# goodOutcomesRight = goodOutcomesRight, Not this handler
# 				# badOutcomesLeft = badOutcomesLeft, Not this handler
# 				# badOutcomesRight = badOutcomesRight, Not this handler
# 				# causalJudgment = causalJudgment, Not this handler
# 				judgmentOrder = judgmentOrder);
		
# 			newajaxmessage.put()
# 			self.response.out.write(json.dumps(({'blah': 'blah'}))) # not sure what this does?

# 		else:
# 			obj = que.get()
			
# 			# user properties
# 			obj.user=self.session['userkey']
# 			obj.usernum = usernum
# 			obj.account = self.session['account']				
# 			# scenario properties
# 			obj.scenario = scenario
# 			obj.condition = self.session['conditions'][self.session['scenario']]
# 			# drug properties
# 			obj.leftDrugName = drugA_Name
# 			obj.rightDrugName = drugB_Name
# 			obj.leftDrugRarity = leftDrugRarity # DO THESE
# 			obj.rightDrugRarity = rightDrugRarity
# 			obj.leftDrugColor = leftDrugColor
# 			obj.rightDrugColor = rightDrugColor
# 			obj.leftNumberBad = leftNumberBad
# 			obj.rightNumberBad = rightNumberBad 
# 			# goodOutcomesLeft = goodOutcomesLeft, Not this handler
# 			# goodOutcomesRight = goodOutcomesRight, Not this handler
# 			# badOutcomesLeft = badOutcomesLeft, Not this handler
# 			# badOutcomesRight = badOutcomesRight, Not this handler
# 			# causalJudgment = causalJudgment, Not this handler
# 			obj.judgmentOrder = judgmentOrder


class AjaxMemoryHandler(webapp.RequestHandler):
	def get(self):
		que=db.Query(FinalJudgmentData)
		que.order("usernum").order("scenario").order("judgmentNumber")
		d=que.fetch(limit=10000)
		doRender(self, 'ajaxTest.htm',{'d':d})

	def post(self):
		self.session=get_current_session()

		# testOrder = 0: memory first
		# memOrder = 0: ask about outcomes given drug first
		
		# TO = 0, MO = 0: E|C, C|E, Causal
		# TO = 0, MO = 1: C|E, E|C, Causal
		# TO = 1, MO = 0: Causal, E|C, C|E
		# TO = 1, MO = 1: Causal, C|E, E|C

		if int(self.session['testOrder']) == 0 & int(self.session['memOrder']) == 0:
			judgmentOrder = 0 # E|C, C|E, Causal
		elif int(self.session['testOrder']) == 0 & int(self.session['memOrder']) == 1:
			judgmentOrder = 1 # C|E, E|C, Causal
		elif int(self.session['testOrder']) == 1 & int(self.session['memOrder']) == 0:
			judgmentOrder = 2 # Causal, E|C, C|E
		elif int(self.session['testOrder']) == 1 & int(self.session['memOrder']) == 1:
			judgmentOrder = 3 # Causal, C|E, E|C
		else:
			judgmentOrder = 100

  		usernum = self.session['usernum']
  		scenario = self.session['scenario']

  		condition = str(self.request.get('condition')) # good or bad
  		leftDrugName = str(self.request.get('leftDrugName'))
  		rightDrugName = str(self.request.get('rightDrugName'))
  		leftDrugRarity = str(self.request.get('leftDrugRarity'))
  		rightDrugRarity = str(self.request.get('rightDrugRarity'))
		leftDrugColor = str(self.request.get('leftDrugColor'))
  		rightDrugColor = str(self.request.get('rightDrugColor'))
  		leftNumberBad = int(self.request.get('leftNumberBad'))
  		rightNumberBad = int(self.request.get('rightNumberBad'))
  		goodOutcomesLeft = int(self.request.get('goodOutcomesLeft'))
  		goodOutcomesRight = int(self.request.get('goodOutcomesRight'))
  		badOutcomesLeft = int(self.request.get('badOutcomesLeft'))
  		badOutcomesRight = int(self.request.get('badOutcomesRight'))
  		
  		logging.info("usernum: " + str(usernum))
  		logging.info('account: ' + str(self.session['account']))
  		logging.info("condition: "+ str(condition))
  		logging.info("leftDrugName: "+ str(leftDrugName))
  		logging.info("rightDrugName: "+ str(rightDrugName))
  		logging.info("leftDrugRarity: "+ str(leftDrugRarity))
  		logging.info("rightDrugRarity: "+ str(rightDrugRarity))
		logging.info("leftDrugColor: "+ str(leftDrugColor))
  		logging.info("rightDrugColor: "+ str(rightDrugColor))
  		logging.info("leftNumberBad: "+ str(leftNumberBad))
  		logging.info("rightNumberBad: "+ str(rightNumberBad))
  		logging.info("goodOutcomesLeft: "+ str(goodOutcomesLeft))
  		logging.info("goodOutcomesRight: "+ str(goodOutcomesRight))
  		logging.info("badOutcomesLeft: "+ str(badOutcomesLeft))
  		logging.info("badOutcomesRight: "+ str(badOutcomesRight))
  		logging.info("memOrder: " + str(self.session['memOrder']))
  		logging.info("testOrder: " + str(self.session['testOrder']))
  		logging.info("judgmentOrder: "+ str(judgmentOrder))
  		

  		judgmentOrder = judgmentOrder 


  		

		que = db.Query(FinalJudgmentData).filter('usernum =', self.session['usernum']).filter('scenario =', scenario)
		results = que.fetch(limit=1000)


		# make all of the data items into 3-value arrays, then make a loop to put them in the datastore
		if (len(results) == 0):   
			logging.info('NEW ENTRY')
			newajaxmessage = FinalJudgmentData(
				# user properties
				user=self.session['userkey'],
				usernum = usernum,
				account = self.session['account'],				
				# scenario properties
				scenario = scenario,
				condition = condition,
				# drug properties
				leftDrugName = leftDrugName,
				rightDrugName = rightDrugName,
				leftDrugRarity = leftDrugRarity, # DO THESE
				rightDrugRarity = rightDrugRarity,
				leftDrugColor = leftDrugColor,
				rightDrugColor = rightDrugColor,
				leftNumberBad = leftNumberBad,
				rightNumberBad = rightNumberBad,
				goodOutcomesLeft = goodOutcomesLeft,
				goodOutcomesRight = goodOutcomesRight,
				badOutcomesLeft = badOutcomesLeft,
				badOutcomesRight = badOutcomesRight,
				# causalJudgment = causalJudgment, Not this handler
				judgmentOrder = judgmentOrder);
		
			newajaxmessage.put()
			self.response.out.write(json.dumps(({'blah': 'blah'}))) # not sure what this does?

		else:
			logging.info('UPDATING CURRENT')
			obj = que.get()
			
			# user properties
			obj.user=self.session['userkey']
			obj.usernum = usernum
			obj.account = self.session['account']				
			
			# scenario properties
			obj.scenario = scenario
			obj.condition = condition
			
			# drug properties
			obj.leftDrugName = leftDrugName
			obj.rightDrugName = rightDrugName
			obj.leftDrugRarity = leftDrugRarity # DO THESE
			obj.rightDrugRarity = rightDrugRarity
			obj.leftDrugColor = leftDrugColor
			obj.rightDrugColor = rightDrugColor
			obj.leftNumberBad = leftNumberBad
			obj.rightNumberBad = rightNumberBad
			obj.goodOutcomesLeft = goodOutcomesLeft
			obj.goodOutcomesRight = goodOutcomesRight
			obj.badOutcomesLeft = badOutcomesLeft
			obj.badOutcomesRight = badOutcomesRight
			# causalJudgment = causalJudgment, Not this handler
			obj.judgmentOrder = judgmentOrder

			obj.put()
			self.response.out.write(json.dumps(({'blah': 'blah'}))) # ?


class AjaxCausalHandler(webapp.RequestHandler):
	def get(self):
		# I don't even think I need this handler...
		que=db.Query(FinalJudgmentData)
		que.order("usernum").order("scenario").order("judgmentNumber")
		d=que.fetch(limit=10000)
		doRender(self, 'ajaxCausalTest.htm',{'d':d})

	def post(self):
		self.session=get_current_session()
		# message=str(self.request.get('message'))
		
		usernum = self.session['usernum']
		scenario = self.session['scenario']
		
		causalJudgment = int(self.request.get('judgmentInput'))
		
		# how to check if there are example rows in the datastore
		que = db.Query(FinalJudgmentData).filter('usernum =', self.session['usernum']).filter('scenario =', scenario)
		results = que.fetch(limit=1000)
		
		# make all of the data items into 3-value arrays, then make a loop to put them in the datastore
		if (len(results) == 0):   
			logging.info('NEW ENTRY')
			newajaxmessage = FinalJudgmentData(
				# user properties
				user=self.session['userkey'],
				usernum = usernum,
				account = self.session['account'],				
				# scenario properties
				scenario = scenario,
				# condition = self.session['conditions'][self.session['scenario']],
				# drug properties
				# leftDrugName = drugA_Name,
				# rightDrugName = drugB_Name,
				# leftDrugRarity = leftDrugRarity, # DO THESE
				# rightDrugRarity = rightDrugRarity,
				# leftDrugColor = leftDrugColor,
				# rightDrugColor = rightDrugColor,
				# leftNumberBad = leftNumberBad, Not this handler
				# rightNumberBad = rightNumberBad, Not this handler
				# goodOutcomesLeft = goodOutcomesLeft,
				# goodOutcomesRight = goodOutcomesRight,
				# badOutcomesLeft = badOutcomesLeft,
				# badOutcomesRight = badOutcomesRight,
				causalJudgment = causalJudgment);
				# judgmentOrder = judgmentOrder);
		
			newajaxmessage.put()
			self.response.out.write(json.dumps(({'blah': 'blah'}))) # not sure what this does?

		else:
			logging.info('UPDATING CURRENT')
			obj = que.get()
			
			# user properties
			obj.user=self.session['userkey']
			obj.usernum = usernum
			obj.account = self.session['account']				
			# scenario properties
			obj.scenario = scenario
			# obj.condition = self.session['conditions'][self.session['scenario']]
			# drug properties
			# obj.leftDrugName = drugA_Name
			# obj.rightDrugName = drugB_Name
			# obj.leftDrugRarity = leftDrugRarity # DO THESE
			# obj.rightDrugRarity = rightDrugRarity
			# obj.leftDrugColor = leftDrugColor
			# obj.rightDrugColor = rightDrugColor
			# leftNumberBad = leftNumberBad, Not this handler
			# rightNumberBad = rightNumberBad, Not this handler
			# goodOutcomesLeft = goodOutcomesLeft,
			# goodOutcomesRight = goodOutcomesRight,
			# badOutcomesLeft = badOutcomesLeft,
			# badOutcomesRight = badOutcomesRight,
			obj.causalJudgment = causalJudgment
			# obj.judgmentOrder = judgmentOrder

			obj.put()
			self.response.out.write(json.dumps(({'blah': 'blah'}))) # ?


###############################################################################
############################## ScenarioHandler ################################
###############################################################################
# The main handler for all the "scenarios" (e.g., one patient)
class ScenarioHandler(webapp.RequestHandler):
	def get(self):
		self.session = get_current_session()
		logging.info("THIS IS A TEST")


		try:
			scenario = self.session['scenario']

			if scenario == 0:
				drugs = [self.session['drugNames'][0], self.session['drugNames'][1]]
				drugColors = [self.session['drugColors'][0], self.session['drugColors'][1]]
			else:
				drugs = [self.session['drugNames'][2], self.session['drugNames'][3]]
				drugColors = [self.session['drugColors'][2], self.session['drugColors'][3]]

			condition = self.session['conditions'][scenario]

			position = self.session['position'][scenario]

			if(condition == 'positive'):

				doRender(self, 'scenario.htm',
					{'paradigmData':self.session['posParadigmData'],
					'groupData':self.session['posGroupData'],
					'drugNames': self.session['drugNames'],
					'diseaseNames': self.session['diseaseNames'],
					'condition': condition,
					'scenario': self.session['scenario'],
					'drugs': drugs,
					'drugColors': drugColors,
					'position':position,
					'faces': self.session['faces']})
			else:
				doRender(self, 'scenario.htm',
					{'paradigmData':self.session['negParadigmData'],
					'groupData':self.session['negGroupData'],
					'drugNames': self.session['drugNames'],
					'diseaseNames': self.session['diseaseNames'],
					'condition': condition,
					'scenario': self.session['scenario'],
					'drugs': drugs,
					'drugColors': drugColors,
					'position':position,
					'faces': self.session['faces']})

		except KeyError:
			doRender(self, 'mturkid.htm',
				{'error':1})


				
	

	

# first and second judgment refers to the get/post requests, NOT ajax
class FirstJudgmentHandler(webapp.RequestHandler):
	def get(self):
		
		self.session = get_current_session()

		scenario = self.session['scenario']
		# scenario = 0 # testing

		condition = self.session['conditions'][scenario]

		if scenario == 0:
			drugs = [self.session['drugNames'][0], self.session['drugNames'][1]]
			drugColors = [self.session['drugColors'][0], self.session['drugColors'][1]]
		else:
			drugs = [self.session['drugNames'][2], self.session['drugNames'][3]]
			drugColors = [self.session['drugColors'][2], self.session['drugColors'][3]]

		position = self.session['position'][scenario]

		# self.session['testOrder'] = 1 # testing

		logging.info('TEST ORDER: '+str(self.session['testOrder']))

		if self.session['testOrder'] == 0:
			# have to pass a "progress" variable into the page so it knows which handler to post
			doRender(self, 'mJudgment.htm',
				{'drugNames': self.session['drugNames'],
				'diseaseNames': self.session['diseaseNames'],
				'drugs': drugs,
				'drugColors': drugColors,
				'position': position,
				'testOrder':self.session['testOrder'],
				'condition':condition,
				'faces': self.session['faces'],
				'memOrder':self.session['memOrder']})
		else:
			# have to pass a "progress" variable into the page so it knows which handler to post
			doRender(self, 'cJudgment.htm',
				{'drugNames': self.session['drugNames'],
				'diseaseNames': self.session['diseaseNames'],
				'drugs': drugs,
				'drugColors': drugColors,
				'position': position,
				'testOrder':self.session['testOrder']})

# class CausalJudgmentHandler(webapp.RequestHandler):
class SecondJudgmentHandler(webapp.RequestHandler):
	def get(self):
		self.session = get_current_session()

		scenario = self.session['scenario']
		# scenario = 0 # testing

		if scenario == 0:
			drugs = [self.session['drugNames'][0], self.session['drugNames'][1]]
			drugColors = [self.session['drugColors'][0], self.session['drugColors'][1]]
		else:
			drugs = [self.session['drugNames'][2], self.session['drugNames'][3]]
			drugColors = [self.session['drugColors'][2], self.session['drugColors'][3]]

		position = self.session['position'][scenario]
		condition = self.session['conditions'][scenario]

		if self.session['testOrder'] == 0:
			# have to pass a "progress" variable into the page so it knows which handler to post
			doRender(self, 'cJudgment.htm',
				{'drugNames': self.session['drugNames'],
				'diseaseNames': self.session['diseaseNames'],
				'drugs': drugs,
				'drugColors': drugColors,
				'position': position,
				'testOrder':self.session['testOrder']})
		else:
			# have to pass a "progress" variable into the page so it knows which handler to post
			doRender(self, 'mJudgment.htm',
				{'drugNames': self.session['drugNames'],
				'diseaseNames': self.session['diseaseNames'],
				'drugs': drugs,
				'drugColors': drugColors,
				'position': position,
				'testOrder':self.session['testOrder'],
				'condition':condition,
				'faces': self.session['faces'],
				'memOrder':self.session['memOrder']})

	def post(self):

		self.session = get_current_session()


		self.session['scenario'] += 1
		# self.session['scenario'] = 1 # testing
	
		scenario=self.session['scenario']		
		
		

		# does it make sense to have multiple scenarios? How long should our datasets be?
		if scenario<=NumScenarios-1: #have more scenarios to go
			disease = self.session['diseaseNames'][1]
			drugs = [self.session['drugNames'][2], self.session['drugNames'][3]]
			
			condition = self.session['conditions'][scenario]

			position = self.session['position'][self.session['scenario']]
			doRender(self, 'newscenario.htm',
				{'bonus':self.session['BonusOne'],
				'disease': disease,
				'drugs': drugs,
				'drugColors':self.session['drugColors'],
				'condition':condition,
				'position': position})
		
		else: 
			doRender(self, 'demographics.htm')



###############################################################################
############################## Small Handlers #################################
###############################################################################

class TestHandler(webapp.RequestHandler):	# handler that renders a specific page, for testing purposes
	def get(self):
		doRender(self, 'mJudgment.htm',
			{'drugNames': [0,1],
			'diseaseNames': [0,1],
			'drugs': [0,1],
			'drugColors': [0,1],
			'position': 1,
			'testOrder':0,
			'condition':'positive',
			'faces':0,
			'memOrder':0})

	

class InstructionsHandler(webapp.RequestHandler):
	def get(self):
		self.session = get_current_session()
		doRender(self, 'task.htm',
			{'faces':self.session['faces']})
				
class preScenarioHandler(webapp.RequestHandler):
	def get(self):
		self.session = get_current_session()
		disease = self.session['diseaseNames'][0]
		drugs = [self.session['drugNames'][0], self.session['drugNames'][1]]
		position = self.session['position'][self.session['scenario']]
		
		condition = self.session['conditions'][0]
		doRender(self, 'prescenario.htm',
			{'disease':disease,
			'drugs': drugs,
			'condition':condition,
			'drugColors':self.session['drugColors'],
			'position':position}) # don't need scenario, it's always 0

class DataHandler(webapp.RequestHandler):
	def get(self):

		doRender(self, 'datalogin.htm')


	def post(self):
		self.session = get_current_session()
		password=self.request.get('password')
		page = self.request.get('whichPage')

	
		if password == "gZ2BYJxfCY5SiyttS8zl":
		# if password == "": # testing

			que=db.Query(ScenarioData)
			que.order("usernum").order("scenario").order("trialNumber")
			d=que.fetch(limit=10000)
			
			que2=db.Query(User)
			que2.order("usernum")
			u=que2.fetch(limit=10000)
			
			que3 = db.Query(FinalJudgmentData)
			que3.order("usernum").order("scenario")
			t = que3.fetch(limit=10000)

			if page == 'scenario':
				doRender(
					self, 
					'data.htm',
					{'d':d})
			
			elif page == 'user':
				doRender(
					self, 
					'userData.htm',
					{'u':u})

			else:
				doRender(self, 'ajaxTest.htm',
					{'t':t})
			
			# elif page == 'causalTest':
			# 	doRender(self, 'ajaxCausalTest.htm',
			# 		{'c':c})
		else:
			doRender(self, 'dataloginfail.htm')




class QualifyHandler(webapp.RequestHandler):
	def get(self):
		doRender(self, 'qualify.htm')
		
class DNQHandler(webapp.RequestHandler):
	def get(self):
		doRender(self, 'do_not_qualify.htm')    

##############################################################################
############################ DemographicsHandler #############################
##############################################################################
# This handler is a bit confusing - it has all this code to calculate the
# correct race number

class DemographicsHandler(webapp.RequestHandler):
	def get(self):
		doRender(self, 'demographics.htm')
		
	def post(self):
		self.session=get_current_session()
		bonus = self.session['BonusOne']+self.session['BonusTwo']
		try:
			
		
			sex=int(self.request.get('sex'))
			ethnicity=int(self.request.get('ethnicity'))
			racel=map(int,self.request.get_all('race')) #race list
			
			age=int(self.request.get('ageInput'))

			logging.info("race list")   
			logging.info(racel)

			rl1=int(1 in racel)
			rl2=int(2 in racel)
			rl3=int(3 in racel)
			rl4=int(4 in racel)
			rl5=int(5 in racel)
			rl6=int(6 in racel)
			rl7=int(7 in racel)
			
	#Amer Indian, Asian, Native Hawaiian, Black, White, More than one, No Report
	#race_num is a number corresponding to a single race AmerInd (1) - White(5)
			race_num=rl1*1+rl2*2+rl3*3+rl4*4+rl5*5
			
			morethanonerace=0
			for i in [rl1,rl2,rl3,rl4,rl5]:
					if i==1:
							morethanonerace+=1
			if rl6==1:
					morethanonerace+=2
					
			if rl7==1:  #dont want to report
					race=7
			elif morethanonerace>1:
					race=6
			elif morethanonerace==1:
					race=race_num
			
			logging.info("race")
			logging.info(race)
			
			
			
			Completion_Code=random.randint(10000000,99999999)
			
			
			obj = User.get(self.session['userkey']);
			# obj.Completion_Code = Completion_Code
			obj.sex = sex
			obj.ethnicity = ethnicity
			obj.race = race
			obj.age = age
			obj.put();
			
			
			# self.session.__delitem__('usernum')
			# self.session.__delitem__('username')
			# self.session.__delitem__('userkey')
			# self.session.__delitem__('scenario')
			# self.session.__delitem__('datalist')

			self.session.__delitem__('account')
			# self.session.__delitem__('BonusOne')
			# self.session.__delitem__('BonusTwo')
			self.session.__delitem__('conditions')
			self.session.__delitem__('diseaseNames')
			self.session.__delitem__('drugColors')
			self.session.__delitem__('drugNames')
			self.session.__delitem__('faces')
			self.session.__delitem__('negGroupData')
			self.session.__delitem__('negParadigmData')
			self.session.__delitem__('posGroupData')
			self.session.__delitem__('posParadigmData')
			self.session.__delitem__('position')
			self.session.__delitem__('runningBonuses')
			self.session.__delitem__('scenario')
			self.session.__delitem__('testOrder')
			self.session.__delitem__('trialGuesses')
			self.session.__delitem__('userkey')
			self.session.__delitem__('usernum')

			
			
			doRender(self, 'logout.htm',
				{'bonus':bonus})
		except:
			doRender(self, 'logout.htm',
				{'bonus':bonus})
		

###############################################################################
############################### MturkIDHandler ################################
###############################################################################
	  
class MturkIDHandler(webapp.RequestHandler):
	def get(self):
		doRender(self, 'mturkid.htm',
			{'error':0})

	def post(self):
		
		usernum = create_or_increment_NumOfUsers()

		browser = self.request.get('browser')
		account = self.request.get('ID')
		logging.info('BROWSER: '+browser)
		
		#Make the data that this subject will see.
		#It is made once and stored both in self.session and in database				

		# import data
		f = open('data/rareNeg.csv', 'rU')
		mycsv = csv.reader(f)
		mycsv = list(mycsv)

	
		# chunk in 4 groups of 12
		for i in range(0, 4):
			tempOutcomeData = []
			tempGroupData = []
			for j in range(0,6):
				tempOutcomeData.append(int(mycsv[(i*6)+j+0][0]))
				tempGroupData.append(int(mycsv[(i*6)+j+0][1]))
			for j in range(0,2):
				tempOutcomeData.append(int(mycsv[(i*2)+j+24][0]))
				tempGroupData.append(int(mycsv[(i*2)+j+24][1]))
			for j in range(0,3):
				tempOutcomeData.append(int(mycsv[(i*3)+j+32][0]))
				tempGroupData.append(int(mycsv[(i*3)+j+32][1]))
			for j in range(0,1):
				tempOutcomeData.append(int(mycsv[(i*1)+j+44][0]))
				tempGroupData.append(int(mycsv[(i*1)+j+44][1]))

			if i == 0:
				TOD1 = tempOutcomeData
				TGD1 = tempGroupData
			elif i == 1:
				TOD2 = tempOutcomeData
				TGD2 = tempGroupData
			elif i == 2:
				TOD3 = tempOutcomeData
				TGD3 = tempGroupData
			elif i == 3:
				TOD4 = tempOutcomeData
				TGD4 = tempGroupData

		# test1 - test4 are the chunks. Now I need to randomize order in each

		order1 = [0,1,2,3,4,5,6,7,8,9,10,11]
		order2 = order1
		order3 = order1
		order4 = order1

		random.shuffle(order1)
		random.shuffle(order2)
		random.shuffle(order3)
		random.shuffle(order4)

		OD1 = []
		OD2 = []
		OD3 = []
		OD4 = []

		GD1 = []
		GD2 = []
		GD3 = []
		GD4 = []

		for i in range(0, len(order1)):
			OD1.append(TOD1[order1[i]])
			GD1.append(TGD1[order1[i]])

			OD2.append(TOD1[order2[i]])
			GD2.append(TGD1[order2[i]])

			OD3.append(TOD1[order3[i]])
			GD3.append(TGD1[order3[i]])

			OD4.append(TOD1[order4[i]])
			GD4.append(TGD1[order4[i]])

		negParadigmData = OD1+OD2+OD3+OD4
		negGroupData = GD1+GD2+GD3+GD4

		# if valence is negative (negative ICs), most of these will be positive
		conditions = ['positive', 'negative']
		random.shuffle(conditions) # conditions in random order

		# same for positive rare condition:
		# import data
		f = open('data/rarePos.csv', 'rU')
		mycsv = csv.reader(f)
		mycsv = list(mycsv)

	
		# chunk in 4 groups of 12
		for i in range(0, 4):
			tempOutcomeData = []
			tempGroupData = []
			for j in range(0,6):
				tempOutcomeData.append(int(mycsv[(i*6)+j+0][0]))
				tempGroupData.append(int(mycsv[(i*6)+j+0][1]))
			for j in range(0,2):
				tempOutcomeData.append(int(mycsv[(i*2)+j+24][0]))
				tempGroupData.append(int(mycsv[(i*2)+j+24][1]))
			for j in range(0,3):
				tempOutcomeData.append(int(mycsv[(i*3)+j+32][0]))
				tempGroupData.append(int(mycsv[(i*3)+j+32][1]))
			for j in range(0,1):
				tempOutcomeData.append(int(mycsv[(i*1)+j+44][0]))
				tempGroupData.append(int(mycsv[(i*1)+j+44][1]))

			if i == 0:
				TOD1 = tempOutcomeData
				TGD1 = tempGroupData
			elif i == 1:
				TOD2 = tempOutcomeData
				TGD2 = tempGroupData
			elif i == 2:
				TOD3 = tempOutcomeData
				TGD3 = tempGroupData
			elif i == 3:
				TOD4 = tempOutcomeData
				TGD4 = tempGroupData

		# test1 - test4 are the chunks. Now I need to randomize order in each

		order1 = [0,1,2,3,4,5,6,7,8,9,10,11]
		order2 = order1
		order3 = order1
		order4 = order1

		random.shuffle(order1)
		random.shuffle(order2)
		random.shuffle(order3)
		random.shuffle(order4)

		OD1 = []
		OD2 = []
		OD3 = []
		OD4 = []

		GD1 = []
		GD2 = []
		GD3 = []
		GD4 = []

		for i in range(0, len(order1)):
			OD1.append(TOD1[order1[i]])
			GD1.append(TGD1[order1[i]])

			OD2.append(TOD1[order2[i]])
			GD2.append(TGD1[order2[i]])

			OD3.append(TOD1[order3[i]])
			GD3.append(TGD1[order3[i]])

			OD4.append(TOD1[order4[i]])
			GD4.append(TGD1[order4[i]])

		posParadigmData = OD1+OD2+OD3+OD4
		posGroupData = GD1+GD2+GD3+GD4

	
		# randomize left/right for drug A/B at the level of the scenario
		# default is 0, A on the left. 1 is A on the right
		position = []
		for i in range(0, NumScenarios):
			position.append(random.choice([0,1]))

		# order of asking (memory vs causal)
		testOrder = random.choice([0,1])

		# within memory, order of asking C|E or E|C
		# 0 is E|C first
		memOrder = random.choice([0,1])

		# testOrder = 0: memory first
		# memOrder = 0: ask about outcomes given drug first

		# TO = 0, MO = 0: E|C, C|E, Causal
		# TO = 0, MO = 1: C|E, E|C, Causal
		# TO = 1, MO = 0: Causal, E|C, C|E
		# TO = 1, MO = 1: Causal, C|E, E|C


		# counterbalance left/right for faces at the level of the participant
		if usernum % 2 == 0:
			faces = 0 # good on the left
		else:
			faces = 1 # good on the right

		# disease names
		diseaseNames = ['Duastea', 'Stectosis']
		random.shuffle(diseaseNames)

		# drug names
		# drugNames = ['XF702', 'BT339', 'GS596', 'PR242']
		drugNames = [0,1,2,3]
		random.shuffle(drugNames)
		
		# drugColors = ['blue', 'green', 'orange', 'purple']
		drugColors = [0,1,2,3]
		random.shuffle(drugColors)

		trialGuesses = [0]*LengthOfData

		# running tally of bonuses
		runningBonuses = [0,0]

		newuser = User(
			usernum=usernum, 
			account=account, 
			browser=browser, 
			sex=0,
			ethnicity=0,
			race=0,
			age=0,
			bonusAmt=0,
			testOrder = testOrder,
			memOrder = memOrder); 

		# dataframe modeling, but I'm not sure what exactly
		userkey = newuser.put()
		
		# this stores the new user in the datastore
		newuser.put()

		# store these variables in the session
		self.session=get_current_session() #initialize sessions

		self.session['account']				= account
		self.session['BonusOne']			= 0
		self.session['BonusTwo']			= 0
		self.session['conditions']			= conditions
		self.session['diseaseNames']		= diseaseNames
		self.session['drugColors']			= drugColors
		self.session['drugNames']			= drugNames
		self.session['faces']				= faces
		self.session['negGroupData']		= negGroupData
		self.session['negParadigmData']		= negParadigmData
		self.session['posGroupData']		= posGroupData
		self.session['posParadigmData']		= posParadigmData
		self.session['position']			= position
		self.session['runningBonuses']		= runningBonuses
		self.session['scenario']			= 0
		self.session['testOrder']			= testOrder
		self.session['trialGuesses']		= trialGuesses
		self.session['userkey']				= userkey
		self.session['usernum']				= usernum
		self.session['memOrder']			= memOrder
		
		
		# doRender(self, 'qualify.htm') no need if we're using SONA

		doRender(self, 'task.htm',
			{'faces':self.session['faces']})


		# If got no response back from http://www.mturk-qualify.appspot.com
		# else:
		#   error="The server is going slowly. Please reload and try again."
		#   self.response.out.write(result.content)

	
###############################################################################
############################### MainAppLoop ###################################
###############################################################################

application = webapp.WSGIApplication([
	('/ajax', AjaxHandler),
	# ('/AjaxOutcomeMemoryTest', AjaxOutcomeMemoryHandler),
	('/AjaxMemoryTest', AjaxMemoryHandler),
	('/AjaxCausalTest', AjaxCausalHandler),
	('/preScenario', preScenarioHandler),
	('/instructions', InstructionsHandler),
	('/data', DataHandler),
	('/do_not_qualify', DNQHandler),
	('/scenario', ScenarioHandler),
	('/firstJudgment', FirstJudgmentHandler),
	('/secondJudgment', SecondJudgmentHandler),
	('/qualify', QualifyHandler),
	('/demographics', DemographicsHandler),
	('/mturkid', MturkIDHandler), 
	('/.*',      MturkIDHandler)],  #default page
	# ('/.*',      TestHandler)],  # testing
	debug=True)

def main():
		run_wsgi_app(application)

if __name__ == '__main__':
	main()


