# 总线模块（event_bus.py）
from PyQt6.QtCore import QObject, pyqtSignal


class _EventBus(QObject):
    """
    全局事件总线，用于整个应用程序的事件传递。
    使用单例模式实现全局事件总线。
    """
    # 单例实例
    _instance = None
    
    # 将信号定义为类变量而非实例变量
    # 数据变更通知信号
    inference_data_saved = pyqtSignal()  # 推理数据保存成功信号
    dashboard_data_updated = pyqtSignal() # 仪表盘数据更新信号
    
    # 全局消息通知信号
    message_notification = pyqtSignal(str, str)  # 消息通知信号，参数是标题和内容
    
    # 摄像头操作信号
    camera_capture_triggered = pyqtSignal()  # 摄像头拍摄触发信号
    camera_inference_finished = pyqtSignal(object)  # 摄像头推理完成信号，携带推理结果对象

    def __init__(self):
        """
        私有构造函数，防止外部直接实例化
        """
        if _EventBus._instance is not None:
            raise Exception("单例类不能重复实例化")
        super().__init__()
        _EventBus._instance = self
        
    @classmethod
    def get_instance(cls) -> '_EventBus':
        """
        获取 EventBus 单例
        """
        if cls._instance is None:
            cls._instance = _EventBus()
        return cls._instance


EventBus = _EventBus