import os
import datetime
import uuid
from flask import Flask, request, jsonify, render_template, redirect, url_for, session

app = Flask(__name__)

# CONFIGURATION
app.secret_key = os.urandom(24) 
SECRET_TOKEN = os.environ.get("SECRET_TOKEN", "unsafe_default")

# DATA STRUCTURES
commands_log = [] 
cmd_queue = []

@app.route('/')
def index():
    return redirect(url_for('admin'))

@app.route('/admin', methods=['GET', 'POST'])
def admin():
    # 1. HANDLE POST (Form Submissions)
    if request.method == 'POST':
        form_token = request.form.get('token')
        cmd_input = request.form.get('cmd')

        # Check Token
        if form_token != SECRET_TOKEN:
            # ERROR: Redirect to GET with error flag (Avoids "Confirm Resubmission")
            return redirect(url_for('admin', error='invalid'))
        
        # SUCCESS: Update Session
        session['token'] = form_token
        
        # Process Command (if provided)
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
            return redirect(url_for('admin', new_id=cmd_id))
        
        # Login Only (No command): Redirect to refresh page state
        return redirect(url_for('admin'))

    # 2. HANDLE GET (Page View)
    user_token = session.get('token')
    is_authenticated = (user_token == SECRET_TOKEN)
    
    error = None
    success_msg = None
    last_command = None

    # Check URL args for status messages
    if request.args.get('error') == 'invalid':
        error = "INVALID TOKEN"
    
    new_id = request.args.get('new_id')
    if new_id:
        success_msg = f"Command queued (ID: {new_id})"

    # Retrieve Data if Authenticated
    if is_authenticated:
        if commands_log:
            last_command = commands_log[-1]
    
    return render_template(
        'index.html', 
        last_command=last_command,
        status_error=error, 
        status_success=success_msg,
        token_value=user_token or "",
        is_authenticated=is_authenticated
    )

@app.route('/history')
def history():
    if session.get('token') != SECRET_TOKEN:
        return "<h1>Unauthorized</h1><p>Please login at the <a href='/admin'>Dashboard</a> first.</p>"
    return render_template('history.html', history=reversed(commands_log))

@app.route('/logout')
def logout():
    session.pop('token', None)
    return redirect(url_for('admin'))

# --- AGENT API ---

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