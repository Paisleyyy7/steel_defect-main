import traceback
from time import sleep
from typing import List, Optional

import cv2
import numpy as np

from PyQt6.QtCore import QObject, QThreadPool, pyqtSignal
from app.models.database.defect_dao import DefectDAO
from app.models.database.inference_dao import InferenceDAO
from app.models.event_bus import EventBus
from app.models.utils import WorkerSignals, Worker
from ml.detector import Detector, InferenceResult


class InferenceModel(QObject):
    """
    推理模型类，负责管理推理流程和数据存储
    
    核心功能:
    1. 管理模型加载和选择
    2. 处理图像推理任务
    3. 保存推理结果到数据库
    4. 通过信号机制与视图层通信
    """
    
    # 定义信号
    init_data_signal = pyqtSignal(list)  # 初始化数据信号
    start_inference_signal = pyqtSignal()  # 开始推理信号
    update_inference_progress = pyqtSignal(int)  # 更新进度信号
    finished_inference_signal = pyqtSignal(int)  # 推理完成信号
    inference_data_saved = pyqtSignal()  # 推理数据保存信号
    step_inference_signal = pyqtSignal(object)  # 每推理完一张图片后发送推理结果
    error_signal = pyqtSignal(str)  # 错误信号

    def __init__(self):
        """初始化推理模型组件和线程池"""
        super().__init__()
        self.defect_dao = DefectDAO()
        self.inference_dao = InferenceDAO()
        self.detector = Detector()
        self.thread_pool = QThreadPool()

        # 设置最大线程数，避免资源过度消耗
        self.thread_pool.setMaxThreadCount(2)


    def init_data(self):
        """初始化数据，包括模型列表等"""
        try:
            self.init_data_signal.emit(self.detector.model_list)
        except Exception as e:
            self.error_signal.emit(f"初始化数据失败: {str(e)}")

    def start_select_image_2_inference(self, selected_files: List[str], model_name: str):
        """
        选择图片并进行推理然后保存到数据库
        
        Args:
            selected_files: 选择的图片文件路径列表
            model_name: 选择的模型名称
        """
        # 参数验证
        if not selected_files:

            self.error_signal.emit("请选择至少一个图片文件")
            return
            
        if not model_name:

            self.error_signal.emit("请先选择一个模型")
            return
        
        # 创建工作线程
        worker = Worker(self.select_images_task, selected_files, model_name)
        worker.signals.result.connect(self.finished_select_images)
        worker.signals.error.connect(self.handle_error)
        self.thread_pool.start(worker)

    def handle_error(self, error_info):
        """
        处理错误信息
        
        Args:
            error_info: 错误信息
        """

        self.error_signal.emit(str(error_info))

    def select_images_task(self, selected_files: List[str], model_name: str, signals: WorkerSignals):
        """
        加载选中的图片任务
        
        Args:
            selected_files: 选择的图片文件路径列表
            model_name: 选择的模型名称
            signals: 工作线程信号对象
        
        Returns:
            元组: (model_name, images)
        """
        images = []
        for file in selected_files:
            try:
                image = cv2.imread(file)
                if image is None:

                    continue
                    
                images.append(image)
            except Exception as e:

                continue
                
        if not images:
            raise ValueError("没有成功加载任何图片")
            
        return model_name, images

    def finished_select_images(self, args):
        """
        图像加载完成的回调函数
        
        Args:
            args: 包含模型名称和图像列表的元组
        """
        self.start_inference(*args)

    def start_inference(self, model_name: str, images: List[np.ndarray]):
        """
        开始推理流程
        
        Args:
            model_name: 使用的模型名称
            images: 图像数据列表
        """
        if not images:

            return
            
        worker = Worker(self.inference_task, model_name, images)
        self.start_inference_signal.emit()  # 发送开始推理信号
        worker.signals.progress.connect(self.update_inference_progress.emit)  # 发送更新进度信号
        worker.signals.result.connect(self.finished_inference)  # 完成后调用保存到数据库的函数
        worker.signals.error.connect(self.handle_error)  # 错误处理
        self.thread_pool.start(worker)  # 启动线程


    def inference_task(self, model_name: str, images: List[np.ndarray], signals: WorkerSignals):
        """
        推理任务，在工作线程中执行
        
        Args:
            model_name: 模型名称
            images: 图像数据列表
            signals: 工作线程信号对象
        
        Returns:
            List[InferenceResult]: 推理结果列表
        """
        img_count = len(images)
        results = []
        count = 0

        
        for i, image in enumerate(images):
            try:
                if image is None:

                    continue
                    
                result = self.detector.detect(model_name=model_name, img=image)
                if result:
                    results.append(result)
                    # 发送中间结果信号
                    self.step_inference_signal.emit(result)
            except Exception as e:

                traceback.print_exc()
                continue
            finally:
                count += 1
                # 发送进度信号
                signals.progress.emit(int(count * 100 / img_count))
                

        
        # 等待页面渲染
        sleep(0.3)
        return results

    def finished_inference(self, results: List[InferenceResult]):
        """
        推理完成后的处理函数
        
        Args:
            results: 推理结果列表
        """
        if not results:

            self.error_signal.emit("推理未产生有效结果")
            return
            
        self.finished_inference_signal.emit(len(results))  # 发送推理完成信号
        self.start_save_2_db(results)

    def start_save_2_db(self, results: List[InferenceResult]):
        """
        启动保存到数据库的线程
        
        Args:
            results: 推理结果列表
        """
        worker = Worker(self.save_2_db_task, results)
        worker.signals.error.connect(self.handle_error)
        self.thread_pool.start(worker)


    def save_2_db_task(self, results: List[InferenceResult], signals: WorkerSignals):
        """
        保存推理结果到数据库任务
        
        Args:
            results: 推理结果列表
            signals: 工作线程信号对象
        """
        success_count = 0
        
        for i, result in enumerate(results):
            try:
                # 检查数据有效性
                if result is None or result.original_image is None:

                    continue
                
                # 将原始图像和标注图像转换为 bytes
                original_image_bytes = cv2.imencode('.jpg', result.original_image)[1].tobytes()
                
                # 安全地处理可能为空的标注图像
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
                
            except Exception as e:

                traceback.print_exc()
                
        # 发送数据更新信号
        if success_count > 0:
            EventBus.get_instance().inference_data_saved.emit()
            EventBus.get_instance().message_notification.emit("上传成功", f"成功上传了{success_count}张图片")
