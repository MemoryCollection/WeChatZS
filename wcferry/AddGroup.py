import time
import random
import sqlite3
import json
from wcferry import sendlog

def run(wcf, max_invites=10, current_wxid = "wxid_mouekuvkxa3v22", class_name = "未分", invite_name="laqun-0001"):
    """邀请目标加入群聊：laqun-0001。
        wcf (Wcf): Wcf 对象。
        max_invites (int): 最大邀请次数。
        current_wxid (str): 当前登录的微信号。
        class_name (str): 群分类名称。
        invite_name (str): 被邀请者的备注名称。
    """
    sendlog.run(f"开始邀请目标加入群聊：{invite_name}, 最大邀请次数：{max_invites}, 群分类：{class_name}。")

    db_path = "data/data.db"  # 数据库路径

    def fetch_data(query, params):
        """执行查询并返回结果。"""
        try:
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            cursor.execute(query, params)
            return cursor.fetchall()
        except sqlite3.Error as e:
            sendlog.run(f"数据库查询错误: {e}")
            return []
        finally:
            conn.close()

    def get_wxid_and_invite_history():
        """从数据库获取指定联系人 wxid 和其邀请历史。"""
        result = fetch_data(f"SELECT wxid, invite_history FROM {current_wxid} WHERE remark=?", (invite_name,))
        if not result:
            return None, []

        wxid, invite_history = result[0]
        try:
            invite_history = json.loads(invite_history) if invite_history else []
        except json.JSONDecodeError:
            sendlog.run("邀请历史解析失败，初始化为空列表。")
            invite_history = []
        return wxid, invite_history

    def get_group_info_by_class():
        """从数据库获取指定分类的群信息，包括群 wxid 和名称。"""
        return fetch_data(f"SELECT wxid, name, MemberNum, wxidList FROM {current_wxid} WHERE class=?", (class_name,))

    def update_invite_history(wxid, group_wxid):
        """更新指定联系人 wxid 的邀请历史。"""
        try:
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()

            # 获取当前联系人 invite_history
            cursor.execute(f"SELECT invite_history FROM {current_wxid} WHERE wxid=?", (wxid,))
            result = cursor.fetchone()
            invite_history = json.loads(result[0]) if result and result[0] else []

            # 如果群 wxid 不在 invite_history 中，加入并更新
            if group_wxid not in invite_history:
                invite_history.append(group_wxid)
                cursor.execute(f"UPDATE {current_wxid} SET invite_history=? WHERE wxid=?", (json.dumps(invite_history), wxid))
                conn.commit()
        except (sqlite3.Error, json.JSONDecodeError) as e:
            sendlog.run(f"更新邀请历史失败: {e}")
        finally:
            conn.close()

    # 获取被邀请人员信息
    contact_wxid, invite_history = get_wxid_and_invite_history()

    if not contact_wxid:
        sendlog.run("指定联系人不存在。")
        return

    # 获取指定分类的群信息
    groups = get_group_info_by_class()

    if not groups:
        sendlog.run("没有找到符合条件的群。")
        return

    invites_sent = 0  # 统计已发送的邀请次数

    for group_wxid, group_name, MemberNum, wxidList in groups:
        if invites_sent >= max_invites:
            sendlog.run(f"已达到最大邀请次数 {max_invites}，停止邀请。")
            break

        if contact_wxid in wxidList:
            sendlog.run(f"联系人 {contact_wxid} 已在群 {group_name} 中，跳过。")
            continue

        if group_wxid in invite_history or MemberNum == 500:
            sendlog.run(f"群：{group_name} 已邀请过或群人数已满，跳过。")
            continue

        time.sleep(random.randint(5, 10))

        try:
            if wcf.invite_chatroom_members(group_wxid, contact_wxid) != 1:
                sendlog.run("邀请失败！！！")
                continue
        except Exception as e:
            sendlog.run(f"调用 wcf.invite_chatroom_members 时出错: {e}")
            continue

        update_invite_history(contact_wxid, group_wxid)
        sendlog.run(f"成功邀请 {group_name} ({group_wxid})。")
        invites_sent += 1  # 增加已邀请次数
