from common.firebase import db, bucket, firebase_web_config
from common.email_creds import email, password
from common.captchaKey import key
from firebase_admin import auth, firestore
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
import pandas as pd
import time
from datetime import datetime
import pytz
from algorithm.getRecommendations import get_recommendations


app = Flask(__name__)
app.secret_key = 'roomies' 
firebase = pyrebase.initialize_app(firebase_web_config)
storage = firebase.storage
auth = firebase.auth()  

app.config.update(dict(
    DEBUG = True,
    MAIL_SERVER = 'smtp.gmail.com',
    MAIL_PORT = 587,
    MAIL_USE_TLS = True,
    MAIL_USE_SSL = False,
    MAIL_USERNAME = email,
    MAIL_PASSWORD = password,
))

mail = Mail(app)
face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')

def get_docs():
    docs = db.collection('RoommatePreferences').get()
    data_list = []
    for doc in docs:
        data_list.append(doc.to_dict())
    df = pd.DataFrame(data_list)
    return df

def username_exists(username):
    print("triggered")
    user_ref = db.collection('Users').document(username)
    user_doc = user_ref.get()
    return user_doc.exists

def email_exists(email):
    print("triggered")
    user_ref = db.collection('Users').where('Email', '==', email)
    user_doc = user_ref.get()
    return len(user_doc) > 0

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

def upload_image_to_firebase(image, name):
    filename = 'dpimage_' + name + '.jpg'
    blob = bucket.blob('Profile Photo/'+filename)
    # Convert the OpenCV image to bytes
    _, image_data = cv2.imencode('.jpg', image)
    blob.upload_from_string(image_data.tobytes(), content_type='image/jpeg')

def verify_recaptcha(token):
    api_url = 'https://www.google.com/recaptcha/api/siteverify'
    
    response = requests.post(api_url, {
        'secret': key,
        'response': token
    })

    result = response.json()
    return result['success']

def get_profile_picture_url(profile_picture_path):
    try:
        # Get the blob (file) from Firestore Storage
        blob = bucket.blob(profile_picture_path)
        blob.make_public()
        # Check if the blob exists
        if not blob.exists():
            return None
        
        return blob.public_url

    except Exception as e:
        print("Error fetching profile picture URL:", e)
        return None


@app.route('/')
def index():
    return render_template('index.html')

# @app.route('/about')
# def about():
#     admin_users = get_admin_users()
#     return render_template('about.html',admin_users=admin_users)

@app.route('/terms')
def terms():
    return render_template('terms.html')

@app.route('/whyroommatefinder')
def whyroommatefinder():
    admin_users = get_admin_users()
    return render_template('about.html',admin_users=admin_users)

@app.route('/signup')
def signup():
    return render_template('signup.html')

@app.route('/login')
def login():
    return render_template('index2.html')

@app.route('/check_username', methods=['POST'])
def check_username():
    username = request.json.get('username')
    if username_exists(username):
        return jsonify({'available': False})
    else:
        return jsonify({'available': True})
    
@app.route('/check_email', methods=['POST'])
def check_email():
    email = request.json.get('email')
    if email_exists(email):
        return jsonify({'available': False})
    else:
        return jsonify({'available': True})

@app.route('/signup1', methods=['GET', 'POST'])
def signup1():
    username = request.form.get('username')
    fname = request.form.get('fname')
    lname = request.form.get('lname')
    email = request.form.get('mail')
    password = request.form.get('password')
    phone_number = request.form.get('phone')
    # age = request.form.get('age')
    birthdate_str = request.form.get('birthdate')
    gender = request.form.get('Gender')

    try:
        birthdate = datetime.strptime(birthdate_str, '%Y-%m-%d')
        # Calculate age
        today = datetime.today()
        age = today.year - birthdate.year - ((today.month, today.day) < (birthdate.month, birthdate.day))

        user = auth.create_user_with_email_and_password(
            email=email,
            password=password
        )

        otp = generate_otp()

        session['user_info'] = {
            'username': username,
            'email': email,
            'gender': gender,
            'phone_number': phone_number,
            'fname': fname,
            'lname': lname,
            'age': age,
            'otp': otp
        }
        print(session['user_info'])
        
        user_info = session.get('user_info', {}) 
        db.collection('Users').document(user_info['username']).set({
                'OTP': 0,
                'FaceDetection': 0,
                'Preference1': 0,
                'Preference2': 0,
                'Username': user_info['username'],
                'FirstName': user_info['fname'],
                'LastName': user_info['lname'],
                'Age': int(user_info['age']),
                'Email': user_info['email'],
                'Gender': user_info['gender'],
                'PhoneNumber': user_info['phone_number']
        })

        send_otp_email(email, otp)

        print('Successfully created new user:', user)
        return redirect(url_for('verify_email'))

    except Exception as e:
        print('Error creating user:', e)
        return render_template('signup.html', error=e)
    
@app.route('/verify_email', methods=['GET', 'POST'])
def verify_email():
    if request.method == 'POST':
        entered_otp = request.form.get('otp')
        
        session_otp_user_info = session.get('user_info', {}).get('otp')
        session_otp_user = session.get('user', {}).get('otp')
        user_info = session.get('user_info', {}) 
        user_info_login = session.get('user', {})
        if entered_otp == session_otp_user_info or entered_otp == session_otp_user:
            if session_otp_user_info:
                db.collection('Users').document(user_info['username']).update({
                'OTP': 1,
                })
                print(user_info)
                print("signup")
            else:
                db.collection('Users').document(user_info_login['username']).update({
                'OTP': 1,
                })
                print(user_info_login)
            # OTP matched, proceed with signup
            # session.pop('user_info')['otp']
            return redirect(url_for('facedetect'))
        else:
            return render_template('verify_email.html', error='Incorrect OTP. Please try again.')

    return render_template('verify_email.html')

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
         
        user_info = session.get('user_info', {})    
        user_info_login = session.get('user', {})  

        session_username = session.get('user_info', {}).get('username')
        session_username_login = session.get('user', {}).get('username')

        if len(faces) > 0:
            print("success!")
            if session_username:
                upload_image_to_firebase(image,session_username)
                db.collection('Users').document(user_info['username']).update({
                'FaceDetection': 1,
                })
            else:
                upload_image_to_firebase(image,session_username_login)
                db.collection('Users').document(user_info_login['username']).update({
                'FaceDetection': 1,
                })
            return redirect(url_for('preferences'))
        else:
            return "No human user detected. Make sure your face is clearly visible and you are in a well lit place. \nPlease capture another image."
    return render_template('facedetect1.html')

@app.route('/preferences', methods=['GET', 'POST'])
def preferences():
    fname =  session.get('user_info', {}).get('fname')
    lname =  session.get('user_info', {}).get('lname')
    gender = session.get('user_info', {}).get('gender')
    age = session.get('user_info', {}).get('age')

    fname_login = session.get('user', {}).get('fname')
    lname_login = session.get('user', {}).get('lname')
    age_login = session.get('user', {}).get('age')
    gender_login = session.get('user', {}).get('gender')

    if request.method == 'POST':
        bio = request.form.get('bio')
        location = request.form.get('location')
        habits = request.form.get('habits')
        food_preference = request.form.get('food')
        profession = request.form.get('profession')
        religion = request.form.get('religion')
        sleep_schedule = request.form.get('sleepschedule')
        cleanliness_habits = request.form.get('cleanlinessH')
        pet = request.form.get('pet')

        if 'user_info' in session:
            user_info = session.get('user_info', {})
            user_info.update({
                'bio': bio,
                'location': location,
                'habits': habits,
                'food_preference': food_preference,
                'profession': profession,
                'religion': religion,
                'sleep_schedule': sleep_schedule,
                'cleanliness_habits': cleanliness_habits,
                'pet_friendly': pet,
            })
        
            session['user_info'] = user_info

            print(user_info)

            db.collection('Users').document(user_info['username']).update({
                    'Preference1': 1,
                })
            
            db.collection('RoommatePreferences').document(user_info['username']).set({
                'Username': user_info['username'],
                'Bio': user_info['bio'],
                'Location': user_info['location'],
                'Habits': user_info['habits'],
                'FoodPreference': user_info['food_preference'],
                'Profession': user_info['profession'],
                'Religion': user_info['religion'],
                'SleepSchedule': user_info['sleep_schedule'],
                'CleanlinessHabits': user_info['cleanliness_habits'],
                'PetFriendliness': user_info['pet_friendly'],
                'Age': int(user_info['age']),
                'Gender': user_info['gender'],
                'Listed': 0,
                })

        else:
            user_info_login = session.get('user', {})
            user_info_login.update({
                'bio': bio,
                'location': location,
                'habits': habits,
                'food_preference': food_preference,
                'profession': profession,
                'religion': religion,
                'sleep_schedule': sleep_schedule,
                'cleanliness_habits': cleanliness_habits,
                'pet_friendly': pet,
            })
        
            session['user'] = user_info_login

            print(user_info_login)

            db.collection('Users').document(user_info_login['username']).update({
                    'Preference1': 1,
                })
            
            db.collection('RoommatePreferences').document(user_info_login['username']).set({
                'Username': user_info_login['username'],
                'Bio': user_info_login['bio'],
                'Location': user_info_login['location'],
                'Habits': user_info_login['habits'],
                'FoodPreference': user_info_login['food_preference'],
                'Profession': user_info_login['profession'],
                'Religion': user_info_login['religion'],
                'SleepSchedule': user_info_login['sleep_schedule'],
                'CleanlinessHabits': user_info_login['cleanliness_habits'],
                'PetFriendliness': user_info_login['pet_friendly'],
                'Age': int(user_info_login['age']),
                'Gender': user_info_login['gender'],
                'Listed': 0,
                })

        return redirect(url_for('preferences2'))

    return render_template('preferences.html', gender = gender, lname = lname, fname = fname, age = age, fname_login = fname_login, lname_login = lname_login, age_login=age_login, gender_login=gender_login )

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
        
        if 'user_info' in session:
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
            print(user_info)

            db.collection('Users').document(user_info['username']).update({
                    'Preference2': 1,
                })

            db.collection('RoommatePreferences').document(user_info['username']).update({
                'Adventurous': user_info['activity'],
                'Organized': user_info['organized'],
                'Social': user_info['social'],
                'Compromise': user_info['conflict'],
                'Stress': user_info['stress'],
                'Exploring': user_info['cultures'],
                'Proactive': user_info['future'],
                'Seekout': user_info['gatherings'],
                'Patient': user_info['patient'],
                'Emotional': user_info['mood'],
                'Email': user_info['email'],
            })

            session.pop('user_info', None)

        else:
            user_info_login = session.get('user', {})
            user_info_login.update({
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
            session['user'] = user_info_login
            print(user_info_login)

            db.collection('Users').document(user_info_login['username']).update({
                    'Preference2': 1,
                })

            db.collection('RoommatePreferences').document(user_info_login['username']).update({
                'Adventurous': user_info_login['activity'],
                'Organized': user_info_login['organized'],
                'Social': user_info_login['social'],
                'Compromise': user_info_login['conflict'],
                'Stress': user_info_login['stress'],
                'Exploring': user_info_login['cultures'],
                'Proactive': user_info_login['future'],
                'Seekout': user_info_login['gatherings'],
                'Patient': user_info_login['patient'],
                'Emotional': user_info_login['mood'],
                'Email': user_info_login['email'],
            })

            session.pop('user', None)

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
                'username':doc.id,
                'fname': doc.get('FirstName'),
                'lname': doc.get('LastName'),
                'gender': doc.get('Gender'),
                'age': doc.get('Age'),
                }
                
                otp = doc.get('OTP')
                face_detection = doc.get('FaceDetection')
                preference1 = doc.get('Preference1')
                preference2 = doc.get('Preference2')

            if otp == 0:
                otp = generate_otp()
                user_info_login = session.get('user', {})
                user_info_login.update({
                'otp': otp,
                })
                session['user'] = user_info_login
                send_otp_email(email, otp)
                return redirect(url_for('verify_email'))
            elif face_detection == 0:
                return redirect(url_for('facedetect'))
            elif preference1 == 0:
                return redirect(url_for('preferences'))
            elif preference2 == 0:
                return redirect(url_for('preferences2'))
            else:
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

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user' not in session:
            return redirect(url_for('login')) 
        user_id = session['user']['username']
        admin_users = get_admin_users()
        if user_id not in admin_users:
            return render_template('admin_access_denied.html')
        return f(*args, **kwargs)
    return decorated_function

def get_admin_users():
    admin_users = []
    users_ref = db.collection('Users').stream()
    for doc in users_ref:
        user_data = doc.to_dict()
        if 'Admin' in user_data and user_data['Admin']:
            admin_users.append(doc.id)
    return admin_users

@app.route('/admin')
@admin_required
def admin():
    preferences_ref = db.collection('RoommatePreferences')
    users_ref = db.collection('Users')
    queries_ref = db.collection('UserQueries')
    reports_ref = db.collection('Reports')

    preferences_count = len(preferences_ref.get())
    users_count = len(users_ref.get())
    queries_count = len(queries_ref.get())
    reports_count = len(reports_ref.get())

    queries_data = []
    queries = queries_ref.get()
    for query in queries:
        query_data = query.to_dict()
        queries_data.append(query_data)
    
    reports_data=[]
    reports = reports_ref.get()
    for report in reports:
        report_data = report.to_dict()
        reports_data.append(report_data)

    admin_users = get_admin_users()

    return render_template('admin_dashboard.html', preferences_count=preferences_count,users_count=users_count,queries_count=queries_count,reports_count=reports_count,queries_data=queries_data,reports_data=reports_data,admin_users=admin_users)

@app.route('/dashboard')
@login_required
def dashboard():
    if 'user' in session:
        user_info = session.get('user')
        if user_info:
            user_email = user_info.get('email')
            user_gender = user_info.get('gender')
            user_age = user_info.get('age')
            
            user_ref = db.collection('RoommatePreferences')
            doc_ref = user_ref.where(filter=FieldFilter('Email','==',user_email)).limit(1).stream()
            for doc in doc_ref:
                Habits = doc.get('Habits')
                FoodPreference = doc.get('FoodPreference')
                Profession = doc.get('Profession')
                Religion = doc.get('Religion')
                SleepSchedule = doc.get('SleepSchedule')
                CleanlinessHabits = doc.get('CleanlinessHabits')
                PetFriendliness = doc.get('PetFriendliness')
                Adventurous = doc.get('Adventurous')
                Organized = doc.get('Organized')
                Social = doc.get('Social')
                Compromise = doc.get('Compromise')
                Stress = doc.get('Stress')
                Exploring = doc.get('Exploring')
                Proactive = doc.get('Proactive')
                Seekout = doc.get('Seekout')
                Patient = doc.get('Patient')
                Emotional = doc.get('Emotional')
                Location = doc.get('Location')
            
            user_profile = f"Location: {Location} Gender: {user_gender} Age: {user_age} Habits: {Habits} FoodPreference: {FoodPreference} Profession: {Profession} Religion: {Religion} SleepSchedule: {SleepSchedule} CleanlinessHabits: {CleanlinessHabits} PetFriendliness: {PetFriendliness} Adventurous: {Adventurous} Organized: {Organized} Social: {Social} Compromise: {Compromise} Stress: {Stress} Exploring: {Exploring} Proactive: {Proactive} Seekout: {Seekout} Patient: {Patient} Emotional: {Emotional}"
            df = get_docs()
            
            top_n = 20
            
            recommendations = get_recommendations(df, user_profile, top_n)

            recommendations_dashboard = recommendations.to_dict(orient='records')

            profile_picture_urls = []

            for recommendation in recommendations_dashboard:
                username = recommendation['Username']
                profile_picture_path = f"Profile Photo/dpimage_{username}.jpg"
                profile_picture_url = get_profile_picture_url(profile_picture_path)
                if profile_picture_url is None:
                    profile_picture_url = "https://firebasestorage.googleapis.com/v0/b/roomies-166f5.appspot.com/o/Profile%20Photo%2Favatar.jpg?alt=media&token=bf819735-cee1-400a-ad30-0d7063d473ab"
                profile_picture_urls.append(profile_picture_url)

        admin_users = get_admin_users()

        return render_template('dashboard.html', user_email=user_email, recommendations_dashboard=recommendations_dashboard, profile_picture_urls=profile_picture_urls,admin_users=admin_users)
    else:
        return redirect(url_for('index'))
    
@app.route('/chat', methods=['GET'])
def chatroom():
    username = request.args.get('user')
    current_username = session["user"]["username"]  # Get the username from the query parameter
    # Now you can render your chatroom template with the username
    return render_template('chatroom.html', username=username,current_username=current_username)

    
@app.route('/profile')
@login_required
def profile():
    user_info = session.get('user')

    if user_info:
        user_email = user_info.get('email')
        user_username = user_info.get('username')
    
    profile_picture_path = f"Profile Photo/dpimage_{user_username}.jpg"

    profile_picture_url = get_profile_picture_url(profile_picture_path)

    if profile_picture_url:
        profile_picture_url += f"?t={int(time.time())}"

    user_preferences = get_user_preferences(user_email)  

    admin_users = get_admin_users()

    return render_template('profile.html', user_preferences = user_preferences, profile_picture_url=profile_picture_url,admin_users=admin_users)  

@app.route('/profiles/<username>')
@login_required
def profiles(username):
    doc_ref = db.collection('RoommatePreferences').document(username)
    doc_ref1 = db.collection('Users').document(username)
    
    doc_snapshot = doc_ref.get()
    doc_snapshot1 = doc_ref1.get()

    if doc_snapshot.exists:
        user_data = doc_snapshot.to_dict()
        user_data1 = doc_snapshot1.to_dict()
    
        profile_picture_path = f"Profile Photo/dpimage_{username}.jpg"

        profile_picture_url = get_profile_picture_url(profile_picture_path)

        if profile_picture_url:
            profile_picture_url += f"?t={int(time.time())}"
        
        admin_users = get_admin_users()

        return render_template('user_profile.html', user_data=user_data, user_data1=user_data1,profile_picture_url=profile_picture_url,admin_users=admin_users)
    else:
        return "User profile not found", 404
    
@app.route('/update_listed_status', methods=['POST'])
def update_listed_status():
    user_id = session['user']['username']
    listed_status = request.json.get('listed', 0)
    local_timezone = pytz.timezone('Asia/Kolkata')
    local_time = datetime.now(local_timezone)
    db.collection('RoommatePreferences').document(user_id).update({'Listed': listed_status})
    if listed_status == 1:
        db.collection('RoommatePreferences').document(user_id).update({'ListedTimestamp': local_time})
    else:
        db.collection('RoommatePreferences').document(user_id).update({'ListedTimestamp': None})
    return jsonify({'success': True}), 200

@app.route('/compare')
def compare():
    username = request.args.get('username')
    user_info = session.get('user')

    email_ref = db.collection('Users').document(username)
    user_data = email_ref.get()
    if user_data.exists:
        compare_email = user_data.to_dict().get('Email')

    if user_info:
        user_email = user_info.get('email')
        user_username = user_info.get('username')
    
    profile_picture_path1 = f"Profile Photo/dpimage_{user_username}.jpg"
    profile_picture_path2 = f"Profile Photo/dpimage_{username}.jpg"

    profile_picture_url1 = get_profile_picture_url(profile_picture_path1)
    profile_picture_url2 = get_profile_picture_url(profile_picture_path2)

    if profile_picture_url1 and profile_picture_url2:
        profile_picture_url1 += f"?t={int(time.time())}"
        profile_picture_url2 += f"?t={int(time.time())}"
    

    user_preferences1 = get_user_preferences(user_email)
    user_preferences2 = get_user_preferences(compare_email)

    attributes_to_compare = ['Age', 'Gender', 'Profession', 'Religion', 'Habits','Food Preference', 'Sleep Schedule', 'Pet Friendliness']

    comparison_results = {}

    for attribute in attributes_to_compare:
        # Get attribute values for both users
        user_value = user_preferences1.get(attribute)
        compare_value = user_preferences2.get(attribute)

        # Perform comparison
        if user_value == compare_value:
            comparison_results[attribute] = True  # Match
        else:
            comparison_results[attribute] = False

    return render_template('compare.html', comparison_results=comparison_results,user_preferences1=user_preferences1,user_preferences2=user_preferences2)


@app.route('/like', methods=['POST'])
@login_required
def like_person():
    data = request.get_json()
    username = data['username']
    user_info = session.get('user')
    user_username = user_info.get('username')
    db.collection('RoommatePreferences').document(user_username).update({'Liked': firestore.ArrayUnion([username])})
    return '', 204  # Return empty response with status code 204

@app.route('/unlike', methods=['POST' , 'DELETE'])
@login_required
def unlike_person():
    data = request.get_json()
    username = data['username']
    user_info = session.get('user')
    user_username = user_info.get('username')

    # Remove the username from the liked list
    db.collection('RoommatePreferences').document(user_username).update({'Liked': firestore.ArrayRemove([username])})
    
    return '', 204  

@app.route('/liked_users')
@login_required
def get_liked_users():
    # Get the currently logged-in user's username
    user_info = session.get('user')
    user_username = user_info.get('username')

    # Retrieve the document snapshot for the user
    user_ref = db.collection('RoommatePreferences').document(user_username)
    user_snapshot = user_ref.get()

    # Extract the 'Liked' field from the document snapshot
    liked_users = user_snapshot.to_dict().get('Liked', [])

    return jsonify({'liked_users': liked_users})

@app.route('/update_preferences', methods=['POST'])
@login_required
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
@login_required
def delete_account():
    try:
        user_info = session.get('user')  
        if user_info:
            id_token = user_info.get('idToken')
            username = user_info.get('username')
        else:
            return redirect(url_for('login'))
        
        db.collection('Users').document(username).delete()
        db.collection('RoommatePreferences').document(username).delete()
        auth.delete_user_account(id_token)

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
    
    admin_users = get_admin_users()
    # Perform actions specific to the support page for GET requests
    return render_template('support.html',admin_users=admin_users)

@app.route('/report', methods=['GET', 'POST'])
@login_required
def report():
    if request.method == 'POST':
        name = request.form.get('name')
        reported = request.form.get('reported')
        description = request.form.get('description')
        image = request.files['image'] if 'image' in request.files else None

        if image:
            image_blob = bucket.blob('ReportImages/' + image.filename)
            image_blob.upload_from_string(
                image.read(),
                content_type=image.content_type
            )

            # Get the download URL of the uploaded image
            image_url = image_blob.public_url
        else:
            image_url = None

        db.collection('Reports').add({
            'Username': name,
            'ReportedUser': reported,
            'Description': description,
            'Image': image_url,
            'timestamp': firestore.SERVER_TIMESTAMP
        })

        # Redirect to the same page
        return redirect(url_for('report'))
    admin_users = get_admin_users()
    # Perform actions specific to the support page for GET requests
    return render_template('report.html',admin_users=admin_users)

if __name__ == '__main__':
    app.run(debug=True)
