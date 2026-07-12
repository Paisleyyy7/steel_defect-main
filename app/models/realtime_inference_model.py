import time
import threading
import traceback
from datetime import datetime

import cv2
import numpy as np
from PyQt6.QtCore import QObject, QTimer, pyqtSignal

from app.models.camera_model import CameraModel
from app.models.database.defect_dao import DefectDAO
from app.models.database.inference_dao import InferenceDAO
from app.models.event_bus import EventBus
from ml.detector import Detector, InferenceResult


class RealtimeInferenceModel(QObject):
    """实时推理模型，负责处理摄像头捕获和定时推理的逻辑"""
    
    # 定义信号
    inference_result_signal = pyqtSignal(object)  # 推理结果信号
    statistics_updated_signal = pyqtSignal(int, int, int)  # 统计信息更新信号（总帧数，缺陷帧数，缺陷总数）
    inference_error_signal = pyqtSignal(str)  # 推理错误信号
    
    def __init__(self, camera_model: CameraModel):
        super().__init__()
        self.camera_model = camera_model
        self.detector = Detector()
        self.defect_dao = DefectDAO()
        self.inference_dao = InferenceDAO()
        
        # 推理定时器
        self.inference_timer = QTimer()
        self.inference_timer.timeout.connect(self._do_inference)
        
        # 推理间隔时间（秒）
        self.inference_interval = 5
        
        # 当前推理状态
        self.is_running = False
        
        # 统计信息
        self.total_frames = 0
        self.defect_frames = 0
        self.defect_count = 0
        
        # 本次推理会话记录
        self.session_start_time = None
        self.inference_results = []
        
    def start_inference(self, model_name: str, interval: int):
        """开始实时推理"""
        if self.is_running:
            return False
            
        if not model_name:
            self.inference_error_signal.emit("请先选择一个模型")
            return False
            
        self.model_name = model_name
        self.inference_interval = max(1, interval)  # 确保间隔至少为1秒
        
        # 重置统计信息
        self.total_frames = 0
        self.defect_frames = 0
        self.defect_count = 0
        self.inference_results = []
        self.session_start_time = datetime.now()
        
        # 发送初始统计信息
        self.statistics_updated_signal.emit(0, 0, 0)
        
        # 启动定时器
        self.is_running = True
        self.inference_timer.start(self.inference_interval * 1000)  # 毫秒
        
        return True
        
    def stop_inference(self):
        """停止实时推理"""
        if not self.is_running:
            return False
            
        # 停止定时器
        self.inference_timer.stop()
        self.is_running = False
        
        return True
        
    def save_inference_session(self):
        """保存本次推理会话的结果到数据库"""
        if not self.inference_results:
            return False
            
        try:
            # 开启一个线程进行数据库操作，避免阻塞主线程
            save_thread = threading.Thread(target=self._save_session_to_db)
            save_thread.daemon = True
            save_thread.start()
            return True
        except Exception as e:
            print(f"开始保存线程时错误: {e}")
            traceback.print_exc()
            return False
            
    def _save_session_to_db(self):
        """将推理会话数据保存到数据库的线程函数"""
        success_count = 0
        
        try:
            for result in self.inference_results:
                if result is None or result.original_image is None:
                    continue
                    
                # 将图像转换为字节流
                original_image_bytes = cv2.imencode('.jpg', result.original_image)[1].tobytes()
                annotated_image_bytes = None
                if result.annotated_image is not None:
                    annotated_image_bytes = cv2.imencode('.jpg', result.annotated_image)[1].tobytes()
                    
                # 保存推理结果基本信息
                inference_result_id = self.inference_dao.add_inference_result(
                    defect_count=result.defect_count,
                    original_image=original_image_bytes,
                    annotated_image=annotated_image_bytes
                )
                
                # 保存缺陷计数信息
                if result.defect_ids:
                    for defect_name, count in result.defect_ids.items():
                        self.defect_dao.add_defect_count(
                            inference_result_id=inference_result_id,
                            defect_name=defect_name,
                            count=count
                        )
                
                success_count += 1
                
            # 发出数据更新事件
            if success_count > 0:
                EventBus.get_instance().inference_data_saved.emit()
                EventBus.get_instance().message_notification.emit(
                    "保存成功", 
                    f"成功保存了{success_count}个推理结果到数据库"
                )
        except Exception as e:
            print(f"保存推理结果到数据库时错误: {e}")
            traceback.print_exc()
            
    def _do_inference(self):
        """执行单帧推理"""
        if not self.is_running or self.camera_model.current_frame is None:
            return
            
        try:
            # 获取当前帧
            current_frame = self.camera_model.current_frame.copy()
            
            # RGB转BGR，因为detector需要BGR格式
            frame_bgr = cv2.cvtColor(current_frame, cv2.COLOR_RGB2BGR)
            
            # 执行推理
            result = self.detector.detect(self.model_name, frame_bgr)
            
            # 更新统计信息
            self.total_frames += 1
            if result.defect_count > 0:
                self.defect_frames += 1
                self.defect_count += result.defect_count
                
            # 保存结果
            self.inference_results.append(result)
            
            # 发送推理结果信号
            self.inference_result_signal.emit(result)
            
            # 发送统计信息更新信号
            self.statistics_updated_signal.emit(
                self.total_frames,
                self.defect_frames,
                self.defect_count
            )
            
        except Exception as e:
            error_msg = f"执行推理时出错: {str(e)}"
            print(error_msg)
            traceback.print_exc()
            self.inference_error_signal.emit(error_msg)