import traceback
import threading
import time

import cv2
import numpy as np
from PyQt6.QtCore import pyqtSignal, QObject, QThreadPool, QTimer, QTime
from PyQt6.QtGui import QImage

from app.models.database.defect_dao import DefectDAO
from app.models.database.inference_dao import InferenceDAO
from app.models.event_bus import EventBus
from app.models.utils import Worker, WorkerSignals
from ml.detector import Detector, InferenceResult


class CameraModel(QObject):
    # 摄像头信号
    camera_list_signal = pyqtSignal(list)  # 摄像头列表信号
    model_list_signal = pyqtSignal(list)  # 模型列表信号
    camera_frame_signal = pyqtSignal(object)  # 摄像头帧信号
    camera_started_signal = pyqtSignal(bool)  # 摄像头启动状态信号
    camera_error_signal = pyqtSignal(str)  # 摄像头错误信号
    
    # 图像捕获信号
    image_captured_signal = pyqtSignal(object)  # 图像捕获信号
    
    # 推理信号
    inference_started_signal = pyqtSignal()  # 推理开始信号
    inference_finished_signal : pyqtSignal = pyqtSignal(np.ndarray, InferenceResult)  # 推理完成信号，传递原图和推理结果
    inference_error_signal = pyqtSignal(str)  # 推理错误信号
    
    def __init__(self):
        super().__init__()
        self.detector: Detector = Detector()  # 初始化缺陷检测器
        self.defect_dao: DefectDAO = DefectDAO()  # 初始化缺陷数据访问对象
        self.inference_dao: InferenceDAO = InferenceDAO()  # 初始化推理数据访问对象
        self.thread_pool: QThreadPool = QThreadPool()
        self.thread_pool.setMaxThreadCount(3)  # 设置最大线程数
        
        # 摄像头相关对象
        self.camera_capture = None  # OpenCV摄像头对象
        self.current_camera_id = -1  # 当前摄像头ID
        self.camera_thread = None  # 摄像头线程
        self.camera_running = False  # 摄像头运行状态
        self.frame_timer = QTimer()  # 帧定时器
        self.frame_timer.timeout.connect(self._process_frame)
        
        self.current_frame: np.ndarray | None = None
        self.captured_image : np.ndarray | None = None
        self.inference_result : InferenceResult | None = None
        
        # 性能相关参数
        self.last_frame_time: int = 0  # 上一帧处理时间
        self.frame_interval: int = 1000 // 30  # 限制为30fps

        # 添加摄像头状态标识
        self.camera_is_starting = False
        self.camera_is_stopping = False
        
    def get_camera_list(self) -> list:
        """获取可用摄像头列表"""
        try:
            camera_list = []
            # 检查前10个摄像头索引
            for i in range(10):
                cap = cv2.VideoCapture(i)
                if cap.isOpened():
                    # 摄像头可用
                    ret, _ = cap.read()
                    if ret:
                        # 尝试获取摄像头名称（在某些系统上可能无法获取）
                        name = f"摄像头 {i}"
                        camera_list.append({
                            'id': i,
                            'description': name,
                            'device_id': str(i)
                        })
                    cap.release()
            
            if not camera_list:
                traceback.print_exc()
                
            self.camera_list_signal.emit(camera_list)
            return camera_list
        except Exception as e:
            error_msg = f"获取摄像头列表时出错: {str(e)}"
            self.camera_error_signal.emit(error_msg)
            return []
        
    def get_model_list(self) -> list:
        """获取可用模型列表"""
        try:
            model_list = self.detector.model_list
            self.model_list_signal.emit(model_list)
            return model_list
        except Exception as e:
            error_msg = f"获取模型列表时出错: {str(e)}"
            self.camera_error_signal.emit(error_msg)
            return []
        
    def start_camera(self, camera_id: int) -> bool:
        """启动摄像头"""
        try:
            # 如果已经在启动或停止过程中，直接返回
            if self.camera_is_starting or self.camera_is_stopping:
                self.camera_error_signal.emit("摄像头正在启动或关闭中，请稍候再试")
                return False
                
            # 标记开始启动
            self.camera_is_starting = True
            
            # 如果已经有摄像头在运行，先停止
            if self.camera_capture is not None:
                self.stop_camera()
                # 等待资源释放
                QTimer.singleShot(500, lambda: self._continue_start_camera(camera_id))
                return True
            else:
                return self._continue_start_camera(camera_id)
        except Exception as e:
            error_msg = f"启动摄像头时出现未预期的错误: {str(e)}"
            traceback.print_exc()
            self.camera_error_signal.emit(error_msg)
            self.camera_is_starting = False
            return False
    
    def _continue_start_camera(self, camera_id: int) -> bool:
        """继续启动摄像头的过程"""
        try:
            # 强制将camera_id转为整数
            try:
                camera_id = int(camera_id)
            except (TypeError, ValueError):
                error_msg = f"无效的摄像头ID: {camera_id}"
                self.camera_error_signal.emit(error_msg)
                self.camera_is_starting = False
                return False
            
            # 尝试打开摄像头
            self.camera_capture = cv2.VideoCapture(camera_id)
            if not self.camera_capture.isOpened():
                error_msg = f"无法打开摄像头 ID: {camera_id}"
                self.camera_error_signal.emit(error_msg)
                self.camera_is_starting = False
                return False
            
            # 保存当前使用的摄像头ID
            self.current_camera_id = camera_id
            
            # 设置摄像头分辨率（可选）
            self.camera_capture.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
            self.camera_capture.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
            
            # 启动摄像头线程
            self.camera_running = True
            self.camera_thread = threading.Thread(target=self._camera_thread_func)
            self.camera_thread.daemon = True
            self.camera_thread.start()
            
            self.frame_timer.start(30)
            
            self.camera_is_starting = False
            
            QTimer.singleShot(1000, lambda: self.camera_started_signal.emit(True))
            return True
            
        except Exception as e:
            error_msg = f"启动摄像头时出错: {str(e)}"
            traceback.print_exc()
            self.camera_error_signal.emit(error_msg)
            
            # 确保资源被释放
            self.stop_camera()
            self.camera_is_starting = False
            return False
    
    def _camera_thread_func(self):
        """摄像头线程函数"""
        try:
            while self.camera_running:
                if self.camera_capture is None or not self.camera_capture.isOpened():
                    # 摄像头已关闭，退出线程
                    break
                
                ret, frame = self.camera_capture.read()
                if ret:
                    # 转换为RGB格式（OpenCV默认为BGR）
                    frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                    self.current_frame = frame_rgb
                else:
                    # 读取失败
                    time.sleep(0.1)
        except Exception as e:
            error_msg = f"摄像头线程出错: {str(e)}"
            traceback.print_exc()
            QTimer.singleShot(0, lambda: self.camera_error_signal.emit(error_msg))
    
    def _process_frame(self):
        """处理当前帧并发送信号"""
        if self.current_frame is not None:
            # 控制帧率
            current_time = QTime.currentTime().msecsSinceStartOfDay()
            if current_time - self.last_frame_time < self.frame_interval:
                return  # 跳过此帧
            self.last_frame_time = current_time

            self.camera_frame_signal.emit(self.current_frame.copy())
    
    def stop_camera(self):
        """停止摄像头"""
        try:
            # 如果正在停止，不重复操作
            if self.camera_is_stopping:
                return
                
            self.camera_is_stopping = True
            
            # 停止帧处理定时器
            if self.frame_timer.isActive():
                self.frame_timer.stop()
            
            # 停止摄像头线程
            self.camera_running = False
            if self.camera_thread is not None and self.camera_thread.is_alive():
                self.camera_thread.join(timeout=2.0)  # 等待线程结束，最多2秒
                self.camera_thread = None
            
            # 释放摄像头资源
            if self.camera_capture is not None:
                self.camera_capture.release()
                self.camera_capture = None
            
            self.current_camera_id = -1
            
            # 重置状态标志
            self.camera_is_stopping = False
            
            # 发送摄像头已停止的信号
            self.camera_started_signal.emit(False)

        except Exception as e:
            error_msg = f"停止摄像头时出错: {str(e)}"
            traceback.print_exc()
            self.camera_error_signal.emit(error_msg)
            self.camera_is_stopping = False
    
    def capture_image(self) -> bool:
        """捕获当前帧作为图像"""
        try:
            if self.camera_running and self.current_frame is not None:
                # 复制当前帧
                self.captured_image = self.current_frame.copy()
                self.image_captured_signal.emit(self.captured_image)
                return True
            else:
                error_msg = "摄像头未启动或无可用帧"
                self.camera_error_signal.emit(error_msg)
                return False
        except Exception as e:
            error_msg = f"捕获图像时出错: {str(e)}"
            self.camera_error_signal.emit(error_msg)
            return False
    
    def start_inference(self, model_name: str):
        """开始推理"""
        if self.captured_image is None:
            self.inference_error_signal.emit("没有可用的图像进行推理")
            return
            
        # 将RGB转为BGR，因为detector需要BGR格式输入
        image_bgr = cv2.cvtColor(self.captured_image, cv2.COLOR_RGB2BGR)
        worker = Worker(self._inference_task, model_name, image_bgr)
        worker.signals.result.connect(self._handle_inference_result)
        worker.signals.error.connect(self._handle_inference_error)
        self.inference_started_signal.emit()
        self.thread_pool.start(worker)
    
    def _inference_task(self, model_name: str, image: np.ndarray, signals: WorkerSignals) -> InferenceResult:
        """推理任务"""
        try:
            # 执行推理
            result = self.detector.detect(model_name, image)
            return result
        except Exception as e:
            raise e
    
    def _handle_inference_result(self, result : InferenceResult):
        """处理推理结果"""
        self.inference_result = result
        self.inference_finished_signal.emit(self.captured_image, result)
    
    def _handle_inference_error(self, error_info):
        """处理推理错误"""
        exc_type, exc_value, _ = error_info
        error_message = str(exc_value)
        self.inference_error_signal.emit(error_message)
    
    def save_inference_to_db(self) -> bool:
        """保存推理结果到数据库"""
        if self.inference_result is None:
            return False
            
        worker = Worker(self._save_to_db_task)
        worker.signals.result.connect(self._handle_save_result)
        self.thread_pool.start(worker)
        return True
    
    def _save_to_db_task(self, signals: WorkerSignals) -> bool:
        """保存到数据库任务"""
        result = self.inference_result
        
        try:
            if result is None:
                return False
            original_image = result.original_image
            annotated_image = result.annotated_image

            original_image_bytes = cv2.imencode('.jpg', original_image)[1].tobytes() if original_image is not None else None
            annotated_image_bytes = cv2.imencode('.jpg', annotated_image)[1].tobytes() if annotated_image is not None else None

            # 保存推理结果基本信息
            inference_result_id = self.inference_dao.add_inference_result(
                defect_count=result.defect_count,
                original_image=original_image_bytes,
                annotated_image=annotated_image_bytes
            )
            
            # 保存缺陷计数信息
            for defect_name, count in result.defect_ids.items():
                self.defect_dao.add_defect_count(
                    inference_result_id=inference_result_id,
                    defect_name=defect_name,
                    count=count
                )
                
            return True
        except Exception as e:
            print(f"保存到数据库出错: {e}")
            return False
    
    def _handle_save_result(self, success: bool):
        """处理保存结果"""
        if success:
            # 发送全局通知
            EventBus.get_instance().inference_data_saved.emit()
            EventBus.get_instance().message_notification.emit("保存成功", "推理结果已成功保存到数据库")
