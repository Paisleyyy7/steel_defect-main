import traceback
import cv2
from PyQt6.QtWidgets import QMessageBox

from app.models.camera_model import CameraModel
from app.models.realtime_inference_model import RealtimeInferenceModel
from app.views.realtime_inference_view import RealtimeInferenceView
from app.views.components.confirm_dialog import ConfirmDialog


class RealtimeInferenceController:
    """实时推理控制器，连接实时推理视图和模型"""

    def __init__(self, view: RealtimeInferenceView, camera_model: CameraModel, inference_model: RealtimeInferenceModel):
        self.view = view
        self.camera_model = camera_model
        self.inference_model = inference_model
        
        # 初始化状态
        self.is_camera_running = False
        self.is_inference_running = False
        
        # 连接视图信号到控制器方法
        self._connect_view_signals()
        
        # 连接模型信号到视图方法
        self._connect_model_signals()
        
        # 初始化数据
        self._init_data()
        
    def _init_data(self):
        """初始化数据"""
        try:
            # 获取摄像头列表
            self.camera_model.get_camera_list()
            
            # 获取模型列表
            self.camera_model.get_model_list()
            
            # 初始禁用推理按钮，等摄像头开启后再启用
            self.view.enable_inference_controls(False)
        except Exception as e:
            error_msg = f"初始化数据时出错: {str(e)}"
            print(error_msg)
            traceback.print_exc()
            self.view.show_error("初始化错误", error_msg)
            
    def _connect_view_signals(self):
        """连接视图信号到控制器方法"""
        # 摄像头控制信号
        self.view.camera_selected_signal.connect(self._on_camera_selected)
        self.view.toggle_camera_signal.connect(self._toggle_camera)
        
        # 推理控制信号
        self.view.start_inference_signal.connect(self._toggle_inference)
        self.view.inference_interval_changed_signal.connect(self._on_inference_interval_changed)
        
    def _connect_model_signals(self):
        """连接模型信号到视图和控制器方法"""
        # 摄像头模型信号
        self.camera_model.camera_list_signal.connect(self.view.update_camera_list)
        self.camera_model.model_list_signal.connect(self.view.update_model_list)
        self.camera_model.camera_frame_signal.connect(self.view.update_camera_frame)
        self.camera_model.camera_started_signal.connect(self._on_camera_started)
        self.camera_model.camera_error_signal.connect(self._on_camera_error)
        
        # 推理模型信号
        self.inference_model.inference_result_signal.connect(self._on_inference_result)
        self.inference_model.statistics_updated_signal.connect(self.view.update_statistics)
        self.inference_model.inference_error_signal.connect(self._on_inference_error)
        
    def _on_camera_selected(self, index: int):
        """摄像头选择处理"""
        # 当选择摄像头时不需要特别处理，等用户点击启动按钮时再处理
        pass
        
    def _toggle_camera(self):
        """切换摄像头状态（开启/关闭）"""
        try:
            if not self.is_camera_running:
                # 获取选中的摄像头ID (使用currentData而不是currentIndex)
                camera_id = self.view.camera_select.currentData()
                if camera_id is None:
                    self.view.show_error("摄像头错误", "请先选择摄像头")
                    return
                    
                # 启动摄像头
                self.camera_model.start_camera(camera_id)
            else:
                # 如果推理正在运行，先停止推理
                if self.is_inference_running:
                    self._stop_inference()
                    
                # 停止摄像头
                self.camera_model.stop_camera()
        except Exception as e:
            error_msg = f"摄像头控制时出错: {str(e)}"
            print(error_msg)
            traceback.print_exc()
            self.view.show_error("摄像头错误", error_msg)
            
    def _on_camera_started(self, success: bool):
        """摄像头启动状态处理"""
        self.is_camera_running = success
        self.view.set_camera_state(success)
        
        # 如果摄像头已启动，启用推理控制
        if success:
            self.view.enable_inference_controls(True)
        else:
            # 摄像头停止，确保推理也停止
            if self.is_inference_running:
                self.inference_model.stop_inference()
                self.is_inference_running = False
                self.view.set_inference_state(False)
            
    def _on_camera_error(self, error_message: str):
        """摄像头错误处理"""
        self.view.show_error("摄像头错误", error_message)
        
    def _toggle_inference(self, start: bool):
        """切换推理状态"""
        if start:
            self._start_inference()
        else:
            self._stop_inference()
            
    def _start_inference(self):
        """开始推理"""
        if not self.is_camera_running:
            self.view.show_error("推理错误", "请先启动摄像头")
            return
            
        try:
            # 获取当前选择的模型和推理间隔
            model_name = self.view.get_current_model()
            inference_interval = self.view.get_inference_interval()
            
            # 开始推理
            success = self.inference_model.start_inference(model_name, inference_interval)
            
            if success:
                self.is_inference_running = True
                self.view.set_inference_state(True)
                self.view.show_notification("推理开始", f"已开始实时推理，间隔 {inference_interval} 秒")
        except Exception as e:
            error_msg = f"开始推理时出错: {str(e)}"
            print(error_msg)
            traceback.print_exc()
            self.view.show_error("推理错误", error_msg)
            
    def _stop_inference(self):
        """停止推理"""
        if not self.is_inference_running:
            return
            
        try:
            # 停止推理
            success = self.inference_model.stop_inference()
            
            if success:
                self.is_inference_running = False
                self.view.set_inference_state(False)
                
                # 显示统计结果并询问是否保存到数据库
                self._show_inference_summary()
        except Exception as e:
            error_msg = f"停止推理时出错: {str(e)}"
            print(error_msg)
            traceback.print_exc()
            self.view.show_error("推理错误", error_msg)
            
    def _show_inference_summary(self):
        """显示推理统计结果并询问是否保存"""
        total_frames = self.inference_model.total_frames
        defect_frames = self.inference_model.defect_frames
        defect_count = self.inference_model.defect_count
        
        defect_ratio = 0
        if total_frames > 0:
            defect_ratio = (defect_frames / total_frames) * 100
            
        # 创建确认对话框
        dialog = ConfirmDialog(
            title="推理会话结束",
            content=f"推理统计信息：\n"
                   f"- 总帧数：{total_frames}\n"
                   f"- 缺陷帧数：{defect_frames}\n"
                   f"- 缺陷比例：{defect_ratio:.2f}%\n"
                   f"- 缺陷总数：{defect_count}\n\n"
                   f"是否将推理结果保存到数据库？",
            parent=self.view
        )
        
        # 如果用户确认保存
        if dialog.exec():
            success = self.inference_model.save_inference_session()
            if success:
                self.view.show_notification("保存开始", "正在后台保存推理结果到数据库...")
            else:
                self.view.show_error("保存错误", "没有推理结果可保存")
                
    def _on_inference_result(self, result):
        """处理推理结果"""
        if result and result.annotated_image is not None:
            # 将BGR格式转换为RGB格式显示
            rgb_image = cv2.cvtColor(result.annotated_image, cv2.COLOR_BGR2RGB)
            self.view.update_result_frame(rgb_image)
            
    def _on_inference_error(self, error_message: str):
        """处理推理错误"""
        self.view.show_error("推理错误", error_message)
        
    def _on_inference_interval_changed(self, interval: int):
        """处理推理间隔变更"""
        # 如果推理正在运行，需要先停止再重新启动以应用新的间隔
        if self.is_inference_running:
            self._stop_inference()
            self._start_inference()