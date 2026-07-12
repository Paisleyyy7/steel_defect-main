from PyQt6.QtWidgets import QFileDialog, QMessageBox
from app.models.inference_model import InferenceModel
from app.views.inference_view import InferenceView


class InferenceController:
    """
    推理控制器
    
    负责连接推理视图和推理模型，处理用户交互并调用相应的模型方法
    
    主要职责:
    1. 初始化视图和模型之间的信号连接
    2. 处理用户操作事件
    3. 验证用户输入的有效性
    4. 管理视图和模型之间的数据流
    """
    
    def __init__(self, view: InferenceView, model: InferenceModel):
        """
        初始化推理控制器
        
        Args:
            view: 推理视图对象
            model: 推理模型对象
        """
        self.view = view
        self.model = model
        
        # 连接模型信号到视图
        self.model.update_inference_progress.connect(self.view.update_progress)
        self.model.start_inference_signal.connect(self.view.start_progress)
        self.model.finished_inference_signal.connect(self.view.stop_progress)
        self.model.init_data_signal.connect(self.view.init_data)
        self.model.step_inference_signal.connect(self.view.show_inference_images)
        self.model.error_signal.connect(self.show_error_message)
        
        # 连接视图事件到控制器方法
        self.view.add_image_btn.clicked.connect(self.select_image)
        
        # 初始化数据
        self.model.init_data()


    def show_error_message(self, message: str):
        """
        显示错误消息对话框
        
        Args:
            message: 错误消息文本
        """
        QMessageBox.critical(self.view, "错误", message)


    def select_image(self):
        """处理用户选择图片的操作"""
        try:
            # 检查是否已选择模型
            model_name = self.view.select_model_checkbox.currentText()
            if not model_name:
                self.show_error_message("请先选择一个模型")
                return
            
            # 创建文件对话框
            file_dialog = QFileDialog(self.view)
            file_dialog.setFileMode(QFileDialog.FileMode.ExistingFiles)
            file_dialog.setNameFilter("Images (*.png *.jpg *.bmp)")
            
            # 如果用户选择了文件
            if file_dialog.exec():
                selected_files = file_dialog.selectedFiles()
                if selected_files:

                    # 调用model层的推理方法
                    self.model.start_select_image_2_inference(selected_files, model_name)
        except Exception as e:
            self.show_error_message(f"选择图片时出错: {str(e)}")
