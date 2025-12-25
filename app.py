import os
import datetime
import uuid
from flask import Flask, request, jsonify, render_template, redirect, url_for

app = Flask(__name__)

SECRET_TOKEN = os.environ.get("SECRET_TOKEN", "unsafe_default")

# DATA STRUCTURES
# commands_log: Stores the full history (id, timestamp, cmd, status, output)
commands_log = [] 
# cmd_queue: Stores just the IDs of commands waiting to be picked up
cmd_queue = []

@app.route('/')
def index():
    return redirect(url_for('admin'))

@app.route('/admin', methods=['GET', 'POST'])
def admin():
    # 1. Get Token (Check URL args first for auto-refresh, then Form)
    token_val = request.args.get('token') or request.form.get('token') or ""
    
    error = None
    success_msg = None
    last_command = None

    # 2. Handle New Command Submission
    if request.method == 'POST':
        cmd_input = request.form.get('cmd')
        
        if token_val != SECRET_TOKEN:
            error = "INVALID TOKEN"
        elif cmd_input:
            # Create a new command object
            cmd_id = str(uuid.uuid4())[:8] # Short random ID
            new_cmd = {
                "id": cmd_id,
                "timestamp": datetime.datetime.now().strftime("%H:%M:%S"),
                "cmd": cmd_input,
                "status": "queued", # queued -> sent -> executed
                "output": None
            }
            commands_log.append(new_cmd)
            cmd_queue.append(cmd_id)
            success_msg = f"Command '{cmd_input}' queued (ID: {cmd_id})"

    # 3. Retrieve Last Command (If token is valid)
    if token_val == SECRET_TOKEN and commands_log:
        last_command = commands_log[-1]
    elif token_val and token_val != SECRET_TOKEN:
        error = "INVALID TOKEN"

    return render_template(
        'index.html', 
        last_command=last_command, # Only sending the LATEST command
        status_error=error, 
        status_success=success_msg,
        token_value=token_val
    )

@app.route('/history')
def history():
    token_val = request.args.get('token')
    if token_val != SECRET_TOKEN:
        return "<h1>Unauthorized</h1><p>Invalid Token</p>"
    
    # Return full log, but we generally don't show massive outputs here to keep it clean
    # We reverse it to show newest first
    return render_template('history.html', history=reversed(commands_log), token_value=token_val)

# --- AGENT API ---

@app.route('/poll', methods=['GET'])
def poll():
    if request.headers.get('Authorization') != SECRET_TOKEN:
        return jsonify({"error": "Unauthorized"}), 403
    
    if cmd_queue:
        # Get the ID of the next command
        next_id = cmd_queue.pop(0)
        
        # Find the command object and mark as sent
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
        
        # Find the command by ID and update it
        for cmd in commands_log:
            if cmd['id'] == cmd_id:
                cmd['status'] = 'executed'
                cmd['output'] = output
                break
                
    return "OK"

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
