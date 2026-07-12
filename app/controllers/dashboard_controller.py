from PyQt6.QtWidgets import QMessageBox
from app.models.dashboard_model import DashboardModel
from app.views.dashboard_view import DashboardView


class DashboardController:

    def __init__(self, view: DashboardView, model: DashboardModel):
        self.view = view
        self.model = model
        self.setup_connections()
        self.update_charts()

    def setup_connections(self):
        self.view.year_spin.valueChanged.connect(self.update_charts)
        self.view.month_combo.currentTextChanged.connect(self.update_charts)
        self.model.data_updated.connect(self.view.update_charts)
        
        # 连接Excel导出相关信号
        self.view.excel_export_requested.connect(self.export_to_excel)
        self.model.excel_export_finished.connect(self.on_excel_export_finished)
        self.model.excel_export_error.connect(self.on_excel_export_error)

    def update_charts(self):
        year = self.view.year_spin.value()
        month = int(self.view.month_combo.currentText())
        self.model.get_monthly_stats(year, month)
    
    def export_to_excel(self):
        """处理Excel导出请求"""
        year = self.view.year_spin.value()
        month = int(self.view.month_combo.currentText())
        self.model.export_monthly_data_to_excel(year, month)
    
    def on_excel_export_finished(self, filepath):
        """Excel导出完成时的处理"""
        QMessageBox.information(
            self.view, 
            "导出成功", 
            f"Excel文件已成功导出到：\n{filepath}"
        )
    
    def on_excel_export_error(self, error_msg):
        """Excel导出错误时的处理"""
        QMessageBox.critical(
            self.view, 
            "导出失败", 
            f"导出Excel文件时发生错误：\n{error_msg}"
        )