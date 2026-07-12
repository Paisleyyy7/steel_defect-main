from PyQt6.QtCore import pyqtSignal, QThreadPool, QObject

from app.models.database.defect_dao import DefectDAO
from app.models.database.inference_dao import InferenceDAO
from app.models.event_bus import EventBus
from app.models.utils import Worker, WorkerSignals



class DataModel(QObject):
    loaded_data_signal = pyqtSignal(dict) # 修改为发送字典，包含总数和数据
    
    def __init__(self):
        super().__init__()
        self.defect_dao = DefectDAO()
        self.inference_dao = InferenceDAO()
        self.thread_pool = QThreadPool() # 初始化线程池
        self.thread_pool.setMaxThreadCount(2) # 设置最大线程数，根据需要调整
        self.page = 1
        self.page_size = 10
        self.from_time = None
        self.to_time = None

        # 连接数据更新信号
        EventBus.get_instance().inference_data_saved.connect(self.load_data)


    def load_data(self, page=None):
        """
        加载指定页的数据
        """
        if page is not None:
            self.page = page
            
        worker = Worker(self.load_data_task)
        worker.signals.result.connect(self.loaded_data_signal.emit)
        self.thread_pool.start(worker)


    def load_data_task(self, signals: WorkerSignals):
        """
        分页加载数据任务
        """
        total, results = self.inference_dao.fetch_inference_results_by_page(
            self.page, 
            self.page_size,
            self.from_time,
            self.to_time
        )
        print(f"加载第 {self.page} 页数据，每页 {self.page_size} 条，总数 {total} 条，时间范围：{self.from_time} - {self.to_time}")

        return {
            'total': total,
            'data': results,
            'page': self.page,
            'page_size': self.page_size
        }


    def get_inference_result_by_id(self, id):
        """
        根据ID获取推理结果。

        Args:
            id (int): 推理结果ID。

        Returns:
            dict: 推理结果。
        """
        inference_result = self.inference_dao.get_inference_result_by_id(id)
        # 再从缺陷表中获取缺陷信息
        defects = self.defect_dao.fetch_defect_counts_by_inference_id(id)
        result = {
            'inference_result': inference_result,
            'defects': defects
        }
        print(f"根据ID获取推理结果，ID: {id}")  # 添加日志
        return result

    def set_time_filter(self, from_time, to_time):
        """设置时间过滤器"""
        self.from_time = from_time
        self.to_time = to_time
        self.load_data(1)  # 重置到第一页
