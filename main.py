# 化学笺集自动化滴定项目的主程序
# 作者：李峙德，刘一弘
# 邮箱：contact@chemview.net
# 最后更新：2025-10-24
import cv2
import time
import threading
from flask import Flask, render_template, request, jsonify, Response
import webview
import numpy as np
import os
import json
import logging
import titration
import message_process

class Webview:
    def __init__(self, titration_instance):
        self.t=titration_instance
        self.app = Flask(__name__, template_folder='web', static_folder='web')
        log = logging.getLogger('werkzeug')
        log.disabled = True
        self.setup_routes()
        self.config_file = 'config.json'
        self.load_config()
        self.main_window = None
        self.child_windows = {}  # 用于管理子窗口
        
    def load_config(self):
        if os.path.exists(self.config_file):
            with open(self.config_file, 'r') as f:
                config = json.load(f)
                # 将配置应用到滴定实例
                for key, value in config.items():
                    if hasattr(self.t, key):
                        setattr(self.t, key, value)
    
    def save_config(self, config_data):
        # 先读取现有配置
        existing_config = {}
        if os.path.exists(self.config_file):
            with open(self.config_file, 'r') as f:
                existing_config = json.load(f)
        
        # 合并配置
        merged_config = {**existing_config,** config_data}
        
        # 保存合并后的配置
        with open(self.config_file, 'w') as f:
            json.dump(merged_config, f, indent=4)
        
        # 更新滴定实例的配置
        for key, value in config_data.items():
            if hasattr(self.t, key):
                setattr(self.t, key, value)
        
        self.t.mp.log('gc',f'{merged_config}')

    def generate_frames(self):
        while True:
            try:
                # 检查滴定实例和摄像头是否可用
                if (hasattr(self.t, 'cd') and self.t.cd and  
                    hasattr(self.t.cd, 'proc') and self.t.cd.proc and 
                    self.t.cd.proc.frame_copy is not None):
                    
                    frame = self.t.cd.proc.frame_copy
                    
                    # 调整帧大小以提高性能
                    frame = cv2.resize(frame, (640, 480))
                    
                    # 将帧转换为JPEG格式
                    ret, buffer = cv2.imencode('.jpg', frame, 
                                             [cv2.IMWRITE_JPEG_QUALITY, 50])
                    if ret:
                        frame_bytes = buffer.tobytes()
                        yield (b'--frame\r\n'
                              b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')
                else:
                    # 生成一个黑色帧作为占位符
                    blank_frame = np.zeros((480, 640, 3), dtype=np.uint8)
                    ret, buffer = cv2.imencode('.jpg', blank_frame)
                    if ret:
                        frame_bytes = buffer.tobytes()
                        yield (b'--frame\r\n'
                              b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')
                
                time.sleep(0.04)
                
            except Exception as e:
                self.t.mp.log('ve',f'{e}')
                # 生成错误帧
                error_frame = np.zeros((480, 640, 3), dtype=np.uint8)
                cv2.putText(error_frame, 'Camera Error', (200, 240), 
                           cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
                ret, buffer = cv2.imencode('.jpg', error_frame)
                if ret:
                    frame_bytes = buffer.tobytes()
                    yield (b'--frame\r\n'
                          b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')
                time.sleep(1)
    
    def setup_routes(self):
        
        @self.app.route('/')
        def index():
            return render_template('index.html')
        
        @self.app.route('/config')
        def config():
            return render_template('config.html')
        
        @self.app.route('/exp')
        def exp():
            return render_template('exp.html')
        
        @self.app.route('/debug')
        def debug():
            return render_template('debug.html')
        
        @self.app.route('/predict')
        def predict():
            return render_template('predict.html')
        
        @self.app.route('/about')
        def about():
            return render_template('about.html')
        
        @self.app.route('/api/status')
        def get_status():
            return jsonify({
                'message': getattr(self.t.mp, 'message', ''),
                'predict_color': getattr(self.t, 'predict_color', '#9CA3AF'),
                'time': f"{getattr(self.t, 'time', 0):.2f} s" if getattr(self.t, 'time', 0) > 0 else '--',
                'volume': f"{getattr(self.t, 'volume', 0):.2f} mL",
                'running': getattr(self.t, 'running', False),
                'endpoint': getattr(self.t, 'endpoint', False)
            })
        
        @self.app.route('/api/start', methods=['POST'])
        def start_titration():
            self.t.run()
            return jsonify({'success': True})
        
        @self.app.route('/api/stop', methods=['POST'])
        def stop_titration():
            self.t.stop()
            return jsonify({'success': True})
        
        @self.app.route('/api/save_config', methods=['POST'])
        def save_config():
            try:
                config_data = request.json
                self.save_config(config_data)
                return jsonify({'success': True})
            except Exception as e:
                return jsonify({'success': False, 'error': str(e)})
            
        @self.app.route('/api/predict', methods=['POST'])
        def llm_predict():
            try:
                exptype = request.json['exptype']
                self.t.llm_predict(exptype)
                return jsonify({'success': True})
            except Exception as e:
                return jsonify({'success': False, 'error': str(e)})
        
        @self.app.route('/api/open_help')
        def open_help():
            try:
                help_file = 'help.pdf'
                if os.path.exists(help_file):
                    os.startfile(help_file)
                return jsonify({'success': True})
            except Exception as e:
                return jsonify({'success': False, 'error': str(e)})

        @self.app.route('/api/open_log_console')
        def open_log_console():
            try:
                console_file = 'cat.log'
                if os.path.exists(console_file):
                    os.startfile(console_file)
                return jsonify({'success': True})
            except Exception as e:
                return jsonify({'success': False, 'error': str(e)})
            
        @self.app.route('/api/reload')
        def reload():
            self.t.release()
            self.t.con()
            return jsonify({'success': True})
            
        @self.app.route('/api/rinse')
        def rinse():
            self.t.rinse()
            return jsonify({'success': True})
            
        @self.app.route('/api/get_config')
        def get_config():
            try:
                config = {}
                if os.path.exists(self.config_file):
                    with open(self.config_file, 'r') as f:
                        config = json.load(f)
                        self.t.mp.log('ar',f'{config}')
                else:
                    # 如果配置文件不存在，返回当前实例的配置
                    config = {
                        'cap_num': getattr(self.t, 'cap_num', 0),
                        'port': getattr(self.t, 'port', 'COM1'),
                        'rate': getattr(self.t, 'rate', '05.00'),
                        'threshold': getattr(self.t, 'threshold', 30),
                        'threshold_times': getattr(self.t, 'threshold_times', 1.5),
                        'usemask': getattr(self.t, 'usemask', True)
                    }
                    self.t.mp.log('ar',f'{config}')
                
                return jsonify(config)
            except Exception as e:
                return jsonify({'error': str(e)})
            
        @self.app.route('/video_feed')
        def video_feed():
            return Response(self.generate_frames(), 
                        mimetype='multipart/x-mixed-replace; boundary=frame')
        
        # 添加新的API端点用于创建子窗口
        @self.app.route('/api/open_window/<path:path>/<title>/<int:width>/<int:height>')
        def open_window(path, title, width, height):
            try:
                # 检查窗口是否已存在，如果存在则关闭
                if path in self.child_windows:
                    self.child_windows[path].destroy()
                
                # 创建新窗口，不使用parent参数
                window = webview.create_window(
                    title,
                    f'http://127.0.0.1:8917/{path}',
                    width=width,
                    height=height,
                    resizable=False
                )
                
                # 存储窗口引用
                self.child_windows[path] = window
                return jsonify({'success': True})
            except Exception as e:
                self.t.mp.log('cw',f'{e}')

    def run_flask(self):
        self.app.run(host='127.0.0.1', port=8917, debug=False, use_reloader=False)

    def run(self):
        # 在后台启动Flask服务器
        flask_thread = threading.Thread(target=self.run_flask)
        flask_thread.daemon = True
        flask_thread.start()
        
        # 等待服务器启动
        time.sleep(0.1)
        
        self.t.con()

        # 创建主窗口
        self.main_window = webview.create_window(
            '化学笺集自动化滴定项目',
            'http://127.0.0.1:8917/',
            width=1000,
            height=700,
            resizable=True
        )
        
        # 启动webview
        webview.start()

if __name__=='__main__':
    try:
        t=titration.Titration()
        t.mp=message_process.MessageProcessor()
        webview_app=Webview(t)
        webview_app.run()
    except Exception as e:

        print(f'错误：{e}')

