from wcferry import Wcf, enumWeChatProcess, AB, mass_sending, AddGroup, sendlog
import yaml

def read_yaml(config_path = "data/config.yml"):
    """读取 YAML 配置文件"""
    try:
        with open(config_path, 'r', encoding='utf-8') as file:
            return yaml.safe_load(file)
    except yaml.YAMLError as e:
        logging.error(f"Error reading config: {e}")
        return {}

def write_yaml_config(config_data, file_path = "data/config.yml"):
    """写入 YAML 配置文件"""
    try:
        with open(file_path, 'w', encoding='utf-8') as file:
            yaml.dump(config_data, file, allow_unicode=True, sort_keys=False)
        sendlog.run(f"YAML 文件已成功写入: {file_path}")
    except Exception as e:
        sendlog.run(f"写入 YAML 文件时出现错误: {e}")
        
def chushihua(nums=[0]):
    """wcf初始化

    Args:
        nums (list, optional): 进程索引列表，默认为 [0]

    Returns: wcf_instance 为 Wcf 实例，user_info 为登录用户信息字典，包含 name、wxid、mobile 三个字段。
            
    """
    wcf_instances = {}  # 初始化字典
    count = enumWeChatProcess()  # 获取微信进程数量
    sendlog.run(f'WeChat process count: {count}')
    port = 10086  # 初始端口号

    for index in nums:
        try:
            # 创建 Wcf 实例
            wcf = Wcf(debug=False, block=False, processIndex=index, port=port)
            port += 10  # 端口号递增
            denglujieguo = wcf.get_user_info()

            # 将实例和用户信息存入字典，键为进程索引
            wcf_instances[index] = {
                "wcf_instance": wcf,
                "user_info": {
                    "name": denglujieguo.get("name"),
                    "wxid": denglujieguo.get("wxid"),
                    "mobile": denglujieguo.get("mobile")
                }
            }
        except Exception as e:
            # 记录错误日志
            sendlog.run(f"初始化 Wcf 实例时出错 (index: {index}): {e}")
            continue  # 继续处理下一个索引

    return wcf_instances

if __name__ == '__main__':
    wcf_instances = chushihua([1])  # 微信进程从0开始，按照登录顺序，1代表第二个微信

    for index, wcf_instance in wcf_instances.items():
        wcf = wcf_instance["wcf_instance"]
        current_wxid = wcf_instance['user_info']['wxid']
        current_name = wcf_instance['user_info']['name']
        AB.up(wcf, current_wxid, current_name) # 更新数据库
        pz_data = read_yaml("data/config.yml")  # 读取配置文件
        mass_sending.run(wcf, pz_data, current_wxid)  # 群发
        
