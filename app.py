import os
import datetime
import uuid
from flask import Flask, request, jsonify, render_template, redirect, url_for

app = Flask(__name__)

SECRET_TOKEN = os.environ.get("SECRET_TOKEN", "unsafe_default")

# DATA STRUCTURES
commands_log = [] 
cmd_queue = []

@app.route('/')
def index():
    return redirect(url_for('admin'))

@app.route('/admin', methods=['GET', 'POST'])
def admin():
    # 1. Get Token from URL or Form
    token_val = request.args.get('token') or request.form.get('token') or ""
    
    error = None
    success_msg = None
    last_command = None

    # 2. Handle POST (Form Submission)
    if request.method == 'POST':
        cmd_input = request.form.get('cmd')
        
        if token_val != SECRET_TOKEN:
            error = "INVALID TOKEN"
        elif cmd_input:
            # Create command
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
            
            # --- THE FIX: Redirect to GET so we can refresh safely ---
            return redirect(url_for('admin', token=token_val, new_id=cmd_id))

    # 3. Handle GET (Page View)
    
    # Check if we just redirected from a successful submission
    new_id = request.args.get('new_id')
    if new_id:
        success_msg = f"Command queued (ID: {new_id})"

    # Retrieve Last Command Logic
    if token_val == SECRET_TOKEN and commands_log:
        last_command = commands_log[-1]
    elif token_val and token_val != SECRET_TOKEN:
        error = "INVALID TOKEN"

    return render_template(
        'index.html', 
        last_command=last_command,
        status_error=error, 
        status_success=success_msg,
        token_value=token_val
    )

@app.route('/history')
def history():
    token_val = request.args.get('token')
    if token_val != SECRET_TOKEN:
        return "<h1>Unauthorized</h1><p>Invalid Token</p>"
    return render_template('history.html', history=reversed(commands_log), token_value=token_val)

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