import sys
import traceback

from PyQt6.QtCore import QRunnable, pyqtSignal, QObject


class WorkerSignals(QObject):
    '''
    工作线程信号

    finished
        没有数据返回时，发出该信号

    error
        `tuple` (exctype, value, traceback.format_exc() )

    result
        `object` 数据返回时发出该信号

    progress
        `int` indicating % progress
    '''
    finished : pyqtSignal = pyqtSignal()
    error : pyqtSignal = pyqtSignal(tuple)
    result : pyqtSignal = pyqtSignal(object)
    progress : pyqtSignal = pyqtSignal(int)

class Worker(QRunnable):
    '''
    工作线程

    继承自 QRunnable，用于创建工作线程，避免GUI线程阻塞
    '''

    def __init__(self, fn, *args, **kwargs):
        super().__init__()

        # 存储传入的任务函数和参数
        self.fn = fn
        self.args = args
        self.kwargs = kwargs
        self.signals = WorkerSignals()

        # 添加回调kwargs
        self.kwargs['signals'] = self.signals


    def run(self):
        '''
        初始化、设置回调、把结果返回给调用者
        '''

        # Retrieve args/kwargs here; and fire processing using them
        try:
            result = self.fn(*self.args, **self.kwargs)
        except Exception as e:
            traceback.print_exc()
            exctype, value = sys.exc_info()[:2]
            self.signals.error.emit((exctype, value, traceback.format_exc()))
        else:
            self.signals.result.emit(result)  # 返回结果
        finally:
            self.signals.finished.emit()  # 完成
