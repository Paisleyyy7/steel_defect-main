import numpy as np
from PyQt6.QtGui import QImage
from qfluentwidgets import FluentIcon

from app.models.camera_model import CameraModel
from app.views.camera_view import CameraView
from app.views.components.components import MessageBox
from app.views.components.confirm_dialog import ConfirmDialog
from ml.detector import InferenceResult


class CameraController:
    def __init__(self, view: CameraView, model: CameraModel):
        self.view: CameraView = view
        self.model: CameraModel = model
        
        # 绑定信号
        self._connect_signals()
        
        # 初始化数据
        self._init_data()
        
    def _connect_signals(self):
        """连接信号和槽"""
        # 摄像头控制信号
        self.view.start_camera_btn.clicked.connect(self._toggle_camera)
        self.view.capture_btn.clicked.connect(self._capture_image)
        self.view.retake_btn.clicked.connect(self._retake_image)
        self.view.inference_btn.clicked.connect(self._start_inference)
        
        # 模型信号
        self.model.camera_list_signal.connect(self.view.update_camera_list)
        self.model.model_list_signal.connect(self.view.update_model_list)
        self.model.camera_frame_signal.connect(self.view.update_camera_frame)
        self.model.camera_started_signal.connect(self._on_camera_started)
        self.model.camera_error_signal.connect(self._on_camera_error)
        
        # 图像捕获信号
        self.model.image_captured_signal.connect(self.view.show_captured_image)
        
        # 推理信号
        self.model.inference_started_signal.connect(self.view.start_inference_progress)
        self.model.inference_finished_signal.connect(self._on_inference_finished)
        self.model.inference_error_signal.connect(self._on_inference_error)
        
    def _init_data(self):
        """初始化数据"""
        # 获取摄像头列表和模型列表
        try:

            self.model.get_camera_list()
            self.model.get_model_list()
        except Exception as e:

            self.view.status_indicator.setText(f"● 初始化出错: {str(e)}")
    
    def _toggle_camera(self):
        """切换摄像头状态（开启/关闭）"""
        try:
            if self.view.start_camera_btn.text() == "启动摄像头":
                # 获取选中的摄像头索引
                camera_index = self.view.camera_select.currentIndex()
                if camera_index == -1:
                    self.view.status_indicator.setText("● 请先选择摄像头")
                    return
                
                self.view.start_camera_btn.setEnabled(False)
                self.view.camera_select.setEnabled(False)
                self.view.status_indicator.setText("● 正在启动摄像头...")
            
                self.model.start_camera(camera_index)
            else:
                self.view.start_camera_btn.setEnabled(False)
                self.view.capture_btn.setEnabled(False)
                self.view.status_indicator.setText("● 正在关闭摄像头...")
                self.model.stop_camera()
        except Exception as e:
            self.view.status_indicator.setText(f"● 摄像头控制出错: {str(e)}")
            self.view.start_camera_btn.setEnabled(True)
            self.view.camera_select.setEnabled(True)
    
    def _on_camera_started(self, success: bool):
        """摄像头启动成功处理"""
        if success:

            self.view.start_camera_btn.setText("关闭摄像头")
            self.view.start_camera_btn.setIcon(FluentIcon.STOP_WATCH)
            self.view.capture_btn.setEnabled(True)
            self.view.status_indicator.setText("● 摄像头已启动，可以拍摄")
        else:
            self.view.status_indicator.setText("● 摄像头已关闭")
            self.view.start_camera_btn.setText("启动摄像头")
            self.view.start_camera_btn.setIcon(FluentIcon.PLAY)
            self.view.reset_ui()
        
        # 恢复按钮状态
        self.view.start_camera_btn.setEnabled(True)
        self.view.camera_select.setEnabled(True)
    
    def _on_camera_error(self, error_message: str):
        """摄像头错误处理"""
        self.view.status_indicator.setText(f"● 摄像头错误: {error_message}")
        
        # 出错时重置UI
        self.view.start_camera_btn.setText("启动摄像头")
        self.view.start_camera_btn.setIcon(FluentIcon.PLAY)
        self.view.start_camera_btn.setEnabled(True)
        self.view.capture_btn.setEnabled(False)
    
    def _capture_image(self):
        """捕获图像"""
        self.model.capture_image()
        self.view.status_indicator.setText("● 已捕获图像，可以进行推理或重新拍摄")
    
    def _retake_image(self):
        """重新拍摄图像"""
        self.view.clear_captured_image()
        self.view.status_indicator.setText("● 已清除图像，请重新拍摄")
    
    def _start_inference(self):
        """开始推理"""
        model_name = self.view.model_select.currentText()
        if not model_name:
            self.view.status_indicator.setText("● 请先选择一个模型")
            return
        
        self.model.start_inference(model_name)
        self.view.status_indicator.setText("● 正在推理中...")
    
    def _on_inference_finished(self, image : np.ndarray, result : InferenceResult):
        # image 是一个 RGB 格式的 numpy 数组
        """推理完成处理"""
        self.view.stop_inference_progress()
        
        # 计算缺陷信息
        defects = []
        for defect_name, count in result.defect_ids.items():
            defects.append({
                'defect_name': defect_name,
                'count': count
            })

        # 将 result 中的 BGR 格式 numpy 数组转换为pyqt中的 QImage
        original_np = result.original_image
        annotated_np = result.annotated_image


        def numpy_bgr_to_qimage(numpy_array):
            """
            将 BGR 格式的 numpy 数组转换为 PyQt 的 QImage 对象。

            参数：
                numpy_array: BGR 格式的 numpy 数组。

            返回：
                PyQt 的 QImage 对象。
            """
            height, width, channel = numpy_array.shape
            bytes_per_line = 3 * width
            qimage = QImage(numpy_array.data, width, height, bytes_per_line, QImage.Format.Format_RGB888).rgbSwapped()
            return qimage

        # 显示推理结果对话框
        dialog = MessageBox(
            original_image=numpy_bgr_to_qimage(original_np),
            annotated_image=numpy_bgr_to_qimage(annotated_np),
            parent=self.view,
            defects=defects
        )



        # 显示对话框后，询问是否保存结果
        dialog.exec()
        self._show_save_confirmation()
    
    def _show_save_confirmation(self):
        """显示保存确认对话框"""
        dialog = ConfirmDialog(
            title="保存推理结果",
            content="是否将推理结果保存到数据库？",
            parent=self.view
        )
        
        if dialog.exec():
            success = self.model.save_inference_to_db()
            if success:
                self.view.status_indicator.setText("● 推理结果已保存到数据库")
            else:
                self.view.status_indicator.setText("● 保存失败")
    
    def _on_inference_error(self, error_message: str):
        """推理错误处理"""
        self.view.stop_inference_progress()
        self.view.status_indicator.setText(f"● 推理错误: {error_message}")
