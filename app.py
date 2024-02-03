import firebase_admin
from firebase_admin import credentials, firestore, storage, auth
from flask import Flask, jsonify, render_template, request, redirect, url_for,session
import pyrebase
import requests
from functools import wraps 
from google.cloud.firestore_v1.base_query import FieldFilter
from flask_mail import Message, Mail
import random
import cv2
import base64
import numpy as np

app = Flask(__name__)
app.secret_key = 'roomies' 
cred = credentials.Certificate("common/roomies-166f5-firebase-adminsdk-h1537-a0ab5ed914.json")
firebase_admin.initialize_app(cred, {'storageBucket': 'roomies-166f5.appspot.com'})
db = firestore.client()
bucket = storage.bucket()
firebaseConfig = {
    'apiKey': "AIzaSyAp1yMhDs5N5RmPW4rhVlUJ7VtTVfWvty8",
    'authDomain': "roomies-166f5.firebaseapp.com",
    'projectId': "roomies-166f5",
    'storageBucket': "roomies-166f5.appspot.com",
    'messagingSenderId': "1069795528716",
    'appId': "1:1069795528716:web:8e5a61abe0510933cb9e29",
    'measurementId': "G-5DH42NYCQ4",
    'databaseURL': "https://roomies-166f5-default-rtdb.asia-southeast1.firebasedatabase.app"
  }

firebase = pyrebase.initialize_app(firebaseConfig)
storage = firebase.storage
auth = firebase.auth()  

app.config.update(dict(
    DEBUG = True,
    MAIL_SERVER = 'smtp.gmail.com',
    MAIL_PORT = 587,
    MAIL_USE_TLS = True,
    MAIL_USE_SSL = False,
    MAIL_USERNAME = 'roomiesaps@gmail.com',
    MAIL_PASSWORD = 'irsr gxzz vquh bejg',
))

mail = Mail(app)
face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')

def get_user_preferences(email):
    user_preferences = {}
    user_ref = db.collection('RoommatePreferences')
    doc_ref = user_ref.where(filter=FieldFilter('Email','==',email)).limit(1).stream()
    user_ref1 = db.collection('Users')
    doc_ref1 = user_ref1.where(filter=FieldFilter('Email','==',email)).limit(1).stream()
    for doc in doc_ref:
        user_preferences.update(doc.to_dict())
    for doc in doc_ref1:
        user_preferences.update(doc.to_dict())
    return user_preferences

def generate_otp():
    otp = ''.join([str(random.randint(0, 9)) for _ in range(6)])
    print("generation done")
    return otp

def send_otp_email(email, otp):
    msg = Message('Email Verification OTP for ROOMIES',sender='roomiesaps@gmail.com', recipients=[email])
    msg.body = f'Hi,\nThank you for choosing ROOMIES. Use the following OTP to complete your Sign Up procedures.\nOTP is valid for 5 minutes.\n\nOTP: {otp}\n\nRegards,\nROOMIES Team\n\nNote: Please do not respond to this email.'
    mail.send(msg)
    print("sent")

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/about')
def about():
    return render_template('about.html')

def verify_recaptcha(token):
    api_url = 'https://www.google.com/recaptcha/api/siteverify'
    
    response = requests.post(api_url, {
        'secret': "6LctPhkpAAAAAOqyWBd3GhSZj9wQ56m6qg5DFluc",
        'response': token
    })

    result = response.json()
    return result['success']


@app.route('/whyroommatefinder')
def whyroommatefinder():
    return render_template('about.html')

@app.route('/signup')
def signup():
    return render_template('signup.html')

@app.route('/login')
def login():
    return render_template('index2.html')

@app.route('/facedetect', methods=['GET','POST'])
def facedetect():
    if request.method == 'POST':
        # Decode the base64 encoded image data sent from the client-side
        image_data = request.form['image_data'].split(",")[1]
        # Convert the base64 image data to bytes
        image_bytes = bytes(image_data, 'utf-8')
        # Decode the bytes to an image array
        nparr = np.frombuffer(base64.b64decode(image_bytes), np.uint8)
        image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        # Convert the image to grayscale (required for face detection)
        gray_image = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        # Perform face detection
        faces = face_cascade.detectMultiScale(gray_image, scaleFactor=1.1, minNeighbors=5, minSize=(30, 30))
        if len(faces) > 0:
            print("success!")
            return redirect(url_for('preferences'))
        else:
            return "No human user detected. Make sure your face is clearly visible and you are in a well lit place. \nPlease capture another image."
    return render_template('facedetect1.html')

@app.route('/signup1', methods=['GET', 'POST'])
def signup1():
    username = request.form.get('username')
    fname = request.form.get('fname')
    lname = request.form.get('lname')
    email = request.form.get('mail')
    password = request.form.get('password')
    phone_number = request.form.get('phone')
    age = request.form.get('age')
    try:
        user = auth.create_user_with_email_and_password(
            email=email,
            password=password
        )

        otp = generate_otp()

        session['user_info'] = {
            'username': username,
            'email': email,
            'phone_number': phone_number,
            'fname': fname,
            'lname': lname,
            'age': age,
            'otp': otp
        }
        
        send_otp_email(email, otp)

        print('Successfully created new user:', user)
        return redirect(url_for('verify_email'))

    except Exception as e:
        print('Error creating user:', e)
        return render_template('signup.html', error=e)
    
@app.route('/verify_email', methods=['GET', 'POST'])
def verify_email():
    if request.method == 'POST':
        # Verify the OTP entered by the user
        entered_otp = request.form.get('otp')
        session_otp = session.get('user_info').get('otp')
        
        if entered_otp == session_otp:
            # OTP matched, proceed with signup
            session.pop('user_info')['otp']
            return redirect(url_for('facedetect'))
        else:
            # Incorrect OTP, display error message
            return render_template('verify_email.html', error='Incorrect OTP. Please try again.')

    return render_template('verify_email.html')

@app.route('/preferences', methods=['GET', 'POST'])
def preferences():
    if request.method == 'POST':
        bio = request.form.get('bio')
        location = request.form.get('location')
        gender = request.form.get('Gender')
        habits = request.form.get('habits')
        food_preference = request.form.get('food')
        profession = request.form.get('profession')
        religion = request.form.get('religion')
        sleep_schedule = request.form.get('sleepschedule')
        cleanliness_habits = request.form.get('cleanlinessH')
        pet = request.form.get('pet')

        user_info = session.get('user_info', {})
        user_info.update({
            'bio': bio,
            'location': location,
            'gender': gender,
            'habits': habits,
            'food_preference': food_preference,
            'profession': profession,
            'religion': religion,
            'sleep_schedule': sleep_schedule,
            'cleanliness_habits': cleanliness_habits,
            'pet_friendly': pet,
        })
        
        session['user_info'] = user_info

        return redirect(url_for('preferences2'))

    return render_template('preferences.html')

@app.route('/preferences2', methods=['GET', 'POST'])
def preferences2():
    if request.method == 'POST':
        activity = request.form.get('Activity')
        organized = request.form.get('organized')
        social = request.form.get('social')
        conflict = request.form.get('conflict')
        stress = request.form.get('stress')
        cultures = request.form.get('cultures')
        future = request.form.get('future')
        gatherings = request.form.get('gatherings')
        patient = request.form.get('patient')
        mood = request.form.get('mood')

        user_info = session.get('user_info', {})
        user_info.update({
            'activity': activity,
            'organized': organized,
            'social': social,
            'conflict': conflict,
            'stress': stress,
            'cultures': cultures,
            'future': future,
            'gatherings': gatherings,
            'patient': patient,
            'mood': mood,
        })
        session['user_info'] = user_info

        db.collection('Users').document(user_info['username']).set({
            'Username': user_info['username'],
            'First Name': user_info['fname'],
            'Last Name': user_info['lname'],
            'Age': user_info['age'],
            'Email': user_info['email'],
            'Phone Number': user_info['phone_number']
        })

        db.collection('RoommatePreferences').document(user_info['username']).set({
            'Username': user_info['username'],
            'Bio': user_info['bio'],
            'Accomodation Location': user_info['location'],
            'Gender': user_info['gender'],
            'Habits': user_info['habits'],
            'Food Preference': user_info['food_preference'],
            'Profession': user_info['profession'],
            'Religion': user_info['religion'],
            'Sleep Schedule': user_info['sleep_schedule'],
            'Cleanliness Habits': user_info['cleanliness_habits'],
            'Pet Friendliness': user_info['pet_friendly'],
            'Activity': user_info['pet_friendly'],
            'Organized': user_info['organized'],
            'Social': user_info['social'],
            'Conflict': user_info['conflict'],
            'Stress': user_info['stress'],
            'Cultures': user_info['cultures'],
            'Future': user_info['future'],
            'Gatherings': user_info['gatherings'],
            'Patient': user_info['patient'],
            'Mood Swings': user_info['mood'],
            'Email': user_info['email'],
        })

        session.pop('user_info', None)
        
        return redirect(url_for('dashboard'))
    
    return render_template('preferences2.html')


@app.route('/welcome', methods=['GET', 'POST'])
def welcome():
    if request.method == 'POST':
        email = request.form.get('mail')
        password = request.form.get('password')

        try:
            user = auth.sign_in_with_email_and_password(email,password)
            
            print('Successfully fetched user data', user)

            user_ref = db.collection('Users')
            doc_ref = user_ref.where(filter=FieldFilter('Email','==',email)).limit(1).stream()
            for doc in doc_ref:
                session['user'] = {
                'email': user['email'],
                'idToken': user['idToken'],
                'username':doc.id
                }


            return redirect(url_for('dashboard'))
          
        except Exception as e:
            print('Error fetching user data or invalid credentials:', e)
            return render_template('index2.html', error='Invalid credentials')
        
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

@app.route('/dashboard')
@login_required
def dashboard():
    if 'user' in session:
        user_info = session.get('user')
        if user_info:
            user_email = user_info.get('email')
        return render_template('dashboard.html', user_email=user_email)
    else:
        return redirect(url_for('index'))
    
@app.route('/profile')
@login_required
def profile():
    user_info = session.get('user')

    if user_info:
        user_email = user_info.get('email')
        print(user_info)
    
    user_preferences = get_user_preferences(user_email)  

    return render_template('profile.html', user_preferences = user_preferences)    

@app.route('/update_preferences', methods=['POST'])
def update_preferences():
    updated_preferences = request.json
    user_info = session.get('user')

    if user_info:
        username = user_info.get('username')
    try:
        doc_ref = db.collection('RoommatePreferences').document(username)
        doc_ref.update(updated_preferences)
        return jsonify({'message': 'Preferences updated successfully'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/delete_account', methods=['POST'])
def delete_account():
    try:
        # Verify the user is authenticated
        user_info = session.get('user')  
        if user_info:
            id_token = user_info.get('idToken')
        else:
            return redirect(url_for('login'))

        # Delete the user account using the UID
        auth.delete_user_account(id_token)

        # Clear the session and redirect to the index page after successful deletion
        session.pop('user', None)
        return redirect(url_for('index'))

    except Exception as e:
        print('Error deleting user account:', e)
        return redirect(url_for('profile'))

@app.route('/logout')
def logout():
    session.pop('user', None)
    return redirect(url_for('index'))

@app.route('/support', methods=['GET', 'POST'])
def support():
    if request.method == 'POST':
        name = request.form.get('name')
        reach = request.form.get('reach')
        bug = request.form.get('bug')
        detail = request.form.get('detail')
        image = request.files['image'] if 'image' in request.files else None

        if image:
            image_blob = bucket.blob('QueryImages/' + image.filename)
            image_blob.upload_from_string(
                image.read(),
                content_type=image.content_type
            )

            # Get the download URL of the uploaded image
            image_url = image_blob.public_url
        else:
            image_url = None

        db.collection('UserQueries').add({
            'Name': name,
            'Email/Phone': reach,
            'Bug Title': bug,
            'Detail': detail,
            'Image': image_url,
            'timestamp': firestore.SERVER_TIMESTAMP
        })

        # Redirect to the same page
        return redirect(url_for('support'))

    # Perform actions specific to the support page for GET requests
    return render_template('support.html')


if __name__ == '__main__':
    app.run(debug=True)
