import configparser
import datetime
from flask import Flask, render_template
from flask_socketio import SocketIO, emit
from pymongo import MongoClient
from pymongo.errors import PyMongoError
import threading

config = configparser.RawConfigParser()
config.read('config.ini')

app = Flask(__name__)
with open('secret_key', 'r') as f:
    app.config['SECRET_KEY'] = f.read().strip()
socketio = SocketIO(app)

client = MongoClient(
    host=config['mongodb']['host'],
    port=config.getint('mongodb', 'port'),
    username=config['mongodb']['username'],
    password=config['mongodb']['password'],
    directConnection=True)
db = client[config['mongodb']['db']]
collection = db[config['mongodb']['collection']]

from pprint import pprint

def watch_collection():
    try:
        # Set up the change stream to watch for insert operations
        with collection.watch([{'$match': {'operationType': 'insert'}}]) as stream:
            for change in stream:
                document = change['fullDocument']
                method = document['method']
                if method == "chatMessage" or method == "privateMessage":
                    # Extract additional information
                    user = document['object']['user']['username']
                    message = document['object']['message']['message']
                    timestamp = document['timestamp']
                    # Check if timestamp is a datetime object and convert it to a string
                    if isinstance(timestamp, datetime.datetime):
                        timestamp = timestamp.strftime('%Y-%m-%d %H:%M:%S')
                    # Emit the message to all connected clients
                    socketio.emit('new_message', {
                        'user': user,
                        'message': message,
                        'timestamp': timestamp
                    })
    except PyMongoError as e:
        print(f"An error occurred: {e}")

# Start the MongoDB watcher thread
def start_watcher():
    watcher_thread = threading.Thread(target=watch_collection, daemon=True)
    watcher_thread.start()

start_watcher()

@app.route('/')
def index():
    return render_template('index.html')

if __name__ == '__main__':
    socketio.run(app, debug=True)
