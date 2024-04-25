from flask import Flask, render_template

app = Flask(__name__)

# Route for index.html
@app.route('/')
def index():
    return render_template('index.html')

# Route for index2.html
@app.route('/index2')
def index2():
    return render_template('index2.html')

if __name__ == '__main__':
    app.run(debug=True)
