from flask import Flask, render_template, request, redirect, url_for
import firebase_admin
from firebase_admin import credentials, firestore, storage

app = Flask(__name__)

cred = credentials.Certificate("common/roomies-166f5-firebase-adminsdk-h1537-a0ab5ed914.json")
firebase_admin.initialize_app(cred, {'storageBucket': 'roomies-166f5.appspot.com'})
db = firestore.client()
bucket = storage.bucket()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/dashboard')
def dashboard():
    # Perform actions specific to the dashboard, if any
    return render_template('dashboard.html')


@app.route('/index2', methods=['GET', 'POST'])
def index2():
    error = None

    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        # Query Firestore to check if the username and password are valid
        user_ref = db.collection('Users').document(username)
        user_data = user_ref.get().to_dict()
        

        if user_data and user_data.get('password') == password:
            # Valid credentials, perform login actions
            return redirect('/dashboard')
        else:
            # Invalid credentials, handle accordingly (e.g., show an error message)
            error = 'Invalid credentials'

    return render_template('index2.html', error=error)

@app.route('/support', methods=['GET', 'POST'])
def support():
    if request.method == 'POST':
        subject = request.form.get('subject')
        text = request.form.get('textQuery')
        image = request.files['image'] if 'image' in request.files else None

        # Process the form data
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

        # Store data in Firestore
        db.collection('UserQueries').add({
            'subject': subject,
            'text': text,
            'imageUrl': image_url,
            'timestamp': firestore.SERVER_TIMESTAMP
        })

        # Redirect to the same page
        return redirect(url_for('support'))

    # Perform actions specific to the support page for GET requests
    return render_template('support.html')



if __name__ == '__main__':
    app.run(debug=True)
