import eventlet
eventlet.monkey_patch()

import configparser
import datetime
from flask import Flask, render_template
from flask_socketio import SocketIO, emit
from pymongo import MongoClient
from pymongo.errors import PyMongoError
# import threading

config = configparser.RawConfigParser()
config.read('config.ini')

app = Flask(__name__)
with open('secret_key', 'r') as f:
    app.config['SECRET_KEY'] = f.read().strip()
socketio = SocketIO(app, async_mode='eventlet')

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
        with collection.watch([{'$match': {'operationType': 'insert'}}]) as stream:
            for change in stream:
                document = change.get('fullDocument', {})
                method = document.get('method')
                if method in ("chatMessage", "privateMessage"):
                    # Extract additional information with safe access
                    broadcaster = document.get('object', {}).get('broadcaster')
                    user = document.get('object', {}).get('user', {}).get('username', 'Unknown User')
                    if user != broadcaster:
                        message = document.get('object', {}).get('message', {}).get('message', '')
                        timestamp = document.get('timestamp', datetime.datetime.now(datetime.timezone.utc))
                        # Check if timestamp is a datetime object and convert it to a string
                        if isinstance(timestamp, datetime.datetime):
                            timestamp = timestamp.strftime('%Y-%m-%d %H:%M:%S')
                        else:
                            timestamp = 'No timestamp'
                        # Emit the message to all connected clients
                        socketio.emit('new_message', {
                            'user': user,
                            'message': message,
                            'timestamp': timestamp,
                            'method': method
                        })
    except PyMongoError as e:
        print(f"A PyMongoError occurred: {e}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")


# Start the MongoDB watcher thread
# def start_watcher():
#     watcher_thread = threading.Thread(target=watch_collection, daemon=True)
#     watcher_thread.start()

def start_watcher():
    socketio.start_background_task(watch_collection)

start_watcher()

@app.route('/')
def index():
    return render_template('index.html')

if __name__ == '__main__':
    socketio.run(app, debug=True, host='0.0.0.0', port=5000)
