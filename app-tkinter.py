import configparser
import threading
import queue
import tkinter as tk
from tkinter import scrolledtext
from pymongo import MongoClient
from pymongo.errors import PyMongoError
import datetime

config = configparser.RawConfigParser()
config.read('config.ini')

client = MongoClient(
    host=config['mongodb']['host'],
    port=config.getint('mongodb', 'port'),
    username=config['mongodb']['username'],
    password=config['mongodb']['password'],
    directConnection=True)
db = client[config['mongodb']['db']]
collection = db[config['mongodb']['collection']]

# Create a thread-safe queue for inter-thread communication
message_queue = queue.Queue()

# Dictionary to hold user panels
user_panels = {}

from pprint import pprint

def watch_collection():
    try:
        # Set up the change stream to watch for insert operations
        with collection.watch([{'$match': {'operationType': 'insert'}}]) as stream:
            for change in stream:
                document = change['fullDocument']
                pprint(document)
                method = document['method']
                if method == "chatMessage" or method == "privateMessage":
                    # Extract additional information
                    user = document['object']['user']['username']
                    message = document['object']['message']['message']
                    timestamp = document['timestamp']
                    # Put the message into the queue
                    message_queue.put({
                        'user': user,
                        'message': message,
                        'timestamp': timestamp
                    })
    except PyMongoError as e:
        print(f"An error occurred: {e}")

def update_gui():
    while True:
        try:
            # Get a message from the queue
            chat_message = message_queue.get_nowait()
            user = chat_message['user']
            message = chat_message['message']
            timestamp = chat_message['timestamp']
            # timestamp = datetime.datetime.fromtimestamp(message['timestamp']).isoformat()

            # If user panel doesn't exist, create it
            if user not in user_panels:
                user_frame = tk.Frame(container)
                user_frame.pack(side='left', fill='both', expand=True, padx=5, pady=5)
                user_label = tk.Label(user_frame, text=f"User: {user}", font=('Arial', 12, 'bold'))
                user_label.pack(anchor='n')
                text_area = scrolledtext.ScrolledText(user_frame, wrap='word', width=40, height=20)
                text_area.pack(fill='both', expand=True)
                user_panels[user] = text_area

            # Insert the message into the user's text area
            text_widget = user_panels[user]
            text_widget.insert('end', f"{timestamp}: {message}\n")
            text_widget.see('end')  # Scroll to the end

        except queue.Empty:
            break

    # Schedule the next update
    root.after(100, update_gui)

# Create the main application window
root = tk.Tk()
root.title("Chat Messages by User")

# Create a container frame
container = tk.Frame(root)
container.pack(fill='both', expand=True)

# Start the MongoDB watcher thread
watcher_thread = threading.Thread(target=watch_collection, daemon=True)
watcher_thread.start()

# Start the GUI update loop
root.after(100, update_gui)

root.mainloop()