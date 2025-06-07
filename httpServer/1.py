# 导入所有依赖库
from flask import Flask, request, jsonify
import datetime
import config
from flask_apscheduler import APScheduler
from apscheduler.schedulers.background import BackgroundScheduler
import os
import math
import time
import binascii
import base64

# 创建Flask对象
app = Flask(__name__)

# 应用配置
app.config['SCHEDULER_EXECUTORS'] = {'default': {'type': 'threadpool', 'max_workers': 10}}
app.config['SCHEDULER_JOBSTORES'] = {'default': {'type': 'memory'}}
app.config.from_object(config.Config)

# 文件上传配置
UPLOAD_FOLDER = 'uploads/'
DATA_FILE = 'data.txt'
ALLOWED_EXTENSIONS = {'jpg', 'jpeg', 'png'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# 确保上传目录存在
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# 初始化全局情绪变量
dM = [0] * 15          # 情绪缓存数组
LLM_EmotionReturn = 0   # LLM情绪返回值
renew_Flag = 1          # 刷新标志
Emotion = 2             # 当前情绪状态

# 创建APScheduler对象
scheduler = APScheduler(scheduler=BackgroundScheduler(daemon=True))
scheduler.init_app(app)
scheduler.start()

# 定时情绪分析任务（每分钟执行一次）
@scheduler.task(id='mental_power_job', trigger='interval', seconds=10)
def decide_mental_power():
    global LLM_EmotionReturn, Emotion

    if renew_Flag == 1:
        Mental_power = 0.0
        
        # 更新缓存数组数据
        dM.pop(0)
        dM.append(LLM_EmotionReturn)
        
        # 计算情绪能量值（带记忆衰减）
        Mental_power += dM[14]  # 最新数据
        for x in range(14):
            Mental_power += dM[x] * math.exp((x - 15) / 2)
        
        print(f"[情绪分析] 当前情绪能量值：{Mental_power:.2f}")

        # 情绪状态决策逻辑
        if -70 <= Mental_power <= 70:
            Emotion = 2
        elif 70 < Mental_power <= 100:
            Emotion = 1
        elif -100 <= Mental_power < -70:
            Emotion = 3
        elif Mental_power > 100:
            Emotion = 0
        else:
            Emotion = 4
        
        print(f"[状态更新] 当前情绪状态：{get_emotion_text(Emotion)}")

def get_emotion_text(code):
    """将情绪代码转换为文字描述"""
    emotions = {
        0: "幸福", 1: "高兴",
        2: "平静", 3: "低落",
        4: "疲倦"
    }
    return emotions.get(code, "未知状态")

# 文件上传路由
def allowed_file(filename):
    """检查文件扩展名是否合法"""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/upload', methods=['POST'])
def upload_image():
    """处理图片上传请求"""
    # API密钥验证
    api_key = request.headers.get('X-API-KEY')
    if api_key != '12345678':
        print("[安全警报] 无效API密钥尝试访问")
        return jsonify({"error": "Unauthorized"}), 401

    # 文件存在性检查
    if 'image' not in request.files:
        print("[请求错误] 缺少文件参数")
        return jsonify({"error": "No file part"}), 400

    file = request.files['image']
    if file.filename == '':
        print("[请求错误] 空文件名")
        return jsonify({"error": "No selected file"}), 400

    if file and allowed_file(file.filename):
        try:
            # 十六进制转二进制处理
            hex_str = file.read().decode('utf-8')
            binary_data = bytes.fromhex(hex_str)
            
            # 生成带时间戳的文件名
            timestamp = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
            filename = f"esp32cam_{timestamp}.jpg"
            save_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            
            # 保存文件并记录元数据
            with open(save_path, 'wb') as f:
                f.write(binary_data)
            
            print(f"[文件操作] 成功保存图片：{filename}")
            return jsonify({
                "status": "success",
                "filename": filename,
                "size": len(binary_data),
                "emotion_status": get_emotion_text(Emotion)
            }), 200

        except ValueError as e:
            print(f"[格式错误] 十六进制转换失败：{str(e)}")
            return jsonify({"error": "Invalid hex format"}), 400
        except Exception as e:
            print(f"[系统错误] 文件处理异常：{str(e)}")
            return jsonify({"error": "File processing failed"}), 500
    else:
        print("[请求错误] 不支持的文件类型")
        return jsonify({"error": "Invalid file type"}), 400

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)