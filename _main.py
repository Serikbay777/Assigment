import logging
import re
from openai import OpenAI
import time
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from langdetect import detect
import json
import os
from flask import Flask, request, jsonify

# OpenAI API setup
client = OpenAI(api_key="sk-proj-secret")
assistantID = "asst_iDsecret"

# # Google Sheets setup
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds = ServiceAccountCredentials.from_json_keyfile_name('kazturbaza-secret.json', scope)
client_gs = gspread.authorize(creds)

# Используем идентификатор вашей таблицы
spreadsheet_id = 'secret'
sheet = client_gs.open_by_key(spreadsheet_id).sheet1

app = Flask(__name__)

def save_to_sheet(data):
    try:
        sheet.append_row(data)
        logging.info(f"Successfully saved data to sheet: {data}")
    except Exception as e:
        logging.error(f"Failed to save data to sheet: {data}, error: {str(e)}")

@app.route('/start', methods=['GET'])
def start_conversation():
    thread = client.beta.threads.create()
    print("New conversation started with thread ID:", thread.id)
    return jsonify({"thread_id": thread.id})


# Start run
@app.route('/chat', methods=['POST'])
def chat():
    print("chat is working")
    data = request.json
    thread_id = data.get('thread_id')
    user_input = data.get('message', '')
    if not thread_id:
        print("Error: Missing thread_id in /chat")
        return jsonify({"error": "Missing thread_id"}), 400
    print("Received message for thread ID:", thread_id, "Message:", user_input)
    
    # Start run and send run ID back to ManyChat
    client.beta.threads.messages.create(thread_id=thread_id,
                                      role="user",
                                      content=user_input)
    print("good")
    run = client.beta.threads.runs.create(thread_id=thread_id,
                                        assistant_id=assistantID)
    print("Run started with ID:", run.id)
    return jsonify({"run_id": run.id})


def isCooked(response):
    ok = True
    for x in response:
        if x == '?':
            ok = False
    if ok:
        return True
    if 'заявка' in response:
        return True
    if 'заявку' in response:
        return True
    if 'специалисту' in response:
        return True
    if 'специалист' in response:
        return True
    if 'специалистам' in response:
        return True
    
        
# Check status of run
@app.route('/check', methods=['POST'])
def check_run_status():
    print("HERE")
    data = request.json
    thread_id = data.get('thread_id')
    run_id = data.get('run_id')
    user_name = data.get('user_name')
    user_input = data.get('message')
    phone_number = data.get('phone_number')
    
    print(user_input)
    if not thread_id or not run_id:
        print("Error: Missing thread_id or run_id in /check")
        return jsonify({"response": "error"})
    
    # Start timer ensuring no more than 9 seconds, ManyChat timeout is 10s
    start_time = time.time()
    while time.time() - start_time < 8:
        run_status = client.beta.threads.runs.retrieve(thread_id=thread_id,
                                                       run_id=run_id)
        print("Checking run status:", run_status.status)
        
        if run_status.status == 'completed':
            messages = client.beta.threads.messages.list(thread_id=thread_id)
            message_content = messages.data[0].content[0].text
            # Remove annotations
            annotations = message_content.annotations
            for annotation in annotations:
                message_content.value = message_content.value.replace(
                annotation.text, '')

            response = message_content.value
            

            if isCooked(response):
                save_to_sheet([user_name, phone_number, response])

            print("Run completed, returning response")
            return jsonify({
              "response": response,
              "status": "completed"
            })
        time.sleep(1)

    print("Run timed out")
    return jsonify({"response": "timeout"})


if __name__ == '__main__':
  app.run(host='0.0.0.0', port=8080)
