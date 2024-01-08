'''
Author: Fayiz Ali
Date created: Jan 7, 2024
'''

#refereced syntax from https://flask.palletsprojects.com/en/3.0.x/quickstart/, implemented on my own
#https://medium.com/google-cloud/building-a-flask-python-crud-api-with-cloud-firestore-firebase-and-deploying-on-cloud-run-29a10c502877 
from flask import Flask, request, jsonify
from firebase_admin import credentials, firestore, auth, exceptions, initialize_app
import requests
import os
from dotenv import load_dotenv

app = Flask(__name__) #initialize the main central object

#initialize firebase
cred = credentials.Certificate('./config/key.json')
firebaseApp = initialize_app(cred)

#initialize firestore
db = firestore.client()

approvedListingsRef = db.collection('ApprovedListings')
unapprovedListingsRef = db.collection('UnapprovedListings')

#initialize firebase authentication
firebase_auth:auth.Client = auth.Client(firebaseApp)

successDict = {
    'status': 200
}

errorDict = {
    'status': 500
}

incompleteDict = {
    'status': 422
}

unauthorizedDict = {
    'status': 403
}

ADMIN_TOKEN:str = 'NtoRDfiE7vXf1YRKdC3vWy1on9X2'
API_KEY:str|None = os.getenv('API_KEY')

#https://stackoverflow.com/questions/14993318/catching-a-500-server-error-in-flask
@app.errorhandler(500)
def handleError(error):
    return errorDict

@app.route("/")
def sendDefault():
    return "<h2>Home Page</h2>"

@app.route("/login", methods=['POST'])
def login():
    try:
        email = request.form.get('email')
        password = request.form.get('password')

        bodyDict = {
            'email': email,
            'password': password
        }

        #syntax referenced from https://www.educative.io/answers/how-to-make-api-calls-in-python, implemented on my own
        response = requests.post(f'https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword?key={API_KEY}', json=(bodyDict))
        responseJson = response.json()

        if('idToken' in responseJson):
            print('Success')
            return jsonify(responseJson)
        
        if(responseJson['error']['code']==400):
            return unauthorizedDict

        raise Exception('Unknown error occurred')
    except Exception as e:
        print(f'Exception occurred while logging in {e}')
        raise Exception(e)

#https://firebase.google.com/docs/reference/admin/python/firebase_admin.auth 
@app.route("/sign-up",  methods=['POST'])
def signUp():
    try:
        email = request.form.get('email')
        password = request.form.get('password')

        if(email==None or password==None):
            return incompleteDict

        firebase_auth.create_user(email=email, password=password)
        return successDict
        
    except exceptions.FirebaseError as e:
        print('Error occurred while creating user FirebaseError: {e}')
        if(type(e) is auth.EmailAlreadyExistsError):
            return {
                'status': 409
            }
        else:
            raise Exception(e)     
    except ValueError as e:
        print('Error occurred while creating user ValueError: {e}')
        raise Exception(e)
    except Exception as e:
        print(f'Exception occurred while creating user: {e}')
        raise Exception(e)

@app.route("/create-connection", methods=['POST'])
def createConnection():
    try:
        title = request.form.get('title')
        description = request.form.get('description')
        authorId = request.form.get('id')
        type = request.form.get('type')
        link = request.form.get('link')
        location = request.form.get('location')

        responseDict = {
            'title': title,
            'description': description,
            'authorId': authorId,
            'type': type,
            'link': link,
            'location': location,
        }

        if(title == None or description == None or authorId == None or type == None or location == None):
            return incompleteDict

        unapprovedListingsRef.document().create(responseDict)

        return successDict
    except Exception as e:
        print(f"An error occurred while creating connection: {e}")
        raise Exception(e)

@app.route("/approve-connection", methods=['POST'])
def approveConnection():
    try:
        listingId = None
        
        if(checkIfHasAdminAccess()):
            listingId = request.form.get('listingId')
            unapprovedDocument = unapprovedListingsRef.document(listingId).get()

            approvedListingsRef.document(listingId).create((unapprovedDocument.to_dict()))

            unapprovedListingsRef.document(listingId).delete()

            return successDict
        else:
            return unauthorizedDict
    except Exception as e:
        print(f"An error occurred while approving connection with id {listingId} : {e}")
        raise Exception(e)

@app.route("/get-connections", methods=['GET'])
def getConnections():
    try:
        shouldFetchUnapprovedRequests:bool = (request.args.get('unapproved') == 'true')

        if(shouldFetchUnapprovedRequests):
            if(checkIfHasAdminAccess()):
                docs = unapprovedListingsRef.stream()
            else:
                return unauthorizedDict
        else:
            docs = approvedListingsRef.stream()

        allListings = []
        for doc in docs:
            modifiedDoc = doc.to_dict()
            modifiedDoc['id'] = doc.id
            
            allListings.append(modifiedDoc)

        return allListings
    except Exception as e:
        print(f"An error occurred while getting connections: {e}")
        raise Exception(e)
    

def checkIfHasAdminAccess() -> bool:
    return (request.form.get('token') == ADMIN_TOKEN)