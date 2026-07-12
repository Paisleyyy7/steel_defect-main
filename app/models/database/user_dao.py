import hashlib
import time
import uuid
from typing import List, Optional, Tuple

from .base_db import BaseDB


class UserDAO(BaseDB):
    """用户数据访问对象"""

    def generate_token(self) -> str:
        """生成唯一的用户token"""
        return str(uuid.uuid4()).replace('-', '')

    def create_user(self, name: str, email: str = "", initial_balance: float = 0.0) -> Tuple[int, str]:
        """创建新用户，返回用户ID和token"""
        with self.lock:
            cursor = self.conn.cursor()
            token = self.generate_token()
            
            cursor.execute("""
                INSERT INTO users (token, name, email, balance)
                VALUES (?, ?, ?, ?)
            """, (token, name, email, initial_balance))
            
            user_id = cursor.lastrowid
            self.conn.commit()
            # Ensure user_id is an integer and not None
            if user_id is None:
                raise ValueError("Failed to create user, no ID returned")
            return user_id, token

    def get_user_by_token(self, token: str) -> Optional[dict]:
        """根据token获取用户信息"""
        with self.lock:
            cursor = self.conn.cursor()
            cursor.execute("""
                SELECT id, token, name, email, balance, created_at, updated_at
                FROM users WHERE token = ?
            """, (token,))
            
            row = cursor.fetchone()
            if row:
                return {
                    'id': row[0],
                    'token': row[1],
                    'name': row[2],
                    'email': row[3],
                    'balance': row[4],
                    'created_at': row[5],
                    'updated_at': row[6]
                }
            return None

    def get_all_users(self) -> List[dict]:
        """获取所有用户"""
        with self.lock:
            cursor = self.conn.cursor()
            cursor.execute("""
                SELECT id, token, name, email, balance, created_at, updated_at
                FROM users ORDER BY created_at DESC
            """)
            
            rows = cursor.fetchall()
            return [{
                'id': row[0],
                'token': row[1],
                'name': row[2],
                'email': row[3],
                'balance': row[4],
                'created_at': row[5],
                'updated_at': row[6]
            } for row in rows]

    def update_user_balance(self, user_id: int, new_balance: float) -> bool:
        """更新用户余额"""
        with self.lock:
            cursor = self.conn.cursor()
            cursor.execute("""
                UPDATE users SET balance = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (new_balance, user_id))
            
            self.conn.commit()
            return cursor.rowcount > 0

    def add_balance(self, user_id: int, amount: float, description: str = "充值") -> bool:
        """为用户充值"""
        with self.lock:
            cursor = self.conn.cursor()
            
            # 获取当前余额
            cursor.execute("SELECT balance FROM users WHERE id = ?", (user_id,))
            row = cursor.fetchone()
            if not row:
                return False
            
            balance_before = row[0]
            balance_after = balance_before + amount
            
            # 更新余额
            cursor.execute("""
                UPDATE users SET balance = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (balance_after, user_id))
            
            # 记录充值历史
            cursor.execute("""
                INSERT INTO recharge_records (user_id, amount, balance_before, balance_after, description)
                VALUES (?, ?, ?, ?, ?)
            """, (user_id, amount, balance_before, balance_after, description))
            
            self.conn.commit()
            return True

    def deduct_balance(self, user_id: int, amount: float) -> bool:
        """扣除用户余额"""
        with self.lock:
            cursor = self.conn.cursor()
            
            # 获取当前余额
            cursor.execute("SELECT balance FROM users WHERE id = ?", (user_id,))
            row = cursor.fetchone()
            if not row or row[0] < amount:
                return False
            
            new_balance = row[0] - amount
            cursor.execute("""
                UPDATE users SET balance = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (new_balance, user_id))
            
            self.conn.commit()
            return True

    def delete_user(self, user_id: int) -> bool:
        """删除用户"""
        with self.lock:
            cursor = self.conn.cursor()
            cursor.execute("DELETE FROM users WHERE id = ?", (user_id,))
            self.conn.commit()
            return cursor.rowcount > 0

    def update_user_info(self, user_id: int, name: str = "", email: str = "") -> bool:
        """更新用户信息"""
        with self.lock:
            cursor = self.conn.cursor()
            
            updates = []
            params = []
            
            if name is not None:
                updates.append("name = ?")
                params.append(name)
            if email is not None:
                updates.append("email = ?")
                params.append(email)
            
            if not updates:
                return False
            
            updates.append("updated_at = CURRENT_TIMESTAMP")
            params.append(user_id)
            
            query = f"UPDATE users SET {', '.join(updates)} WHERE id = ?"
            cursor.execute(query, params)
            
            self.conn.commit()
            return cursor.rowcount > 0

    def get_user_by_id(self, user_id: int) -> Optional[dict]:
        """根据ID获取用户信息"""
        with self.lock:
            cursor = self.conn.cursor()
            cursor.execute("""
                SELECT id, token, name, email, balance, created_at, updated_at
                FROM users WHERE id = ?
            """, (user_id,))
            
            row = cursor.fetchone()
            if row:
                return {
                    'id': row[0],
                    'token': row[1],
                    'name': row[2],
                    'email': row[3],
                    'balance': row[4],
                    'created_at': row[5],
                    'updated_at': row[6]
                }
            return None

    def check_balance(self, user_id: int, amount: float) -> bool:
        """检查用户余额是否足够"""
        with self.lock:
            cursor = self.conn.cursor()
            cursor.execute("SELECT balance FROM users WHERE id = ?", (user_id,))
            row = cursor.fetchone()
            return row and row[0] >= amount

    def update_user_token(self, user_id: int, new_token: str) -> bool:
        """更新用户token"""
        with self.lock:
            cursor = self.conn.cursor()
            cursor.execute("""
                UPDATE users SET token = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (new_token, user_id))
            
            self.conn.commit()
            return cursor.rowcount > 0

    def regenerate_user_token(self, user_id: int) -> str:
        """重新生成用户token并更新"""
        new_token = self.generate_token()
        if self.update_user_token(user_id, new_token):
            return new_token
        else:
            raise Exception("重新生成token失败")
