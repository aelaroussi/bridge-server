import os
import datetime
import uuid
from flask import Flask, request, jsonify, render_template, redirect, url_for, session

app = Flask(__name__)

# CONFIGURATION
# 1. Session Key: Encrypts your cookies.
app.secret_key = os.urandom(24) 

# 2. The Main Secret: Used to authenticate the agent and the web user.
SECRET_TOKEN = os.environ.get("SECRET_TOKEN", "unsafe_default")

# DATA STRUCTURES
commands_log = [] 
cmd_queue = []

@app.route('/')
def index():
    return redirect(url_for('admin'))

@app.route('/admin', methods=['GET', 'POST'])
def admin():
    error = None
    success_msg = None
    last_command = None
    
    # 1. AUTHENTICATION LOGIC
    # Check if we already have a valid session
    user_token = session.get('token')

    # If this is a POST (Form Submit), check if they provided a new token
    if request.method == 'POST':
        form_token = request.form.get('token')
        cmd_input = request.form.get('cmd')

        # Prioritize the form token if provided
        if form_token:
            if form_token == SECRET_TOKEN:
                session['token'] = form_token # Login successful, save to session
                user_token = form_token
            else:
                error = "INVALID TOKEN"
        
        # If we are authenticated (either via session or just now), process command
        if user_token == SECRET_TOKEN and not error:
            if cmd_input:
                cmd_id = str(uuid.uuid4())[:8]
                new_cmd = {
                    "id": cmd_id,
                    "timestamp": datetime.datetime.now().strftime("%H:%M:%S"),
                    "cmd": cmd_input,
                    "status": "queued",
                    "output": None
                }
                commands_log.append(new_cmd)
                cmd_queue.append(cmd_id)
                # Redirect to GET to prevent form resubmission warning
                # Note: We do NOT pass the token in the URL anymore
                return redirect(url_for('admin', new_id=cmd_id))
        elif not error:
            error = "MISSING OR INVALID TOKEN"

    # 2. GET REQUEST LOGIC
    # Retrieve status message from URL (e.g. ?new_id=123)
    new_id = request.args.get('new_id')
    if new_id:
        success_msg = f"Command queued (ID: {new_id})"

    # Retrieve Last Command (Only if authenticated)
    if user_token == SECRET_TOKEN and commands_log:
        last_command = commands_log[-1]

    return render_template(
        'index.html', 
        last_command=last_command,
        status_error=error, 
        status_success=success_msg,
        # We pass the token back to the view to pre-fill the input 
        # so the user knows they are logged in, but it's optional now
        token_value=user_token or "" 
    )

@app.route('/history')
def history():
    # Check Session Cookie
    if session.get('token') != SECRET_TOKEN:
        return "<h1>Unauthorized</h1><p>Please login at the <a href='/admin'>Dashboard</a> first.</p>"
    
    return render_template('history.html', history=reversed(commands_log))

@app.route('/logout')
def logout():
    session.pop('token', None)
    return redirect(url_for('admin'))

# --- AGENT API (Uses Headers, Safe) ---

@app.route('/poll', methods=['GET'])
def poll():
    if request.headers.get('Authorization') != SECRET_TOKEN:
        return jsonify({"error": "Unauthorized"}), 403
    
    if cmd_queue:
        next_id = cmd_queue.pop(0)
        for cmd in commands_log:
            if cmd['id'] == next_id:
                cmd['status'] = 'sent'
                return jsonify({"id": cmd['id'], "command": cmd['cmd']})
    return jsonify({"command": None})

@app.route('/report', methods=['POST'])
def report():
    if request.headers.get('Authorization') != SECRET_TOKEN:
        return jsonify({"error": "Unauthorized"}), 403
    
    data = request.json
    if data:
        cmd_id = data.get('id')
        output = data.get('output')
        for cmd in commands_log:
            if cmd['id'] == cmd_id:
                cmd['status'] = 'executed'
                cmd['output'] = output
                break
    return "OK"

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)