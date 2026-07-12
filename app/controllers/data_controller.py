from PyQt6.QtGui import QImage
from PyQt6.QtWidgets import QMessageBox

from app.models.data_model import DataModel
from app.views.components.components import MessageBox
from app.views.data_view import DataView


class DataController:

    def __init__(self, view : DataView , model : DataModel):
        self.model = model
        self.view = view
        self.view.check_data_signal.connect(self.display_data)
        self.model.loaded_data_signal.connect(self.view.init_data)
        self.model.load_data()
        self.view.page_changed_signal.connect(self.handle_page_change)
        self.view.page_size_changed_signal.connect(self.handle_page_size_change)
        self.view.filter_button.clicked.connect(self.handle_time_filter)

    # 弹窗展示数据
    def display_data(self, id):
        # 从数据库获取数据
        data = self.model.get_inference_result_by_id(id)
        if data:
            original_image = QImage.fromData(data['inference_result']['original_image'], "JPEG")
            annotated_image = QImage.fromData(data['inference_result']['annotated_image'], "JPEG")

            if not original_image and not annotated_image:
                QMessageBox.warning(self.view, "警告", "无图片数据可显示。")
                return
            dialog = MessageBox(original_image, annotated_image, self.view, data['defects'])
            dialog.exec()
        else:
            QMessageBox.critical(self.view, "错误", "未找到相关数据。")

        

    def handle_page_change(self, page):
        """
        处理页码变化
        """
        self.model.load_data(page)

    def handle_page_size_change(self, page_size):
        """
        处理每页显示数量变化
        """
        self.model.page_size = page_size
        self.model.load_data(1)  # 切换到第一页

    def handle_time_filter(self):
        """处理时间筛选"""
        from_time = self.view.from_time
        to_time = self.view.to_time
        
        if not from_time or not to_time:
            QMessageBox.warning(self.view, "警告", "请选择完整的时间范围")
            return
            
        if from_time > to_time:
            QMessageBox.warning(self.view, "警告", "开始时间不能大于结束时间")
            return
            
        self.model.set_time_filter(from_time, to_time)




