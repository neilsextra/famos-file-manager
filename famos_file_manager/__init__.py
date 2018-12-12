from flask import Flask  # Import the Flask class
from flask_bower import Bower

print('Creating', __name__)
app = Flask(__name__)    # Create an instance of the class for our use

Bower(app)               # Added Bower

print('Added Bower to', __name__)

def wsgi_app(config):
    return app