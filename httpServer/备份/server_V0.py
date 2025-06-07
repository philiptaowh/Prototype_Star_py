from flask import Flask, request, jsonify
import os
from datetime import datetime
import requests
import json
import binascii
import base64

app = Flask(__name__)
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

# 确保上传目录存在
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

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
    
# 大模型进行对话（带图片）
def picQuery_llm(app_ID, question, pic_ID):
    global Conversation_ID
    try:         
        # 发起对话
        
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

        return response
    except Exception as e:
        print(f"[LLM ERROR] API调用失败: {str(e)}")
        return None

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

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
