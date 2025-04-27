import os
import threading
from flask import Flask, render_template, request, send_file
from flask_socketio import SocketIO
from werkzeug.utils import secure_filename
from dotenv import load_dotenv
import google.generativeai as genai
from analysis import background_task
from dialog_processor import ITEMS

# 初始化 Flask 和 Socket.IO
app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'Uploads'
app.config['STATIC_FOLDER'] = 'static'
socketio = SocketIO(app, async_mode='threading')

# 確保上傳和靜態檔案目錄存在
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(app.config['STATIC_FOLDER'], exist_ok=True)

# 載入環境變數並配置 Gemini API
load_dotenv()
gemini_api_key = os.environ.get("GEMINI_API_KEY")
if not gemini_api_key:
    raise ValueError("請設定環境變數 GEMINI_API_KEY")
genai.configure(api_key=gemini_api_key)
model = genai.GenerativeModel('gemini-1.5-flash')

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        socketio.emit('error', {'message': '請求中無檔案'})
        return 'No file part', 400
    file = request.files['file']
    if file.filename == '':
        socketio.emit('error', {'message': '未選擇檔案'})
        return 'No selected file', 400
    if file and file.filename.endswith('.csv'):
        filename = secure_filename(file.filename)
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(file_path)
        output_csv = os.path.join(app.config['UPLOAD_FOLDER'], '1on1_analysis.csv')
        if os.path.exists(output_csv):
            os.remove(output_csv)  # 刪除舊結果
        socketio.emit('update', {'message': '🟢 檔案上傳成功，開始分析中...'})
        thread = threading.Thread(target=background_task, args=(file_path, output_csv, model, socketio, app.config))
        thread.start()
        return 'File uploaded and processing started.', 200
    else:
        socketio.emit('error', {'message': '僅支援 CSV 檔案'})
        return 'Invalid file type', 400

@app.route('/download/<filename>')
def download_file(filename):
    file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    if os.path.exists(file_path):
        return send_file(file_path, as_attachment=True)
    else:
        socketio.emit('error', {'message': '結果檔案不存在'})
        return 'File not found', 404

if __name__ == '__main__':
    socketio.run(app, debug=True)