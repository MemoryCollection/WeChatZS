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

def chushihua(nums):
    """wcf初始化"""
    wcf_instances = {}
    port = 10086
    for index in nums:
        try:
            wcf = Wcf(debug=False, block=False, processIndex=index, port=port)
            port += 10
            denglujieguo = wcf.get_user_info()
            wcf_instances[index] = {
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
            continue
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

if __name__ == '__main__':
    count = enumWeChatProcess()
    sendlog.run(f'当前已启动微信进程数量: {count}')
    yonghu_id = list(range(count))
    wcf_instances = chushihua(yonghu_id)
    for index, wcf_instance in wcf_instances.items():
        wcf = wcf_instance["wcf_instance"]
        current_wxid = wcf_instance['user_info']['wxid']
        current_name = wcf_instance['user_info']['name']
        current_mobile = wcf_instance['user_info']['mobile']
