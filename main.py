'''
Author: Fayiz Ali
Date created: Jan 7, 2024
Description: 
- Backend for CommunityConnectionApp. This backend is made using Flask. 
- It uses Rest APIs to communicate with frontend and firebase admin sdk + google apis for firebase communication.
- Firebase authentication is used for OAuth2.0 authentication and authorization.
- Firebase cloud firestore nosql realtime databse is used for storing data.
- The rationale for creating this backend was to prevent access to Firebase authentication and Firestore database from frontend, so that it is not misused or hacked [like someone trying to add spam data or something in database]

Even though this backend is not primarily for marking, as the concept of backend has not been taught in class, but still:
This project [backend] deserves Level 4 because:
- All of this backend has been created using Flask, which has not been taught in class
- Uses REST Apis
- Implements Authentication and authorization [admin vs non admin]
- Error handling and http codes get returned on error
- Uses JSON
- Integrates with Firebase authentication and realtime database [Firestore]
- Performs CRUD operation with Firestore
- Uses .env file to hide credentials
- Uses .gitignore to prevent config and credential files from being checked in
- Uses api middlewares
- Uses f strings
- Created get and post APIs
- Data modelling done in firestore
'''

#refereced syntax from https://flask.palletsprojects.com/en/3.0.x/quickstart/, implemented on my own
#refereced syntax from https://medium.com/google-cloud/building-a-flask-python-crud-api-with-cloud-firestore-firebase-and-deploying-on-cloud-run-29a10c502877, implemented on my own
from flask import Flask, request, jsonify
from firebase_admin import credentials, firestore, auth, exceptions, initialize_app
import requests
import os
from dotenv import load_dotenv
from collections.abc import Callable

app = Flask(__name__) #initialize the main central object

#initialize firebase
cred = credentials.Certificate('./config/key.json')
firebaseApp = initialize_app(cred)

#initialize firestore [realtime database]
db = firestore.client()

#references of collections in firestore.
approvedListingsRef = db.collection('ApprovedListings') #primarily displayed to end user . Listings that have been approved with the admin only end up here
unapprovedListingsRef = db.collection('UnapprovedListings')#displayed to admin also, so that the admin can approve these unapproved listings

#initialize firebase authentication
firebase_auth:auth.Client = auth.Client(firebaseApp)

#dictionary for http codes. To be sent as API call results

#sent when everything goes well 
successDict = {
    'status': 200
}

#sent if some unknown error happens
errorDict = {
    'status': 500
}

#sent if incomplete data was sent from frontend to even process the request
incompleteDict = {
    'status': 400
}

#sent if the auth Token is expired, i.e., the user needs to re-login or the user credentials are wrong
unauthorizedDict = {
    'status': 403
}

#.env is an environment file, usually used to keep fields that are configurable. Not checked in, so it contains API keys and admin UID. Needs manual configuration
load_dotenv('./config/.env') #load the file

#get these fields
#syntax referenced from https://stackoverflow.com/questions/40216311/reading-in-environment-variables-from-an-environment-file, implemented on my own
ADMIN_TOKEN:str|None = os.getenv('ADMIN_UID')#used for checking whether the user [authtoken] is an admin or not 
API_KEY:str|None = os.getenv('API_KEY')#used for making calls to google apis for firebase login

uid = None
#syntax referenced from https://stackoverflow.com/questions/14993318/catching-a-500-server-error-in-flask, implemented on my own

'''
description: error handler in case any unknown error happens
takes nothing
returns dictionary with http code as response
'''
@app.errorhandler(500)
def handleError(error):
    return errorDict

#middleware
'''
description: middleware: 
- intervenes before any API call is processed. Called for every API call
- helps detect User ID from the oauth token coming from frontend
- wouldn't check auth token in case of login or signup api, as the token has not been assigned yet.

takes nothing
returns dictionary with http code as response
'''
@app.before_request
def verifyTokenMiddleware():
    #extracted from auth token
    global uid
    uid = None

    #to get different segments of API call URL
    urlSegment = request.path
    if(urlSegment != '/login' and urlSegment != '/sign-up'):
        #prevents auth token checking in case API call is for logging in or signing up, as the token is anyways not assigned then
        
        #if no token is found, then return incomplete request
        if(request.authorization == None):
            return incompleteDict
        
        #extract auth token
        tokenId = request.authorization.token
        
        if(tokenId==None):
            #no token, return 400 http code.
            return unauthorizedDict
        else:
            try:
                #verify if token is not fake and not expired. Also extracts User ID from auth token code
                uid = verifyIfTokenIsValid(tokenId)
            except Exception as e:
                #error handling
                print(f'Exception occurred while verifying tokenId: {e}')
                return unauthorizedDict

'''
description: Just to check if the backend is up or not. default path
takes nothing
returns html to just see if the backend is up or not
'''
@app.route("/")
def sendDefault():
    return "<h2>Home Page</h2>"

'''
description: login api endpoint. helps login
API takes in request body in form format:
    email:str
    password:str
returns JSON
    'status': int,
    'data': response json from firebase
'''
@app.route("/login", methods=['POST'])
def login():
    try:
        #extract these two data from request body
        email = request.form.get('email')
        password = request.form.get('password')

        #payload for google api call
        bodyDict = {
            'email': email,
            'password': password,
            'returnSecureToken': True #helps get the correct authToken back for this user
        }

        #syntax referenced from https://www.educative.io/answers/how-to-make-api-calls-in-python, implemented on my own
        response = requests.post(f'https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword?key={API_KEY}', json=(bodyDict)) #login call to Google API
        responseJson = response.json()#deserialize json and get dictionary

        print('Logging in')
        if('idToken' in responseJson):
            #success
            print('Success')

            #if the authtoken returned matches the preset ADMIN_TOKEN, then the user is an admin and should have admin privileges
            responseJson['isAdmin'] = (responseJson['localId'] == ADMIN_TOKEN) 

            #return this back to frontend
            result = {
                'status': 200,
                'data': responseJson
            }
            return jsonify(result)
        
        #user credentials are wrong
        if(responseJson['error']['code']==400):
            print('Unauthenticated')
            return unauthorizedDict

        #if nothing happened, no success, then something unexpected happened
        raise Exception('Unknown error occurred')
    except Exception as e:
        #error handling. Goes to error handler declared in the beginning of this file
        print(f'Exception occurred while logging in {e}')
        raise Exception(e)

'''
description: signup/register api endpoint. helps register the user
API takes in request body in form format:
    email:str
    password:str
returns JSON
    'status': int,
'''
#syntax referenced from https://firebase.google.com/docs/reference/admin/python/firebase_admin.auth, implemented on my own
@app.route("/sign-up",  methods=['POST'])
def signUp():
    try:
        #extract these two data from request body
        email = request.form.get('email')
        password = request.form.get('password')

        #if no email or password given, then return 400 status
        if(email==None or password==None):
            return incompleteDict

        #create user with firebase authentication
        firebase_auth.create_user(email=email, password=password)
        return successDict #if no exception raised, then the user was created successfully
        
    except exceptions.FirebaseError as e:
        print('Error occurred while creating user FirebaseError: {e}')
        if(type(e) is auth.EmailAlreadyExistsError):
            #email already exists/user already registered
            return {
                'status': 409
            }
        else:
            #unknown error, Goes to error handler declared before
            raise Exception(e)     
    except ValueError as e:
        #unknown error, Goes to error handler declared before
        print('Error occurred while creating user ValueError: {e}')
        raise Exception(e)
    except Exception as e:
        #unknown error, Goes to error handler declared before
        print(f'Exception occurred while creating user: {e}')
        raise Exception(e)

'''
description: create-connection api endpoint. helps create connection listing in database
API takes in request body in form format:
    title:str
    description:str
    type:str, should be either 'whatsapp' or 'facebook'
    link:str    
    location:str
returns JSON
    'status': int,
'''
@app.route("/create-connection", methods=['POST'])
def createConnection():
    try:
        #extract data from form request body
        title = request.form.get('title')
        description = request.form.get('description')
        authorId = uid #uid as extracted from authtoken already
        type = request.form.get('type')
        link = request.form.get('link')
        location = request.form.get('location')

        #payload for firestore
        responseDict = {
            'title': title,
            'description': description,
            'authorId': authorId,
            'type': type,
            'link': link,
            'location': location,
        }

        #if inadequate info was given from frontend, return 400 http code
        if(title == None or description == None or authorId == None or type == None or location == None):
            return incompleteDict

        #create a document with auto ID, and creates a new document with with responseDict keys as fieldnames and their values as field values
        unapprovedListingsRef.document().create(responseDict)

        return successDict
    except Exception as e:
        #unknown error handled by error handler declared before
        print(f"An error occurred while creating connection: {e}")
        raise Exception(e)

'''
description: approve-connection api endpoint. helps approve connection listing in database. Admin only access
API takes in request body format:
    listingId:str id of listing to be approved
returns JSON
    'status': int,
'''
@app.route("/approve-connection", methods=['POST'])
def approveConnection():
    try:
        listingId = None
        
        if(checkIfHasAdminAccess()):
            listingId = request.form.get('listingId')#get from form data request body 

            unapprovedDocument = unapprovedListingsRef.document(listingId).get()#get the listing data by listingId [documentId] to be approved

            approvedListingsRef.document(listingId).create((unapprovedDocument.to_dict()))#add to approved collection

            unapprovedListingsRef.document(listingId).delete()#delete this from unapproved collection, as it is now approved

            return successDict
        else:
            #the person is not an admin and doesn't have access to this action.
            return unauthorizedDict
    except Exception as e:
        #unknown error handled by error handler declared before
        print(f"An error occurred while approving connection with id {listingId} : {e}")
        raise Exception(e)

'''
description: get-connection api endpoint. helps get all connection listings from database
API takes:
    unapproved: bool in form of query parameter. If true, this means admin access connections are also returned
returns JSON
    'status': int,
    'data': response from firebase in form of list of JSON of all documents that fit the criteria requested
'''
@app.route("/get-connections", methods=['GET'])
def getConnections():
    try:
        shouldFetchUnapprovedRequests:bool = (request.args.get('unapproved') == 'true') #see if the user is requestin admin level connections or not
       
        isAdmin:bool = False

        #checks to see if user id given matches with admin UID
        if(shouldFetchUnapprovedRequests):
            if(checkIfHasAdminAccess()):
                isAdmin = True
            else:
                #unauthorized. User is not an admin!!!
                return unauthorizedDict
        
        allListings = []
        docs = None
        if(isAdmin):
            #get all unapproved documents
            docs = unapprovedListingsRef.stream()
        else:
            #get only those unapproved documents that belong to that author/UID
            docs = unapprovedListingsRef.where('authorId', '==', uid).get()

        '''
        description: callback for mutating a document dictionary fields with desirable information
        takes:deserialized dictionary of document and the original serialized document from firestore
        returns:modified doc in dictionary format
        '''
        def changeFieldParamsForUnverfiedDocs(doc, modifiedDoc):
            modifiedDoc['id'] = doc.id#listingId
            modifiedDoc['approved'] = False#as this was fetched from unapprovedCollection. Requires approval by admin

            return modifiedDoc

        allListings += convertDocumentsIntoResponseList(docs, changeFieldParamsForUnverfiedDocs)#concatenate response list

        '''
        description: callback for mutating a document dictionary fields with desirable information
        takes:deserialized dictionary of document and the original serialized document from firestore
        returns:modified doc in dictionary format
        '''
        def changeFieldParamsForVerifiedDocs(doc, modifiedDoc):
            modifiedDoc['id'] = doc.id #listingId
            modifiedDoc['approved'] = True #as this was fetched from approvedCollection. Approved by admin already

            return modifiedDoc

        #get documents that are approved from approved collection
        docs = approvedListingsRef.stream()
        allListings += convertDocumentsIntoResponseList(docs, changeFieldParamsForVerifiedDocs)#concatenate response list

        #success result
        result = {
            'status':200,
            'data': allListings
        }

        return result
    except Exception as e:
        #error handling incase of unexpected error. Goes to error handler at beginning of file
        print(f"An error occurred while getting connections: {e}")
        raise Exception(e)

#************NON API HELPER METHODS*************
'''
description: goes over each document and deserializes it. Also, helps do a callback over each document
takes 
    docs:list of documents fetched from firestore collection
    changeFieldParams:callback that should return a modified doc, and is given deserialized dictionary of document and the original serialized document
returns all modified document in form of list[dict]
'''
def convertDocumentsIntoResponseList(docs, changeFieldParams):
    allListings = []

    #go over all docs
    for doc in docs:
        modifiedDoc = doc.to_dict()#convert to dictionary
        modifiedDoc = changeFieldParams(doc, modifiedDoc)#helps carry any changes to each document
        
        allListings.append(modifiedDoc)
    
    return allListings

'''
description: checks if the user is an admin or not
takes nothing
returns True if user is admin or False if the user is not
'''
def checkIfHasAdminAccess() -> bool:
    return (uid == ADMIN_TOKEN)

'''
description: checks if the token is valid or not
takes token:str
returns userId:str extracted from the token
'''
def verifyIfTokenIsValid(tokenId:str) -> str|None:
    decodedToken = auth.verify_id_token(tokenId)
    return decodedToken['uid']