import sqlite3
from wcferry import sendlog

db_path = "data/data.db"  # 数据库路径

def categorize_contact(contact, qcys, ContactLabel, Contact_ids, sql_biao):
    """根据联系人的信息将其分类。"""
    if 'wxid' not in contact:
        return None, None, None, None, None, None, []

    wxid = contact['wxid']
    remark = contact.get('remark', '')  # 获取备注，默认为空
    name = contact.get('name', '')  # 获取联系人名称
    excluded_friends = ['fmessage', 'filehelper', 'floatbottle', 'medianote', 'newsapp', 'mphelper', '@openim', 'gh_', 'qmessage']

    if 'chatroom' in wxid:
        # 判断群聊分类
        category = '旅游' if '旅游' in remark else '工商' if '工商' in remark else '未分'
        # 查找群成员
        chatroom_members = qcys.get(wxid, [])
        wxidlist = "^".join(chatroom_members)
        member_count = len(chatroom_members)
        if sql_biao not in wxidlist:
            category = '已删'
        return wxid, remark, name, category, member_count, wxidlist, []

    elif not any(excluded_friend in wxid for excluded_friend in excluded_friends):
        # 判断好友分类
        user_labels = Contact_ids.get(wxid, {}).get('LabelIDList', '').split(',')  # wxid 的值是标签id
        del_flag = Contact_ids.get(wxid, {}).get('DelFlag', 0) # 联系人是否已删除

        if del_flag != 0:
            return None, None, None, None, None, None, []
        label_names = [ContactLabel.get(label_id.strip(), '') for label_id in user_labels if label_id.strip()]
        category = '好友'

        return wxid, remark, name, category, 0, '', label_names

    return None, None, None, None, None, None, []

def ensure_columns_exist(cursor, sql_biao):
    """确保表中包含所需的列。"""
    required_columns = {
        "wxid": "TEXT NOT NULL UNIQUE",
        "name": "TEXT NOT NULL",
        "remark": "TEXT",
        "ContactLabel": "TEXT",
        "class": "TEXT NOT NULL",
        "nUnReadCount": "INTEGER NOT NULL DEFAULT 0",
        "nTime": "INTEGER NOT NULL DEFAULT 0",
        "invite_history": "TEXT",
        "MemberNum": "INTEGER",
        "wxidList": "TEXT"
    }

    # 获取表的现有列信息
    cursor.execute(f"PRAGMA table_info({sql_biao})")
    existing_columns = {row[1]: row[2] for row in cursor.fetchall()}

    # 添加缺失的列
    for column, column_type in required_columns.items():
        if column not in existing_columns:
            try:
                cursor.execute(f"ALTER TABLE {sql_biao} ADD COLUMN {column} {column_type}")
            except sqlite3.Error as e:
                sendlog.run(f"列创建错误: {e}")
                raise

def categorize_and_update_contacts(contacts, cursor, qcys, ContactLabel, Contact_ids, sql_biao):
    """批量更新或插入联系人信息。"""
    for contact in contacts:
        wxid, remark, name, category, member_count, wxidlist, label_names = categorize_contact(contact, qcys, ContactLabel, Contact_ids, sql_biao)
        if wxid is None:
            continue

        # 将标签名称列表转换为逗号分隔的字符串
        label_names_str = ','.join(label_names)

        try:
            # 检查联系人是否已存在
            cursor.execute(f"SELECT 1 FROM {sql_biao} WHERE wxid = ?", (wxid,))
            exists = cursor.fetchone() is not None

            # 更新或插入联系人信息
            if exists:
                cursor.execute(f"""
                    UPDATE {sql_biao}
                    SET name = ?, remark = ?, class = ?, ContactLabel = ?, MemberNum = ?, wxidList = ?
                    WHERE wxid = ?
                """, (name, remark, category, label_names_str, member_count, wxidlist, wxid))
            else:
                cursor.execute(f"""
                    INSERT INTO {sql_biao} (wxid, name, remark, class, ContactLabel, nUnReadCount, nTime, MemberNum, wxidList)
                    VALUES (?, ?, ?, ?, ?, 0, 0, ?, ?)
                """, (wxid, name, remark, category, label_names_str, member_count, wxidlist))
        except sqlite3.Error as e:
            sendlog.run(f"数据库操作错误: {e}")
            raise
        except Exception as e:
            sendlog.run(f"其他错误: {e}")
            raise

def up(wcf, sql_biao, current_name):
    """获取联系人列表并分类，返回字典，键为分类名，值为分类内联系人的列表。"""
    categorized_contacts = {'未分': [], '旅游': [], '工商': [], '好友': [], '已删': []}

    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # 创建表（如果不存在）
        cursor.execute(f"""
            CREATE TABLE IF NOT EXISTS {sql_biao} (
                "wxid" TEXT NOT NULL UNIQUE,
                "name" TEXT NOT NULL,
                "remark" TEXT,
                "ContactLabel" TEXT,
                "class" TEXT NOT NULL,
                "nUnReadCount" INTEGER NOT NULL DEFAULT 0,
                "nTime" INTEGER NOT NULL DEFAULT 0,
                "invite_history" TEXT,
                "MemberNum" INTEGER,
                "wxidList" TEXT,
                PRIMARY KEY("wxid")
            )
        """)

        # 确保列存在
        ensure_columns_exist(cursor, sql_biao)

        # 获取联系人和相关信息
        wcf.get_contacts()
        contacts = wcf.contacts
        qcys = {item['ChatRoomName']: item['UserNameList'].split('^') for item in wcf.query_sql("MicroMsg.db", "SELECT ChatRoomName, UserNameList FROM ChatRoom")} # 群聊名称和成员列表的对应关系
        ContactLabel = {str(item['LabelId']): item['LabelName'] for item in wcf.query_sql("MicroMsg.db", "SELECT LabelId, LabelName FROM ContactLabel")} # 联系人id和标签的对应关系
        Contact_ids = {item['UserName']: {'LabelIDList': item['LabelIDList'], 'DelFlag': item['DelFlag']} for item in wcf.query_sql("MicroMsg.db", "SELECT UserName, LabelIDList,DelFlag FROM Contact")} # 标签id 和删除标志

        # 获取已存在的联系人 wxid
        cursor.execute(f"SELECT wxid FROM {sql_biao}")
        existing_wxids = {row[0] for row in cursor.fetchall()}

        # 更新或插入联系人信息
        categorize_and_update_contacts(contacts, cursor, qcys, ContactLabel, Contact_ids, sql_biao)
        conn.commit()

        # 删除本地数据库中没有在微信中出现的联系人
        current_wxids = {contact['wxid'] for contact in contacts}
        for wxid in existing_wxids - current_wxids:
            cursor.execute(f"SELECT name FROM {sql_biao} WHERE wxid = ?", (wxid,))
            name = cursor.fetchone()[0]
            sendlog.run(f"删除 {wxid}, {name}")
            cursor.execute(f"DELETE FROM {sql_biao} WHERE wxid = ?", (wxid,))
        conn.commit()

        # 查询分类联系人并整理
        cursor.execute(f"SELECT wxid, name, class FROM {sql_biao}")
        rows = cursor.fetchall()

        for wxid, name, category in rows:
            categorized_contacts[category].append(f"{wxid},{name}\n")

        # 关闭数据库连接
        conn.close()
        sendlog.run(f"{current_name}: 数据库已更新")
        return categorized_contacts

    except sqlite3.Error as e:
        sendlog.run(f"数据库连接错误: {e}")
        conn.rollback()
        conn.close()
    except Exception as e:
        sendlog.run(f"其他错误: {e}")
        conn.rollback()
        conn.close()
    return categorized_contacts

