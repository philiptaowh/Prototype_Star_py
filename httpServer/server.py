# 说明：本代码需要在根目录中存在以下路径和文件才能实现完整功能
# "\static"且其中包括一张图片；
# "\templates"其中包括与该服务器匹配的html网页
# "\uploads"其中存储上传的图片，不过该代码能够自动在运行的目录中生成该文件夹

from flask import Flask, request, jsonify, render_template, send_from_directory
from datetime import datetime
import config
from flask_apscheduler import APScheduler
from apscheduler.schedulers.background import BackgroundScheduler
import os
import requests
import json
import math
import re

# 创建Flask对象
app = Flask(__name__)
app.config.from_object(config.Config)

# 新增全局变量用于界面数据
logs = []
latest_image = None
latest_decision = ""
latest_emotion = {"power": 0.0, "state": 2}

# 应用配置
app.config['SCHEDULER_EXECUTORS'] = {'default': {'type': 'threadpool', 'max_workers': 10}}
app.config['SCHEDULER_JOBSTORES'] = {'default': {'type': 'memory'}}
app.config.from_object(config.Config)

UPLOAD_FOLDER = 'uploads/'
DATA_FILE = 'data.txt'
ALLOWED_EXTENSIONS = {'jpg', 'jpeg', 'png'}
LLM_Authorization = 'Bearer bce-v3/ALTAK-BSx79U9x4vqNeDAMFIYq9/4bb4fb9a66f47f666e0c8fe8b742935ca26e2dd0'
LLM_API_URL_conversation = "https://qianfan.baidubce.com/v2/app/conversation"
LLM_API_URL_run = "https://qianfan.baidubce.com/v2/app/conversation/runs"
LLM_API_URL_file = "https://qianfan.baidubce.com/v2/app/conversation/file/upload"
Conversation_ID = ""
app_ID1 = "96f41255-639c-4b93-8342-4dc8aeae3f84" # 实验1的ID
app_ID2 = "851e5985-9f1d-4eef-88eb-7a9f429da3e2" # 实验2的ID
app_ID3 = "b2d1bcbf-9e30-4b1d-9119-0ab5f209b2ef" # 实验3的ID
# ESP32的在线状态，0不在，1在
ESP32_Cam_State = 0 
ESP32_Robot_State = 0 
# ESP32在线时间统计，保持在线5分钟不刷新就自动置为离线
ESP32_cam_last_active = None
ESP32_robot_last_active = None

# 初始化机器人控制相关的变量
dM = [0] * 15          # 情绪缓存数组
LLM_EmotionReturn = 0   # LLM情绪返回值，用于更新dM的变量
renew_Flag = 0          # 刷新标志，用于控制刷新运动和情绪决策量的频率
# Emotion_Lock = 0        # 情绪锁标志，用于确保幸福和休息能够维持几个动作周期，由于LLM响应和机器人执行的速度高度不对等，暂时失能这个机制
Emotion = 2             # 当前情绪状态，取值0到4，直接控制RobotBody
Move = 0                # 当前执行动作，取值0到5，直接控制RobotBody
LLM_AnalysisReturn = "你刚刚准备开始运动，运动次数0，情绪评分0，不知道附近环境的情况" # LLM图片理解返回值，用于辅助LLM判断情绪返回值

# 创建APScheduler对象
scheduler = APScheduler(scheduler=BackgroundScheduler(daemon=True))
scheduler.init_app(app)
scheduler.start()

# 确保上传目录存在
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# 在线时间检查任务，1分钟查一次
@scheduler.task(id='esp32_state_check', trigger='interval', seconds=60)
def check_esp32_state():
    global ESP32_Cam_State, ESP32_Robot_State
    global ESP32_cam_last_active, ESP32_robot_last_active
    
    current_time = datetime.now()
    
    # 检查摄像头ESP32状态
    if ESP32_Cam_State == 1 and ESP32_cam_last_active:
        time_diff = (current_time - ESP32_cam_last_active).total_seconds()
        if time_diff > 300:  # 5分钟 = 300秒
            ESP32_Cam_State = 0
            logs.append(f"SYSTEM: [{current_time}] ESP32_Cam状态超时重置：离线")
            print(f"[状态监控] ESP32_Cam 持续在线超过5分钟，已重置为离线")
    
    # 检查机器人ESP32状态
    if ESP32_Robot_State == 1 and ESP32_robot_last_active:
        time_diff = (current_time - ESP32_robot_last_active).total_seconds()
        if time_diff > 300:  # 5分钟 = 300秒
            ESP32_Robot_State = 0
            logs.append(f"SYSTEM: [{current_time}] ESP32_Robot状态超时重置：离线")
            print(f"[状态监控] ESP32_Robot 持续在线超过5分钟，已重置为离线")

# 定时情绪分析任务，10s检查一次
@scheduler.task(id='mental_power_job', trigger='interval', seconds=10)
def decide_mental_power():
    global LLM_EmotionReturn, Emotion, Move, renew_Flag, latest_emotion

    if renew_Flag == 1:
        Mental_power = 0.0
        renew_Flag -= 1
        
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
        elif Mental_power > 100: # 幸福状态，锁定情绪和动作
            Emotion = 0
            Move = 5
        else:
            Emotion = 4
            Move = 4
        
        print(f"[状态更新] 当前情绪状态：{get_emotion_text(Emotion)}")
        # 更新情绪数据
        latest_emotion["power"] = Mental_power
        latest_emotion["state"] = Emotion
        logs.append(f"SYSTEM: [{datetime.now()}] 情绪更新：{get_emotion_text(Emotion)} ({Mental_power:.2f})")

# 将情绪代码转换为文字描述
def get_emotion_text(code):
    emotions = {
        0: "幸福", 1: "高兴",
        2: "平静", 3: "低落",
        4: "疲倦"
    }
    return emotions.get(code, "未知状态")

# 将动作代码转换为文字描述
def get_move_text(code):
    movements = {
        0: "前进", 1: "左转",
        2: "右转", 3: "后退",
        4: "休息", 5: "跳舞"
    }
    return movements.get(code, "未知状态")

# 将在线状态代码转化为文字描述
def get_state_text(code):
    states = {
        0: "离线", 1: "在线",
    }
    return states.get(code, "未知状态")

# 除去大模型格式偏差函数
def extract_number(s):
    match = re.search(r'-?\d+', s)
    return int(match.group()) if match else None

def allowed_file(filename):
    return '.' in filename and filename.split('.', 1) in ALLOWED_EXTENSIONS

# 大模型创建对话
def create_llm(app_ID):
    global Conversation_ID
    try:
        # 新建对话
        payload = json.dumps({
              "app_id": app_ID,
        }, ensure_ascii=False)
        headers = {
            'Content-Type': 'application/json',
            'Authorization': LLM_Authorization
        }
          
        response = requests.request("POST", LLM_API_URL_conversation, headers=headers, data=payload.encode("utf-8"))
        
        # 提取对话ID
        Conversation_ID = response.text.split("\"")[7]

        return response
    except Exception as e:
        print(f"[LLM ERROR] API调用失败: {str(e)}")
        return None
    
# 大模型进行对话
def query_llm(app_ID, question):
    global Conversation_ID
    try:         
        # 对话
        payload = json.dumps({
            "app_id": app_ID,
            "query": question,
            "conversation_id": Conversation_ID,
            "stream": False
        }, ensure_ascii=False)
        headers = {
            'Content-Type': 'application/json',
            'Authorization': LLM_Authorization
        }
        
        raw_response = requests.request("POST", LLM_API_URL_run, headers=headers, data=payload.encode("utf-8"))
        
        response = json.loads(raw_response.text)
        print(response["answer"])

        return response["answer"]
    except Exception as e:
        print(f"[LLM ERROR] API调用失败: {str(e)}")
        return None
    
# 大模型上传文件
def upload_llm(app_ID, fileName):
    global Conversation_ID
    try:
        # 会话文件上传
        payload = {
              "app_id": app_ID,
              "conversation_id": Conversation_ID
        }

        headers = {
            'Authorization': LLM_Authorization
        }
        files = [
            ('file',("image.jpg",open(fileName,'rb'),'image/jpeg'))# 字段名, (服务器接收到的文件名,文件数据,文件种类)
        ]
        response = requests.request("POST", LLM_API_URL_file, headers=headers, data=payload, files=files)

        # 提取图片ID
        image_ID = response.text.split("\"")[7]

        return image_ID
    except Exception as e:
        print(f"[LLM ERROR] API调用失败: {str(e)}")
        return None
    
# 大模型进行对话（带图片）
def picQuery_llm(app_ID, question, pic_ID):
    global Conversation_ID
    try:         
        payload = json.dumps({
        "app_id": app_ID,
        "query": question,
        "conversation_id": Conversation_ID,
        "stream": False,
        "file_ids": [
            pic_ID
        ]
        }, ensure_ascii=False)
        headers = {
            'Content-Type': 'application/json',
            'Authorization': 'Bearer bce-v3/ALTAK-BSx79U9x4vqNeDAMFIYq9/4bb4fb9a66f47f666e0c8fe8b742935ca26e2dd0'
        }
        
        raw_response = requests.request("POST", LLM_API_URL_run, headers=headers, data=payload.encode("utf-8"))
        response = json.loads(raw_response.text)
        print(response["answer"])

        return response["answer"]
    except Exception as e:
        print(f"[LLM ERROR] API调用失败: {str(e)}")
        return None
    
def answer_process(answer):
    global LLM_AnalysisReturn, Move, renew_Flag, LLM_EmotionReturn, dM

    # 缓存更新前数据，便于后续编辑LLM的问题
    past_Move = "你" + get_move_text(Move) + "，"
    past_EmotionPower = "情绪评分" + str(dM[14]) + "，"

    # 接收并分析动作信息
    if answer.split("\"")[3] == "前进":
        Move = 0
    elif answer.split("\"")[3] == "左转":
        Move = 1
    elif answer.split("\"")[3] == "右转":
        Move = 2
    elif answer.split("\"")[3] == "后退":
        Move = 3
    
    # 接收对现状的分析
    LLM_AnalysisReturn = answer.split("\"")[7]
    # 接收情绪评分
    LLM_EmotionReturn = extract_number(answer.split("\"")[11])

    renew_Flag = 1

    # 在原来的基础上，做一定的信息补充，便于下一次分析
    LLM_AnalysisReturn = past_Move + past_EmotionPower + "你发现" + LLM_AnalysisReturn
    print(LLM_AnalysisReturn)

    return 0

# 图片数据上传路由
@app.route('/upload', methods=['POST'])
def upload_image():
    # 界面用全局变量
    global latest_image, logs, latest_decision, ESP32_Cam_State, ESP32_cam_last_active

    ESP32_Cam_State = 1
    ESP32_cam_last_active = datetime.now()  # 更新最后活跃时间
    log_entry = f"STATE: [{datetime.now()}] 单片机ESP32_Cam状态更新：在线"
    logs.append(log_entry)

    # 校验 API 密钥
    api_key = request.headers.get('X-API-KEY')
    if api_key != '12345678':
        print("[ERROR] 未通过验证")
        logs.append("UPLOAD: [ERROR] 未通过验证")
        return jsonify({"error": "Unauthorized"}), 401
    
    # 检查文件是否存在
    if 'image' not in request.files:
        print("[ERROR] 请求错误")
        logs.append("UPLOAD: [ERROR] 请求错误")
        return jsonify({"error": "No file part"}), 400
    
    file = request.files['image']

    if file.filename == '':
        print("[ERROR] 无效文件名")
        logs.append("UPLOAD: [ERROR] 无效文件名")
        return jsonify({"error": "No selected file"}), 400
    
    if file:
        try:
            # 读取十六进制字符串
            hex_str = file.read().decode('utf-8')
            
            # 转换十六进制到二进制
            binary_data = bytes.fromhex(hex_str)
            
            # 生成文件名
            timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
            filename = f"esp32cam_{timestamp}.jpg"
            save_path = os.path.join(UPLOAD_FOLDER, filename)
            
            # 写入二进制文件
            with open(save_path, 'wb') as f:
                f.write(binary_data)

            # 新增日志记录
            log_entry = f"UPLOAD: [{datetime.now()}] 收到图片上传：{filename}"
            logs.append(log_entry)
            latest_image = save_path

            create_llm(app_ID3) # 由于目前只能上传一张图片，因此每次对话都需要更新对话的ID
            pic_ID = upload_llm(app_ID3, save_path)
            answer = picQuery_llm(app_ID3, LLM_AnalysisReturn, pic_ID)
            answer_process(answer)

            # 记录决策信息
            latest_decision = answer
            log_entry = f"UPLOAD: [{datetime.now()}] 模型决策：{answer}"
            logs.append(log_entry)
            
            return jsonify({
                "status": "success",
            }), 200
            
        except ValueError as e:
            print(f"[ERROR] 十六进制转换失败: {str(e)}")
            logs.append(f"UPLOAD: [ERROR] 十六进制转换失败: {str(e)}")
            return jsonify({"error": "Invalid hex format"}), 400
        except Exception as e:
            print(f"[ERROR] 处理失败: {str(e)}")
            logs.append(f"UPLOAD: [{datetime.now()}] 处理失败: {str(e)}")
            return jsonify({"error": "File processing failed"}), 500
    else:
        print("[ERROR] 无效文件类型")
        logs.append("UPLOAD: [ERROR] 无效文件类型")
        return jsonify({"error": "Invalid file type"}), 400

# 机器人控制单片机数据下载路由
@app.route('/Robot_Control', methods=['GET'])
def offer_Instruct():
    global ESP32_Robot_State, ESP32_robot_last_active

    ESP32_Robot_State = 1
    ESP32_robot_last_active = datetime.now()  # 更新最后活跃时间
    log_entry = f"STATE: [{datetime.now()}] 单片机ESP32_Robot状态更新：在线"
    logs.append(log_entry)

    # 统一API密钥验证
    api_key = request.headers.get('X-API-KEY')
    if api_key != '12345678':
        print("[ERROR] 未通过验证")
        logs.append("Robot_Control: [ERROR] 未通过验证")
        return jsonify({"error": "Unauthorized"}), 401
    
    log_entry = f"Robot_Control: [{datetime.now()}] 控制数据下载：{get_emotion_text(Emotion)}, {get_move_text(Move)}"
    logs.append(log_entry)
    return jsonify({
                "emotion": Emotion,
                "move": Move
            }), 200

# ESP32状态监控路由
@app.route('/state', methods=['POST'])
def get_state():
    global ESP32_Cam_State, ESP32_Robot_State, ESP32_cam_last_active, ESP32_robot_last_active
    # 统一API密钥验证
    api_key = request.headers.get('X-API-KEY')
    if api_key != '12345678':
        print("[ERROR] 未通过验证")
        logs.append("STATE: [ERROR] 未通过验证")
        return jsonify({"error": "Unauthorized"}), 401
    
    device = None
    state = None
    data = request.json
    device = data.get('device') if data else None
    state = int(data.get('state')) if data else None

    if device == None or state == None:
        print("[ERROR] 格式错误")
        logs.append("STATE: [ERROR] 格式错误")
        return jsonify({"error": "wrong format"}), 401
    
    if device == "ESP32_Cam":
        ESP32_Cam_State = state
        ESP32_cam_last_active = datetime.now()  # 更新最后活跃时间
    elif device == "ESP32_Robot":
        ESP32_Robot_State = state
        ESP32_robot_last_active = datetime.now()
    log_entry = f"STATE: [{datetime.now()}] 单片机{device}状态更新：{get_state_text(state)}"
    logs.append(log_entry)
        
    return jsonify({
                "status": "success",
            }), 200

# 界面路由
@app.route('/')
def interface():
    return render_template('interface.html')

# 界面路由中使用的数据接口
@app.route('/get_logs')
def get_logs():
    return jsonify(logs)

@app.route('/get_decision')
def get_decision():
    if latest_decision != "":
        now_step = latest_decision.split("\"")[3]
        now_Emotion = latest_decision.split("\"")[11]
        now_word = latest_decision.split("\"")[7]
    else:
        now_step = "--"
        now_Emotion = "--"
        now_word = "--"
    return jsonify({
        "step": now_step,
        "Emotion": now_Emotion,
        "word": now_word
        })

@app.route('/get_emotion')
def get_emotion():
    return jsonify({
        "power": latest_emotion["power"],
        "state": get_emotion_text(latest_emotion["state"]),
        "camState": ESP32_Cam_State,  # 新增摄像头模块状态
        "robotState": ESP32_Robot_State  # 新增机器人控制模块状态
    })

@app.route('/get_image')
def get_image():
    return jsonify({"image": latest_image})

# 在界面显示图片的接口，与上面一个一起生效
@app.route('/uploads/<filename>')
def serve_uploaded_file(filename):
    return send_from_directory(
        os.path.abspath(UPLOAD_FOLDER),  # 使用绝对路径更安全
        filename,
        mimetype='image/jpeg'  # 显式指定MIME类型
    )

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
