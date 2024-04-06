// Initialize Firebase
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

// Get the usernames from the URL parameter
var urlParams = new URLSearchParams(window.location.search);
var otherUser = urlParams.get('user');

// Reference to the chat room document
var chatRoomRef = db.collection('Chats').doc(getChatId(otherUser));

// Add event listener to send button
document.getElementById('sendButton').addEventListener('click', function() {
    sendMessage();
});

// Add event listener to close button
document.getElementById('closeButton').addEventListener('click', function() {
    closeChatRoom();
});

// Function to send a message
function sendMessage() {
    var messageInput = document.getElementById('messageInput');
    var message = messageInput.value.trim();

    if (message !== '') {
        var sender = senderUsername; // Get the sender's username from Flask session
        var timestamp = firebase.firestore.Timestamp.now();

        var messageData = {
            sender: sender,
            text: message,
            timestamp: timestamp
        };

        // Add the message to the Firestore database
        chatRoomRef.collection('Messages').add(messageData)
            .then(function() {
                // Clear the input field after sending the message
                messageInput.value = '';
            })
            .catch(function(error) {
                console.error('Error sending message:', error);
            });
    }
}

// Function to close the chat room and stop snapshot listener
function closeChatRoom() {
    // Stop listening for new messages
    unsubscribeSnapshot();
    // Redirect back to dashboard or any other page
    window.location.href = '/dashboard';
}

// Function to get a unique chat ID based on the usernames of the users involved
function getChatId(otherUser) {
    var currentUser = senderUsername; // Get the current user's username from Flask session
    var chatParticipants = [currentUser, otherUser].sort();
    return chatParticipants.join('_');
}

// Function to start listening for new messages
function startSnapshotListener() {
    unsubscribeSnapshot = chatRoomRef.collection('Messages')
        .orderBy('timestamp')
        .onSnapshot(function(snapshot) {
            snapshot.docChanges().forEach(function(change) {
                if (change.type === 'added') {
                    var message = change.doc.data();
                    displayMessage(message);
                }
            });
        });
}

// Function to display a message in the chatbox
function displayMessage(message) {
    var chatbox = document.getElementById('chatbox');
    var messageElement = document.createElement('div');
    messageElement.textContent = message.sender + ': ' + message.text;
    chatbox.appendChild(messageElement);
}

// Start listening for new messages
startSnapshotListener();
