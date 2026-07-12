from PyQt6.QtCore import Qt
from qfluentwidgets import FluentWindow, FluentIcon, InfoBar, InfoBarPosition

from app.controllers.camera_controller import CameraController
from app.controllers.dashboard_controller import DashboardController
from app.controllers.data_controller import DataController
from app.controllers.inference_controller import InferenceController
from app.controllers.realtime_inference_controller import RealtimeInferenceController
from app.controllers.billing_controller import BillingController
from app.models.camera_model import CameraModel
from app.models.dashboard_model import DashboardModel
from app.models.data_model import DataModel
from app.models.event_bus import EventBus
from app.models.inference_model import InferenceModel
from app.models.realtime_inference_model import RealtimeInferenceModel
from app.views.camera_view import CameraView
from app.views.dashboard_view import DashboardView
from app.views.data_view import DataView
from app.views.inference_view import InferenceView
from app.views.realtime_inference_view import RealtimeInferenceView
from app.views.billing_view import BillingView


class MainWindow(FluentWindow):
    def __init__(self):
        super().__init__()
        self.navigationInterface.setExpandWidth(150)        # 创建 view 层
        self.dashboard_view = DashboardView()
        self.inference_view = InferenceView()
        self.data_view = DataView()
        self.camera_view = CameraView()
        self.realtime_inference_view = RealtimeInferenceView()
        self.billing_view = BillingView()

        # 创建 model 层
        self.dashboard_model = DashboardModel()
        self.inference_model = InferenceModel()
        self.data_model = DataModel()
        self.camera_model = CameraModel()  
        self.realtime_inference_model = RealtimeInferenceModel(self.camera_model)
        
        # 创建 controller 层
        self.dashboard_controller = DashboardController(self.dashboard_view, self.dashboard_model)
        self.inference_controller = InferenceController(self.inference_view, self.inference_model)
        self.data_controller = DataController(self.data_view, self.data_model)
        self.camera_controller = CameraController(self.camera_view, self.camera_model)
        self.billing_controller = BillingController(self.billing_view)  # 将视图传给控制器
        self.realtime_inference_controller = RealtimeInferenceController(
            self.realtime_inference_view, 
            self.camera_model, 
            self.realtime_inference_model
        )
        
        self.init_navigation()
        self.init_window()
        self.setMicaEffectEnabled(True)
        self.init_global_event()

    def init_global_event(self):
        EventBus.get_instance().message_notification.connect(self.info)    
    def init_navigation(self):
        self.addSubInterface(self.dashboard_view, FluentIcon.HOME, "仪表盘")
        self.addSubInterface(self.inference_view, FluentIcon.IMAGE_EXPORT, "图片上传")
        self.addSubInterface(self.camera_view, FluentIcon.CAMERA, "摄像头拍摄")
        self.addSubInterface(self.realtime_inference_view, FluentIcon.IOT, "实时推理")
        self.addSubInterface(self.data_view, FluentIcon.BOOK_SHELF, "数据查看")
        self.addSubInterface(self.billing_view, FluentIcon.CERTIFICATE, "计费管理")


    def init_window(self):
        self.setWindowTitle("缺陷检测系统")
        self.resize(1280, 720)


    def info(self, title: str, content: str):
        # 弹出提示窗
        InfoBar.success(
            title=title,
            content=content,
            orient=Qt.Orientation.Horizontal,
            isClosable=True,
            position=InfoBarPosition.TOP,
            duration=2000,
            parent=self
        )
