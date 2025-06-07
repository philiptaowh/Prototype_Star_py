from flask import Flask, request, jsonify
import datetime
import config
from flask_apscheduler import APScheduler
from apscheduler.schedulers.background import BackgroundScheduler
import os
from datetime import datetime
import requests
import json
import math
import re

# 创建Flask对象
app = Flask(__name__)

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

# 定时情绪分析任务，10s检查一次
@scheduler.task(id='mental_power_job', trigger='interval', seconds=10)
def decide_mental_power():
    global LLM_EmotionReturn, Emotion, Move, renew_Flag

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
        # 发起对话
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
        payload = {
              "app_id": app_ID,
              "conversation_id": Conversation_ID
        }

        headers = {
            'Authorization': 'Bearer bce-v3/ALTAK-BSx79U9x4vqNeDAMFIYq9/4bb4fb9a66f47f666e0c8fe8b742935ca26e2dd0'
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

@app.route('/upload', methods=['POST'])
def upload_image():
    # 校验 API 密钥
    api_key = request.headers.get('X-API-KEY')
    if api_key != '12345678':
        print("[ERROR] 未通过验证")
        return jsonify({"error": "Unauthorized"}), 401
    
    # 检查文件是否存在
    if 'image' not in request.files:
        print("[ERROR] 请求错误")
        return jsonify({"error": "No file part"}), 400
    
    file = request.files['image']

    if file.filename == '':
        print("[ERROR] 无效文件名")
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

            create_llm(app_ID3) # 由于目前只能上传一张图片，因此每次对话都需要更新对话的ID
            pic_ID = upload_llm(app_ID3, save_path)
            answer = picQuery_llm(app_ID3, LLM_AnalysisReturn, pic_ID)
            answer_process(answer)
            
            return jsonify({
                "status": "success",
            }), 200
            
        except ValueError as e:
            print(f"[ERROR] 十六进制转换失败: {str(e)}")
            return jsonify({"error": "Invalid hex format"}), 400
        except Exception as e:
            print(f"[ERROR] 处理失败: {str(e)}")
            return jsonify({"error": "File processing failed"}), 500
    else:
        print("[ERROR] 无效文件类型")
        return jsonify({"error": "Invalid file type"}), 400

@app.route('/data', methods=['GET', 'POST'])  # 同时支持GET和POST
def handle_data():
    # 统一API密钥验证
    api_key = request.headers.get('X-API-KEY')
    if api_key != '12345678':
        print("[ERROR] 未通过验证")
        return jsonify({"error": "Unauthorized"}), 401

    # 处理GET请求
    if request.method == 'GET':
        if not os.path.exists(DATA_FILE):
            print("[ERROR] data文件未找到")
            return jsonify({"error": "data.txt not found"}), 404

        try:
            with open(DATA_FILE, 'r', encoding='utf-8') as f:
                create_llm(app_ID1)
                query = "当前温度：" + str(f.read())
                answer = query_llm(app_ID1, query)

                print("[SUCCESS] 数据已发送")
                return jsonify({
                    "status": "success",
                    "data": answer
                }), 200
        except Exception as e:
            print("[ERROR] 读取失败: " + {str(e)})
            return jsonify({"error": f"读取失败: {str(e)}"}), 500

    # 处理POST请求
    elif request.method == 'POST':
        # 获取请求数据（支持多种格式）
        content = None
        
        # 尝试从不同格式获取数据
        if request.content_type == 'application/json':
            data = request.json
            content = data.get('data') if data else None
        elif request.content_type == 'text/plain':
            content = request.data.decode('utf-8')
        elif 'form-data' in request.content_type:
            content = request.form.get('data')
        
        # 验证数据有效性
        if not content or not isinstance(content, str):
            print("[ERROR] 无效数据内容")
            return jsonify({"error": "无效数据内容"}), 400

        # 写入文件（追加模式）
        try:
            with open(DATA_FILE, 'w', encoding='utf-8') as f:
                f.write(content + '\n')  # 自动添加换行符
                print("[SUCCESS] 数据已更新")
            return jsonify({
                "status": "success",
                "message": "数据已更新",
                "length": len(content)
            }), 201
        except Exception as e:
            print("[ERROR] 写入失败: " + {str(e)})
            return jsonify({"error": f"写入失败: {str(e)}"}), 500

    # 处理其他方法
    print("[ERROR] 方法不允许")
    return jsonify({"error": "方法不允许"}), 405

@app.route('/Robot_Control', methods=['GET'])
def offer_Instruct():
    # 统一API密钥验证
    api_key = request.headers.get('X-API-KEY')
    if api_key != '12345678':
        print("[ERROR] 未通过验证")
        return jsonify({"error": "Unauthorized"}), 401
    
    return jsonify({
                "emotion": Emotion,
                "move": Move
            }), 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
