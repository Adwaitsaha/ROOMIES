import firebase_admin
from firebase_admin import credentials, firestore, storage, auth
from flask import Flask, render_template, request, redirect, url_for,session
import pyrebase
import requests
from functools import wraps 
from google.cloud.firestore_v1.base_query import FieldFilter


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

def get_user_preferences(email):
    user_ref = db.collection('Users')
    doc_ref = user_ref.where(filter=FieldFilter('Email','==',email)).limit(1).stream()
    for doc in doc_ref:
        return doc.to_dict()

    # Return an empty dictionary or None if no matching document is found
    return {}




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

    # Parse the response
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


@app.route('/preferences', methods=['GET', 'POST'])
def preferences():
    if request.method == 'POST':
        fname = request.form.get('fname')
        lname = request.form.get('lname')
        age = request.form.get('age')
        bio = request.form.get('bio')
        location = request.form.get('location')
        gender = request.form.get('Gender')
        habits = request.form.get('habits')
        food_preference = request.form.get('food')
        profession = request.form.get('profession')
        religion = request.form.get('religion')
        sleep_schedule = request.form.get('sleepschedule')
        cleanliness_habits = request.form.get('cleanlinessH')

        user_info = session.get('user_info', {})
        user_info.update({
            'fname': fname,
            'lname': lname,
            'age': age,
            'bio': bio,
            'location': location,
            'gender': gender,
            'habits': habits,
            'food_preference': food_preference,
            'profession': profession,
            'religion': religion,
            'sleep_schedule': sleep_schedule,
            'cleanliness_habits': cleanliness_habits
        })

        db.collection('Users').document(user_info['username']).set({
            'Username': user_info['username'],
            'Email': user_info['email'],
            'Phone Number': user_info['phone_number']
        })

        db.collection('RoommatePreferences').document(user_info['username']).set({
            'Username': user_info['username'],
            'First Name': user_info['fname'],
            'Last Name': user_info['lname'],
            'Age': user_info['age'],
            'Bio': user_info['bio'],
            'Location': user_info['location'],
            'Gender': user_info['gender'],
            'Habits': user_info['habits'],
            'Food_preference': user_info['food_preference'],
            'Profession': user_info['profession'],
            'Religion': user_info['religion'],
            'Sleep Schedule': user_info['sleep_schedule'],
            'Cleanliness Habits': user_info['cleanliness_habits']

        })

        # Clear the session data after storing in Firestore
        session.pop('user_info', None)

        # Redirect to a success page or perform other actions
        return redirect(url_for('dashboard'))

    return render_template('preferences.html')


@app.route('/signup1', methods=['GET', 'POST'])
def signup1():
    username = request.form.get('username')
    email = request.form.get('mail')
    password = request.form.get('password')
    phone_number = request.form.get('phone')
    try:
        user = auth.create_user_with_email_and_password(
            email=email,
            password=password
        )

        session['user_info'] = {
            'username': username,
            'email': email,
            'phone_number': phone_number
        }
        
        print('Successfully created new user:')
        print(user)
        return redirect(url_for('preferences'))
    except Exception as e:
        print('Error creating user:', e)
        return render_template('signup.html', error=e)


@app.route('/welcome', methods=['GET', 'POST'])
def welcome():
    if request.method == 'POST':
        email = request.form.get('mail')
        password = request.form.get('password')

        try:
            user = auth.sign_in_with_email_and_password(email,password)
            session['user'] = user['email']
            print('Successfully fetched user data', user)
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
        user_email = session['user']
        print(user_email)
        return render_template('dashboard.html', user_email=user_email)
    else:
        return redirect(url_for('index'))
    
@app.route('/profile')
@login_required
def profile():
    user_email = session.get('user')
    user_preferences = get_user_preferences(user_email)  

    return render_template('profile.html', user_preferences = user_preferences)    

@app.route('/delete_account', methods=['POST'])
def delete_account():
    try:
        # Verify the user is authenticated
        user_id = session.get('user')  
        if not user_id:
            return redirect(url_for('login'))

        # Delete the user account using the UID
        auth.delete_user_account(user_id)

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

       
        # Create a new document in the "UserQueries" collection
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
