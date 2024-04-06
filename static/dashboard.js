
var firebaseConfig = {
    'apiKey': "AIzaSyAp1yMhDs5N5RmPW4rhVlUJ7VtTVfWvty8",
    'authDomain': "roomies-166f5.firebaseapp.com",
    'projectId': "roomies-166f5",
    'storageBucket': "roomies-166f5.appspot.com",
    'messagingSenderId': "1069795528716",
    'appId': "1:1069795528716:web:8e5a61abe0510933cb9e29",
    'measurementId': "G-5DH42NYCQ4",
    'databaseURL': "https://roomies-166f5-default-rtdb.asia-southeast1.firebasedatabase.app"
};

// Initialize Firebase
firebase.initializeApp(firebaseConfig);

// Get a reference to the Firestore database
var db = firebase.firestore();

// Add event listener to chat buttons
document.querySelectorAll('.chat-btn').forEach(function(button) {
    button.addEventListener('click', function() {
        var otherUser = button.dataset.username;
        openChatRoom(otherUser);
    });
});

// Function to open a private chat room with another user
function openChatRoom(otherUser) {
    // Redirect to chat room HTML page with the other user's username in the URL
    window.location.href = '/chat?user=' + otherUser;
}
