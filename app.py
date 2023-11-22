import firebase_admin
from firebase_admin import credentials, firestore, storage, auth
from flask import Flask, render_template, request, redirect, url_for,session
import pyrebase

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


@app.route('/')
def index():
    return render_template('index.html')

@app.route('/about')
def about():
    return render_template('about.html')

# @app.route('/dashboard')
# def dashboard():
#     # Perform actions specific to the dashboard, if any
#     return render_template('dashboard.html')

@app.route('/signup')
def signup():
    # Perform actions specific to the dashboard, if any
    return render_template('signup.html')

@app.route('/login')
def login():
    # Perform actions specific to the dashboard, if any
    return render_template('index2.html')

@app.route('/signup1', methods=['GET', 'POST'])
def signup1():
    email = request.form.get('mail')
    password = request.form.get('password')

    try:
        user = auth.create_user_with_email_and_password(
            email=email,
            password=password
        )
        print('Successfully created new user:')
        print(user)
        return redirect(url_for('login'))
    except Exception as e:
        print('Error creating user:', e)
        return render_template('signup.html', error='Error creating user')


@app.route('/welcome', methods=['GET', 'POST'])
def welcome():
    if request.method == 'POST':
        email = request.form.get('mail')
        password = request.form.get('password')

        try:
            user = auth.sign_in_with_email_and_password(email,password)
            session['user'] = email
            print('Successfully fetched user data:', user['localId'])
            return redirect(url_for('dashboard'))
        except Exception as e:
            print('Error fetching user data or invalid credentials:', e)
            return render_template('index2.html', error='Invalid credentials')

@app.route('/dashboard')
def dashboard():
    # Check if the user is logged in
    if 'user' in session:
        user_email = session['user']
        # You can use user_email to fetch user-specific data from Firestore
        return render_template('dashboard.html', user_email=user_email)
    else:
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
            # Upload the image to Firestore Storage
            image_blob = bucket.blob('images/' + image.filename)
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
