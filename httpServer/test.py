from flask import Flask, request, jsonify
import os
from datetime import datetime
import binascii
import base64

import threading
import math
import time

app = Flask(__name__)
UPLOAD_FOLDER = 'uploads/'
DATA_FILE = 'data.txt'
ALLOWED_EXTENSIONS = {'jpg', 'jpeg', 'png'}

# # 全局情绪缓存空间、LLM拆解数据（暂时定义，后续看情况删除）、LLM结果刷新标志
# dM = [0] * 15
# LLM_EmotionReturn = 0
# renew_Flag = 1
# # 当前情绪：0 幸福,1 高兴,2 平静,3 低落,4 疲倦
# Emotion = 2

# 线程锁
# lock = threading.Lock()

# # 情绪状态决策函数
# def decide_Mental_Power():
#     global LLM_EmotionReturn, Emotion

#     time.sleep(1)
    
#     if renew_Flag == 1:
#       Mental_power = 0.0
#       # renew_Flag = 0 # 等待下一次LLM_EmotionReturn刷新

#       # 更新缓存数组数据
#       dM.pop(0)
#       dM.append(LLM_EmotionReturn)
      
#       # 根据记忆&遗忘机制计算情绪值
#       Mental_power += dM[14]
#       for x in range(14):
#           Mental_power += dM[x] * math.exp((x - 15) / 2)
#       print(f"当前情绪值和为：{Mental_power}")

#       # 情绪值决策情绪状态
#       if Mental_power >= -70 and Mental_power <= 70:
#           Emotion = 2
#       elif Mental_power > 70 and Mental_power <= 100:
#           Emotion = 1
#       elif Mental_power < -70 and Mental_power >= -100:
#           Emotion = 3
#       elif Mental_power > 100:
#           Emotion = 0
#       elif Mental_power < -100:
#           Emotion = 4

# # 启动后台线程
# timer_thread = threading.Thread(target=decide_Mental_Power)
# # timer_thread.daemon = True  # 设置为守护线程
# timer_thread.start()

# 确保上传目录存在
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def allowed_file(filename):
    return '.' in filename and filename.split('.', 1) in ALLOWED_EXTENSIONS

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
            
            return jsonify({
                "status": "success",
                "filename": filename,
                "size": len(binary_data)
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


@app.route('/uploadJson', methods=['POST'])
def upload_imageJson():
    # 校验 API 密钥（保留原逻辑）
    api_key = request.headers.get('X-API-KEY')
    if api_key != '12345678':
        return jsonify({"error": "Unauthorized"}), 401

    # 校验 Content-Type
    if not request.is_json:
        return jsonify({"error": "Unsupported Media Type"}), 415

    # 解析 JSON
    try:
        raw_data = request.get_data()  # 原始二进制数据

        data = request.get_json()
        if data:
            print("[DEBUG] Get Json")
            print("[DEBUG] 'filename':", data['filename'])
            filename = data['filename']
            img_data = data['data']
            
            binary_data = base64.b64decode(img_data)

            timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
            new_filename = f"esp32cam_{timestamp}_{filename}"
            save_path = UPLOAD_FOLDER + new_filename
            print(save_path)

            f = open(save_path, 'wb')
            f.write(binary_data)
            f.close()

            return jsonify({
                "status": "success",
            }), 200
        else:
            print("[DEBUG] No JSON data parsed.")
            return jsonify({
                "ERROR": "Can not read Json",
            }), 400

    except Exception as e:  # 捕获 JSON 解析等错误
        app.logger.error("Malformed JSON error. Raw data: %s", raw_data.decode('utf-8', errors='replace'))
        return jsonify({"error": "Malformed JSON"}), 400

@app.route('/data', methods=['GET', 'POST'])  # 同时支持GET和POST
def handle_data():
    global LLM_EmotionReturn, Emotion

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
                print("[SUCCESS] 数据已发送")
                return jsonify({
                    "status": "success",
                    "data": f.read()
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
            with open(DATA_FILE, 'a', encoding='utf-8') as f:
                f.write(content + '\n')  # 自动添加换行符
                print("[SUCCESS] 数据已追加")
            return jsonify({
                "status": "success",
                "message": "数据已追加",
                "length": len(content)
            }), 201
        except Exception as e:
            print("[ERROR] 写入失败: " + {str(e)})
            return jsonify({"error": f"写入失败: {str(e)}"}), 500

    # 处理其他方法
    print("[ERROR] 方法不允许")
    return jsonify({"error": "方法不允许"}), 405

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)

