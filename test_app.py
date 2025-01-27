from wcferry import Wcf, enumWeChatProcess, AB, mass_sending, AddGroup, sendlog
import yaml
import threading
from flask import Flask, jsonify, request

app = Flask(__name__)

# 初始化 history_logs
history_logs = {}

CONFIG_PATH = "data/config.yml"
wcf_instances = {}  # 存储每个微信进程的 wcf 实例
wcf = None  # 全局 wcf 变量
renwu_qunfa = False
renwu_yaoqing = False

def read_yaml(config_path=CONFIG_PATH):
    """读取 YAML 配置文件"""
    try:
        with open(config_path, 'r', encoding='utf-8') as file:
            return yaml.safe_load(file)
    except yaml.YAMLError as e:
        sendlog.run(f"读取 YAML 配置文件错误: {e}")
        return {}

def write_yaml_config(config_data, file_path=CONFIG_PATH):
    """写入 YAML 配置文件"""
    try:
        with open(file_path, 'w', encoding='utf-8') as file:
            yaml.dump(config_data, file, allow_unicode=True, sort_keys=False)
        sendlog.run(f"YAML 文件已成功写入: {file_path}")
    except Exception as e:
        sendlog.run(f"写入 YAML 文件错误: {e}")

def chushihua(index):
    """wcf初始化"""
    wcf_instance = None
    port = 1008
    try:
        wcf = Wcf(debug=False, block=False, processIndex=index, port=port)
        port += 10
        denglujieguo = wcf.get_user_info()
        wcf_instance = wcf
        user_info = {
            "name": denglujieguo.get("name"),
            "wxid": denglujieguo.get("wxid"),
            "mobile": denglujieguo.get("mobile")
        }
        sendlog.run(f"成功初始化 Wcf 实例: index = {index}, wxid = {denglujieguo.get('wxid')}")
        # 将 user_info 内容传入 history_logs
        if 'injected_wx' not in history_logs:
            history_logs['injected_wx'] = {}
        history_logs['injected_wx'][index] = user_info
        wcf_instances[index] = wcf_instance
    except Exception as e:
        sendlog.run(f"初始化 Wcf 实例失败 (index: {index}): {e}")
    return wcf_instance

def get_wechat_process_count():
    """获取微信进程数量"""
    if 'process_count' not in history_logs:
        count = enumWeChatProcess()
        history_logs['process_count'] = count
    return history_logs['process_count']

def inject_wcf(index):
    """注入 Wcf 实例"""
    if 'injected_wx' not in history_logs or index not in history_logs['injected_wx']:
        wcf_instance = chushihua(index)
        global wcf
        wcf = wcf_instance
        return wcf_instance
    else:
        sendlog.run(f"微信进程 {index} 已注入，放弃注入")
        return None

def send_group_messages():
    """群发消息"""
    global renwu_qunfa
    if renwu_qunfa:
        return
    renwu_qunfa = True
    try:
        current_wxid = wcf.get_self_wxid()
        pz_data = read_yaml(CONFIG_PATH)
        history_logs['pz_data'] = pz_data  # 将 pz_data 放入 history_logs
        threading.Thread(target=mass_sending.run, args=(wcf, pz_data, current_wxid)).start()
        sendlog.run(f"群发消息开始，wxid: {current_wxid}")
    except Exception as e:
        sendlog.run(f"群发消息失败，wxid: {current_wxid}, 错误: {e}")
    finally:
        renwu_qunfa = False

def invite_friends_to_group(max_invites, current_wxid, invite_name):
    """邀请好友加入群聊"""
    global renwu_yaoqing
    if renwu_yaoqing:
        return
    renwu_yaoqing = True
    try:
        threading.Thread(target=AddGroup.run, args=(wcf, max_invites, current_wxid, invite_name)).start()
        sendlog.run(f"邀请好友开始，wxid: {current_wxid}")
    except Exception as e:
        sendlog.run(f"邀请好友失败，wxid: {current_wxid}, 错误: {e}")
    finally:
        renwu_yaoqing = False

@app.route('/history_logs', methods=['GET'])
def get_history_logs():
    # 确保 pz_data 始终在 history_logs 中
    pz_data = read_yaml(CONFIG_PATH)
    history_logs['pz_data'] = pz_data
    return jsonify(history_logs)

@app.route('/inject', methods=['POST'])
def inject():
    data = request.get_json()
    indexes = data.get('indexes', [])
    for index in indexes:
        inject_wcf(index)
    return jsonify({"status": "success"})

@app.route('/select_wx', methods=['POST'])
def select_wx():
    data = request.get_json()
    index = data.get('index')
    global wcf
    wcf = wcf_instances.get(index)
    return jsonify({"status": "success"})

@app.route('/send_group_messages', methods=['POST'])
def start_send_group_messages():
    send_group_messages()
    return jsonify({"status": "success"})

@app.route('/invite_friends_to_group', methods=['POST'])
def start_invite_friends_to_group():
    data = request.get_json()
    max_invites = data.get('max_invites', 10)
    current_wxid = data.get('current_wxid')
    invite_name = data.get('invite_name', "laqun-0001")
    invite_friends_to_group(max_invites, current_wxid, invite_name)
    return jsonify({"status": "success"})

@app.route('/update_pz_data', methods=['POST'])
def update_pz_data():
    data = request.get_json()
    write_yaml_config(data)
    return jsonify({"status": "success"})

if __name__ == '__main__':
    # 获取微信进程数量
    get_wechat_process_count()
    app.run(debug=True)
