from wcferry import Wcf, enumWeChatProcess, AB, mass_sending, AddGroup, sendlog
import yaml

renwu_qunfa = False
renwu_yaoqing = False
CONFIG_PATH = "data/config.yml"

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
    wcf_instances = {}
    port = 1008
    try:
        wcf = Wcf(debug=False, block=False, processIndex=index, port=port)
        port += 10
        denglujieguo = wcf.get_user_info()
        wcf_instances = {
            "wcf_instance": wcf,
            "user_info": {
                "name": denglujieguo.get("name"),
                "wxid": denglujieguo.get("wxid"),
                "mobile": denglujieguo.get("mobile")
            }
        }
        sendlog.run(f"成功初始化 Wcf 实例: index = {index}, wxid = {denglujieguo.get('wxid')}")
    except Exception as e:
        sendlog.run(f"初始化 Wcf 实例失败 (index: {index}): {e}")
    return wcf_instances

def update_user_info(wcf, current_wxid, current_name):
    """更新用户数据库"""
    AB.up(wcf, current_wxid, current_name)

def send_group_messages(wcf, current_wxid, current_name):
    """群发消息"""
    global renwu_qunfa
    renwu_qunfa = True
    try:
        update_user_info(wcf, current_wxid, current_name)
        pz_data = read_yaml(CONFIG_PATH)
        mass_sending.run(wcf, pz_data, current_wxid)
        sendlog.run(f"群发消息成功，wxid: {current_wxid}, name: {current_name}")
    except Exception as e:
        sendlog.run(f"群发消息失败，wxid: {current_wxid}, 错误: {e}")
    finally:
        renwu_qunfa = False

def invite_friends_to_group(wcf, current_wxid, current_name):
    """邀请好友加入群聊"""
    global renwu_yaoqing
    renwu_yaoqing = True
    try:
        update_user_info(wcf, current_wxid, current_name)
        AddGroup.run(wcf, max_invites=10, current_wxid=current_wxid, invite_name="laqun-0001")
        sendlog.run(f"邀请好友成功，wxid: {current_wxid}")
    except Exception as e:
        sendlog.run(f"邀请好友失败，wxid: {current_wxid}, 错误: {e}")
    finally:
        renwu_yaoqing = False

@app.route('/add_log', methods=['POST'])
def add_log():
    """添加日志"""
    log_message = request.json.get('log_message')
    if not log_message:
        return jsonify({'status': 'failure', 'error': 'Log message is required'}), 400
    formatted_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    full_message = f"{formatted_time}: {log_message}"
    history_logs.append(full_message)
    return jsonify({'status': 'success', 'log': full_message})
    
if __name__ == '__main__':
    count = enumWeChatProcess()
    sendlog.run(f'当前已启动微信进程数量: {count}')

