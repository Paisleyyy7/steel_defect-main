from PyQt6.QtCore import QObject, pyqtSignal, QThreadPool
from typing import List, Dict, Optional

from app.models.database.user_dao import UserDAO
from app.models.database.billing_dao import BillingDAO
from app.models.utils import Worker


class BillingModel(QObject):
    """计费管理模型"""
    
    # 数据更新信号
    users_updated = pyqtSignal(list)  # 用户列表更新
    pricing_updated = pyqtSignal(list)  # 模型定价更新
    api_calls_updated = pyqtSignal(list)  # API调用记录更新
    statistics_updated = pyqtSignal(dict)  # 统计数据更新
    
    # 操作结果信号
    operation_success = pyqtSignal(str)  # 操作成功信号
    operation_error = pyqtSignal(str)    # 操作失败信号
    
    def __init__(self):
        super().__init__()
        self.user_dao = UserDAO()
        self.billing_dao = BillingDAO()
        self.thread_pool = QThreadPool()
        self.thread_pool.setMaxThreadCount(3)
    
    def load_all_users(self):
        """加载所有用户"""
        worker = Worker(self._load_users_task)
        worker.signals.result.connect(self.users_updated.emit)
        worker.signals.error.connect(lambda e: self.operation_error.emit(f"加载用户失败: {str(e)}"))
        self.thread_pool.start(worker)
    
    def _load_users_task(self, signals):
        """加载用户的后台任务"""
        users = self.user_dao.get_all_users()
        return users
    
    def load_model_pricing(self, page: int = 1, page_size: int = 50):
        """加载模型定价"""
        worker = Worker(self._load_pricing_task, page, page_size)
        worker.signals.result.connect(self.pricing_updated.emit)
        worker.signals.error.connect(lambda e: self.operation_error.emit(f"加载定价失败: {str(e)}"))
        self.thread_pool.start(worker)
    
    def _load_pricing_task(self, page, page_size, signals):
        """加载定价的后台任务"""
        pricing = self.billing_dao.get_all_model_pricing(page, page_size)
        return pricing
    
    def load_api_calls(self, page: int = 1, page_size: int = 50):
        """加载API调用记录"""
        worker = Worker(self._load_api_calls_task, page, page_size)
        worker.signals.result.connect(self.api_calls_updated.emit)
        worker.signals.error.connect(lambda e: self.operation_error.emit(f"加载调用记录失败: {str(e)}"))
        self.thread_pool.start(worker)
    
    def _load_api_calls_task(self, page, page_size, signals):
        """加载API调用记录的后台任务"""
        calls = self.billing_dao.get_all_api_calls(page, page_size)
        return calls
    
    def load_statistics(self):
        """加载统计数据"""
        worker = Worker(self._load_statistics_task)
        worker.signals.result.connect(self.statistics_updated.emit)
        worker.signals.error.connect(lambda e: self.operation_error.emit(f"加载统计数据失败: {str(e)}"))
        self.thread_pool.start(worker)
    
    def _load_statistics_task(self, signals):
        """加载统计数据的后台任务"""
        stats = self.billing_dao.get_statistics_summary()
        return stats
    
    def create_user(self, name: str, email: str = "", initial_balance: float = 0.0):
        """创建用户"""
        worker = Worker(self._create_user_task, name, email, initial_balance)
        worker.signals.result.connect(lambda result: self.operation_success.emit("用户创建成功"))
        worker.signals.result.connect(lambda result: self.load_all_users())  # 重新加载用户列表
        worker.signals.error.connect(lambda e: self.operation_error.emit(f"创建用户失败: {str(e)}"))
        self.thread_pool.start(worker)
    
    def _create_user_task(self, name, email, initial_balance, signals):
        """创建用户的后台任务"""
        user_id, token = self.user_dao.create_user(name, email, initial_balance)
        return {'user_id': user_id, 'token': token}
    
    def update_user(self, user_id: int, name: str, email: str):
        """更新用户信息"""
        worker = Worker(self._update_user_task, user_id, name, email)
        worker.signals.result.connect(lambda result: self.operation_success.emit("用户信息更新成功"))
        worker.signals.result.connect(lambda result: self.load_all_users())
        worker.signals.error.connect(lambda e: self.operation_error.emit(f"更新用户失败: {str(e)}"))
        self.thread_pool.start(worker)
    
    def _update_user_task(self, user_id, name, email, signals):
        """更新用户信息的后台任务"""
        success = self.user_dao.update_user_info(user_id, name, email)
        if not success:
            raise Exception("更新失败，用户不存在")
        return True
    
    def delete_user(self, user_id: int):
        """删除用户"""
        worker = Worker(self._delete_user_task, user_id)
        worker.signals.result.connect(lambda result: self.operation_success.emit("用户删除成功"))
        worker.signals.result.connect(lambda result: self.load_all_users())
        worker.signals.error.connect(lambda e: self.operation_error.emit(f"删除用户失败: {str(e)}"))
        self.thread_pool.start(worker)
    
    def _delete_user_task(self, user_id, signals):
        """删除用户的后台任务"""
        success = self.user_dao.delete_user(user_id)
        if not success:
            raise Exception("删除失败，用户不存在")
        return True
    
    def recharge_user(self, user_id: int, amount: float, description: str = "充值"):
        """用户充值"""
        worker = Worker(self._recharge_user_task, user_id, amount, description)
        worker.signals.result.connect(lambda result: self.operation_success.emit(f"充值成功，金额: {amount} 元"))
        worker.signals.result.connect(lambda result: self.load_all_users())
        worker.signals.error.connect(lambda e: self.operation_error.emit(f"充值失败: {str(e)}"))
        self.thread_pool.start(worker)
    
    def _recharge_user_task(self, user_id, amount, description, signals):
        """用户充值的后台任务"""
        success = self.user_dao.add_balance(user_id, amount, description)
        if not success:
            raise Exception("充值失败，用户不存在")
        return True
    
    def add_model_pricing(self, model_name: str, price: float, description: str = ""):
        """添加模型定价"""
        worker = Worker(self._add_model_pricing_task, model_name, price, description)
        worker.signals.result.connect(lambda result: self.operation_success.emit("模型定价添加成功"))
        worker.signals.result.connect(lambda result: self.load_model_pricing())
        worker.signals.error.connect(lambda e: self.operation_error.emit(f"添加模型定价失败: {str(e)}"))
        self.thread_pool.start(worker)
    
    def _add_model_pricing_task(self, model_name, price, description, signals):
        """添加模型定价的后台任务"""
        success = self.billing_dao.add_model_pricing(model_name, price, description)
        if not success:
            raise Exception("添加失败，模型可能已存在")
        return True
    
    def update_model_pricing(self, model_name: str, price: float, description: str = ""):
        """更新模型定价"""
        worker = Worker(self._update_model_pricing_task, model_name, price, description)
        worker.signals.result.connect(lambda result: self.operation_success.emit("模型定价更新成功"))
        worker.signals.result.connect(lambda result: self.load_model_pricing(page=1, page_size=50))
        worker.signals.error.connect(lambda e: self.operation_error.emit(f"更新模型定价失败: {str(e)}"))
        self.thread_pool.start(worker)
    
    def _update_model_pricing_task(self, model_name, price, description, signals):
        """更新模型定价的后台任务"""
        # 先尝试更新，如果失败则添加
        success = self.billing_dao.update_model_price(model_name, price, description)
        if not success:
            # 如果更新失败，可能是模型不存在，尝试添加
            success = self.billing_dao.add_model_pricing(model_name, price, description)
            if not success:
                raise Exception("更新或添加模型定价失败")
        return True
    
    def delete_model_pricing(self, model_name: str):
        """删除模型定价"""
        worker = Worker(self._delete_model_pricing_task, model_name)
        worker.signals.result.connect(lambda result: self.operation_success.emit("模型定价删除成功"))
        worker.signals.result.connect(lambda result: self.load_model_pricing(page=1, page_size=50))
        worker.signals.error.connect(lambda e: self.operation_error.emit(f"删除模型定价失败: {str(e)}"))
        self.thread_pool.start(worker)
    
    def _delete_model_pricing_task(self, model_name, signals):
        """删除模型定价的后台任务"""
        success = self.billing_dao.delete_model_pricing(model_name)
        if not success:
            raise Exception("删除失败，模型不存在")
        return True
    
    def initialize_system_models(self, system_models: dict):
        """初始化系统模型定价（如果不存在）"""
        worker = Worker(self._initialize_system_models_task, system_models)
        worker.signals.result.connect(lambda result: self.operation_success.emit("系统模型初始化完成"))
        worker.signals.result.connect(lambda result: self.load_model_pricing(page=1, page_size=50))
        worker.signals.error.connect(lambda e: self.operation_error.emit(f"系统模型初始化失败: {str(e)}"))
        self.thread_pool.start(worker)
    
    def _initialize_system_models_task(self, system_models, signals):
        """初始化系统模型的后台任务"""
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
        
        return True

    def regenerate_user_token(self, user_id: int):
        """重新生成用户token"""
        worker = Worker(self._regenerate_user_token_task, user_id)
        worker.signals.result.connect(lambda result: self.operation_success.emit("用户Token重新生成成功"))
        worker.signals.result.connect(lambda result: self.load_all_users())
        worker.signals.error.connect(lambda e: self.operation_error.emit(f"重新生成Token失败: {str(e)}"))
        self.thread_pool.start(worker)
    
    def _regenerate_user_token_task(self, user_id, signals):
        """重新生成用户token的后台任务"""
        new_token = self.user_dao.generate_token()
        success = self.user_dao.update_user_token(user_id, new_token)
        if not success:
            raise Exception("更新用户Token失败")
        return new_token
