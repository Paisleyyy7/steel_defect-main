from PyQt6.QtCore import QObject, pyqtSignal
from PyQt6.QtWidgets import QMessageBox

from app.models.database.user_dao import UserDAO
from app.models.database.billing_dao import BillingDAO


class BillingController(QObject):
    """计费管理控制器"""
    
    # 信号
    users_updated = pyqtSignal()
    pricing_updated = pyqtSignal()
    calls_updated = pyqtSignal()
    
    def __init__(self, view=None):
        super().__init__()
        self.user_dao = UserDAO()
        self.billing_dao = BillingDAO()
        self.view = view
        if self.view:
            self._connect_signals()
    
    def set_view(self, view):
        """设置视图"""
        self.view = view
        self._connect_signals()
    
    def get_view(self):
        """获取视图"""
        return self.view
    
    def _connect_signals(self):
        """连接信号和槽"""
        if self.view:
            # 连接控制器信号到视图槽
            self.users_updated.connect(self.view.refresh_users)
            self.pricing_updated.connect(self.view.refresh_pricing)
            self.calls_updated.connect(self.view.refresh_calls)
            
            # 连接视图信号到控制器槽
            self.view.user_create_requested.connect(self.handle_create_user)
            self.view.user_update_requested.connect(self.handle_update_user)
            self.view.user_delete_requested.connect(self.handle_delete_user)
            self.view.user_recharge_requested.connect(self.handle_recharge_user)
            self.view.pricing_update_requested.connect(self.handle_update_pricing)
    
    def handle_create_user(self, name, email, initial_balance):
        """处理创建用户请求"""
        try:
            if not name or name.strip() == "":
                if self.view:
                    self.view.show_error("用户名不能为空")
                return
            
            if initial_balance < 0:
                if self.view:
                    self.view.show_error("初始余额不能为负数")
                return
                
            user_id, token = self.create_user(name.strip(), email.strip(), initial_balance)
            if self.view:
                self.view.show_info("成功", f"用户创建成功！Token: {token}")
        except Exception as e:
            if self.view:
                self.view.show_error(f"创建用户失败: {str(e)}")
    
    def handle_update_user(self, user_id, name, email):
        """处理更新用户请求"""
        try:
            if not name or name.strip() == "":
                if self.view:
                    self.view.show_error("用户名不能为空")
                return
                
            success = self.update_user(user_id, name.strip(), email.strip())
            if success:
                if self.view:
                    self.view.show_info("成功", "用户信息更新成功")
            else:
                if self.view:
                    self.view.show_error("更新用户失败")
        except Exception as e:
            if self.view:
                self.view.show_error(f"更新用户失败: {str(e)}")
    
    def handle_delete_user(self, user_id):
        """处理删除用户请求"""
        try:
            success = self.delete_user(user_id)
            if success:
                if self.view:
                    self.view.show_info("成功", "用户删除成功")
            else:
                if self.view:
                    self.view.show_error("删除用户失败")
        except Exception as e:
            if self.view:
                self.view.show_error(f"删除用户失败: {str(e)}")
    
    def handle_recharge_user(self, user_id, amount, description):
        """处理用户充值请求"""
        try:
            if amount <= 0:
                if self.view:
                    self.view.show_error("充值金额必须大于0")
                return
                
            success = self.add_user_balance(user_id, amount, description)
            if success:
                if self.view:
                    self.view.show_info("成功", f"充值成功，金额: {amount}元")
            else:
                if self.view:
                    self.view.show_error("充值失败")
        except Exception as e:
            if self.view:
                self.view.show_error(f"充值失败: {str(e)}")
    
    def handle_update_pricing(self, model_name, price, description):
        """处理更新定价请求"""
        try:
            if not model_name or model_name.strip() == "":
                if self.view:
                    self.view.show_error("模型名称不能为空")
                return
                
            if price < 0:
                if self.view:
                    self.view.show_error("价格不能为负数")
                return
                
            success = self.update_model_price(model_name.strip(), price, description)
            if success:
                if self.view:
                    self.view.show_info("成功", "模型定价更新成功")
            else:
                if self.view:
                    self.view.show_error("更新模型定价失败")
        except Exception as e:
            if self.view:
                self.view.show_error(f"更新模型定价失败: {str(e)}")

    def get_all_users(self):
        """获取所有用户"""
        return self.user_dao.get_all_users()
    
    def create_user(self, name, email="", initial_balance=0.0):
        """创建用户"""
        user_id, token = self.user_dao.create_user(name, email, initial_balance)
        self.users_updated.emit()
        return user_id, token
    
    def update_user(self, user_id, name="", email=""):
        """更新用户信息"""
        success = self.user_dao.update_user_info(user_id, name, email)
        if success:
            self.users_updated.emit()
        return success
    
    def add_user_balance(self, user_id, amount, description="充值"):
        """用户充值"""
        success = self.user_dao.add_balance(user_id, amount, description)
        if success:
            self.users_updated.emit()
        return success
    
    def delete_user(self, user_id):
        """删除用户"""
        success = self.user_dao.delete_user(user_id)
        if success:
            self.users_updated.emit()
        return success
    
    def get_model_pricing(self):
        """获取模型定价"""
        return self.billing_dao.get_all_model_pricing()
    
    def update_model_price(self, model_name, price, description=""):
        """更新模型价格"""
        success = self.billing_dao.update_model_price(model_name, price, description)
        if success:
            self.pricing_updated.emit()
        return success
    
    def add_model_pricing(self, model_name, price, description=""):
        """添加模型定价"""
        success = self.billing_dao.add_model_pricing(model_name, price, description)
        if success:
            self.pricing_updated.emit()
        return success
    
    def get_api_calls(self, page=1, page_size=10):
        """获取API调用记录"""
        return self.billing_dao.get_all_api_calls(page, page_size)
    
    def get_user_api_calls(self, user_id, page=1, page_size=10):
        """获取用户API调用记录"""
        return self.billing_dao.get_user_api_calls(user_id, page, page_size)
    
    def get_billing_summary(self, user_id):
        """获取用户账单摘要"""
        return self.billing_dao.get_user_billing_summary(user_id)
    
    def get_recharge_records(self, user_id):
        """获取充值记录"""
        return self.billing_dao.get_recharge_records(user_id)
    
    def initialize_system_models(self, system_models):
        """初始化系统模型定价"""
        try:
            # 默认价格设置
            default_prices = {
                '目标定位': 0.1000,
                '精细分析': 0.2000,
                '快速分类': 0.0500,
                '复杂分类': 0.1500
            }
            
            for model_name, description in system_models.items():
                # 检查模型是否已存在
                if not self.billing_dao.get_model_price(model_name):
                    # 模型不存在，添加默认定价
                    price = default_prices.get(model_name, 0.1000)
                    self.billing_dao.add_model_pricing(model_name, price, description)
            
            self.pricing_updated.emit()
            return True
        except Exception as e:
            print(f"[ERROR] 初始化系统模型失败: {e}")
            return False
