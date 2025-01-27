import time
import random
import sqlite3
from wcferry import sendlog

db_path = "data/data.db"  # 数据库路径

class Database:
    def __init__(self, path):
        self.path = path

    def __enter__(self):
        self.conn = sqlite3.connect(self.path)
        self.cursor = self.conn.cursor()
        return self.cursor

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.conn:
            self.conn.commit()
            self.conn.close()

def get_random_emojis():
    """获取随机表情符号。"""
    emojis = ["😀", "😂", "🥺", "😍", "😎", "👍", "👀", "💔", "🎉", "🔥"]
    return ''.join(random.sample(emojis, random.randint(1, 3)))

def get_random_phrase(file_path):
    """从指定文件中随机获取一条消息。"""
    file_path = f"data/{file_path}.txt"
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            phrases = [phrase.strip() for phrase in file.read().split("----\n") if phrase.strip()]
            if not phrases:
                sendlog.run(f"文件 {file_path} 为空。")
                return ""
            return random.choice(phrases)
    except FileNotFoundError:
        sendlog.run(f"文件 {file_path} 不存在。")
    except Exception as e:
        sendlog.run(f"读取文件 {file_path} 时发生异常：{e}")
    return ""

def send_message(wxid, message, wcf):
    """发送消息到指定的群聊。"""
    try:
        send_status = wcf.send_text(message, wxid)
        if send_status != 0:
            sendlog.run(f"发送失败：{wxid}，状态码：{send_status}")
            return False
        return True
    except Exception as e:
        sendlog.run(f"发送消息时发生异常：{wxid}，异常信息：{e}")
        return False

def query_micro_msg_sessions(wcf):
    """查询微信数据库中的群聊信息。"""
    sendlog.run("查询: 微信  数据库 ")
    try:
        result = wcf.query_sql("MicroMsg.db", "SELECT strUsrName, nUnReadCount FROM Session WHERE strUsrName LIKE '%@chatroom%';")
        return {group['strUsrName']: group for group in result}
    except Exception as e:
        sendlog.run(f"查询微信数据库时发生异常：{e}")
    return {}

def query_local_contacts(class_name, current_wxid):
    """查询本地数据库中指定分类的群聊。"""
    sendlog.run(f"查询: 本地  数据库  {class_name}  分类")
    try:
        with Database(db_path) as cursor:
            cursor.execute(f"SELECT wxid, name, nUnReadCount, nTime FROM {current_wxid} WHERE class=?", (class_name,))
            return {row[0]: (row[1], row[2], row[3]) for row in cursor.fetchall()}
    except Exception as e:
        sendlog.run(f"查询本地数据库时发生异常：{class_name}，异常信息：{e}")
    return {}

def update_local_contact(wxid, nUnReadCount, nTime, current_wxid):
    """更新本地数据库中的群聊未读消息数和时间戳。"""
    try:
        with Database(db_path) as cursor:
            cursor.execute(f"UPDATE {current_wxid} SET nUnReadCount=?, nTime=? WHERE wxid=?", (nUnReadCount, nTime, wxid))
    except Exception as e:
        sendlog.run(f"更新本地数据库时发生异常：{wxid}，异常信息：{e}")

def process_group_messages(class_name, wcf, pz_data, qf_num, current_wxid):
    """处理指定分类的群聊消息，判断是否符合发送条件并发送消息。"""
    local_groups = query_local_contacts(class_name, current_wxid)
    if not local_groups:
        sendlog.run(f"本地数据库中 {class_name} 分类没有群聊信息。")
        return qf_num

    micro_msg_groups = query_micro_msg_sessions(wcf)
    if not micro_msg_groups:
        sendlog.run("微信数据库中没有群聊信息。")
        return qf_num

    sendlog.run(f"---------------------------   {class_name}   ---------------------------")
    for wxid, (local_name, local_nUnReadCount, local_nTime) in local_groups.items():
        group = micro_msg_groups.get(wxid)
        if not group:
            continue

        nUnReadCount = group['nUnReadCount']
        nTime = int(time.time())

        # 判断是否需要发送消息
        if (nUnReadCount - local_nUnReadCount) > pz_data['群发配置']['消息间隔'] or (nTime - local_nTime) > (pz_data['群发配置']['消息天数'] * 24 * 3600):
            message = random.choice(pz_data['群发配置']['话术配置'][class_name]) + get_random_emojis()

            if send_message(wxid, message, wcf):
                update_local_contact(wxid, nUnReadCount, nTime, current_wxid)
                qf_num += 1
                random_rest = random.randint(pz_data['群发配置']['最小时间'], pz_data['群发配置']['最大时间'])
                if qf_num % 80 == 0:
                    random_rest = random.randint(600, 1800)
                sendlog.run(f"已群发：{qf_num}，休息：{random_rest}秒  群聊: {local_name}")
                time.sleep(random_rest)
            else:
                sendlog.run(f"群聊: {local_name} 发送失败")
    return qf_num

def run(wcf, pz_data, current_wxid):
    qf_num = 0
    qunfa_list = pz_data['群发配置']['群发群组']
    if not qunfa_list:
        sendlog.run("群发配置中没有指定群发群组。")
        return

    for class_name in qunfa_list:
        qf_num = process_group_messages(class_name, wcf, pz_data, qf_num, current_wxid)
    sendlog.run("群发完成。")
