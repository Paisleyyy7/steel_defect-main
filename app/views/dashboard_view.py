import calendar
import datetime
import os
from datetime import datetime


from PyQt6.QtCharts import (QChart, QChartView, QPieSeries, QBarSeries, QBarSet,
                            QLineSeries, QValueAxis, QBarCategoryAxis, QDateTimeAxis)
from PyQt6.QtCore import Qt, QDateTime, pyqtSignal
from PyQt6.QtGui import QPainter, QImage, QColor, QPen
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout,
                             QComboBox, QLabel, QSpinBox, QMessageBox,
                             QTableWidget, QTableWidgetItem, QHeaderView, QGridLayout)
from qfluentwidgets import (PushButton, FluentIcon, ElevatedCardWidget,
                            TitleLabel, BodyLabel, CaptionLabel, SmoothScrollArea, HeaderCardWidget)


class DashboardView(QWidget):
    excel_export_requested = pyqtSignal()
    
    def __init__(self):
        super().__init__()
        self.setObjectName("dashboard_view")
        self.year_spin = QSpinBox()
        self.month_combo = QComboBox()
        self.summary_button = PushButton(FluentIcon.ACCEPT_MEDIUM, "生成报告")
        self.summary_button.clicked.connect(self.export_to_pdf)
        self.excel_export_button = PushButton(FluentIcon.DOCUMENT, "导出Excel")
        self.excel_export_button.clicked.connect(self.export_to_excel)
        
        # 创建QChart图表和视图
        self.daily_trend_chart = QChart()
        self.daily_trend_chart.setAnimationOptions(QChart.AnimationOption.SeriesAnimations)
        self.daily_trend_chart_view = QChartView(self.daily_trend_chart)
        self.daily_trend_chart_view.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        self.defect_type_chart = QChart()
        self.defect_type_chart.setAnimationOptions(QChart.AnimationOption.SeriesAnimations)
        self.defect_type_chart_view = QChartView(self.defect_type_chart)
        self.defect_type_chart_view.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        self.defect_type_pie_chart = QChart()
        self.defect_type_pie_chart.setAnimationOptions(QChart.AnimationOption.SeriesAnimations)
        self.defect_type_pie_chart_view = QChartView(self.defect_type_pie_chart)
        self.defect_type_pie_chart_view.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        self.setup_ui()

    def setup_ui(self):
        """设置UI组件和布局"""
        # 主滚动区域
        scroll = SmoothScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        
        main_widget = QWidget()
        main_layout = QVBoxLayout(main_widget)
        main_layout.setContentsMargins(24, 24, 24, 24)
        main_layout.setSpacing(24)
          # 顶部标题栏
        header_layout = QHBoxLayout()
        title = TitleLabel("数据概览")
        title.setObjectName("pageTitle")
        header_layout.addWidget(title)
        header_layout.addStretch()
        
        # 添加年月选择器
        controls_layout = QHBoxLayout()
        controls_layout.addWidget(QLabel("年份:"))
        self.year_spin.setMinimum(2020)
        self.year_spin.setMaximum(2030)
        self.year_spin.setValue(datetime.now().year)
        controls_layout.addWidget(self.year_spin)
        
        controls_layout.addWidget(QLabel("月份:"))
        for month in range(1, 13):
            self.month_combo.addItem(str(month))
        self.month_combo.setCurrentText(str(datetime.now().month))
        controls_layout.addWidget(self.month_combo)
        
        controls_layout.addStretch()
        controls_layout.addWidget(self.excel_export_button)
        controls_layout.addWidget(self.summary_button)
        
        header_layout.addLayout(controls_layout)
        
        main_layout.addLayout(header_layout)

        # 统计卡片区域
        stats_card = HeaderCardWidget()
        stats_card.setTitle("关键指标")
        
        # 统计布局
        stats_layout = QHBoxLayout()
        stats_layout.setSpacing(20)
        
        # 统计项
        self.total_detections_label = self._create_stat_item("总检测数", "0", "#007bff")
        self.total_defects_label = self._create_stat_item("缺陷总数", "0", "#dc3545")
        self.defect_rate_label = self._create_stat_item("缺陷率", "0%", "#28a745")
        self.latest_detection_label = self._create_stat_item("最新检测", "无", "#6c757d")
        
        stats_layout.addWidget(self.total_detections_label)
        stats_layout.addWidget(self.total_defects_label)
        stats_layout.addWidget(self.defect_rate_label)
        stats_layout.addWidget(self.latest_detection_label)
        
        stats_card.viewLayout.addLayout(stats_layout)
        main_layout.addWidget(stats_card)

        # 图表区域
        charts_grid = QGridLayout()
        charts_grid.setSpacing(24)

        # 1. 每日缺陷趋势图
        trend_card = HeaderCardWidget()
        trend_card.setTitle("每日缺陷趋势")
        
        self.daily_trend_chart_view.setMinimumSize(400, 300)
        trend_card.viewLayout.addWidget(self.daily_trend_chart_view)
        charts_grid.addWidget(trend_card, 0, 0)

        # 2. 缺陷类型条形图
        bar_chart_card = HeaderCardWidget()
        bar_chart_card.setTitle("缺陷类型统计")
        
        self.defect_type_chart_view.setMinimumSize(400, 300)
        bar_chart_card.viewLayout.addWidget(self.defect_type_chart_view)
        charts_grid.addWidget(bar_chart_card, 0, 1)

        # 3. 缺陷类型饼图
        pie_chart_card = HeaderCardWidget()
        pie_chart_card.setTitle("缺陷类型分布")
        
        self.defect_type_pie_chart_view.setMinimumSize(400, 300)
        pie_chart_card.viewLayout.addWidget(self.defect_type_pie_chart_view)
        charts_grid.addWidget(pie_chart_card, 1, 0)

        # 4. 数据汇总表格
        summary_table_card = HeaderCardWidget()
        summary_table_card.setTitle("数据汇总")
        
        # 初始化 summary_table
        self.summary_table = QTableWidget()
        self.summary_table.setColumnCount(2)
        self.summary_table.setHorizontalHeaderLabels(["缺陷类型", "数量"])
        header = self.summary_table.horizontalHeader()
        if header is not None:
            header.setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.summary_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.summary_table.setMinimumSize(400, 300)
        summary_table_card.viewLayout.addWidget(self.summary_table)
        charts_grid.addWidget(summary_table_card, 1, 1)

        main_layout.addLayout(charts_grid)
        
        # 设置滚动区域
        scroll.setWidget(main_widget)
        
        # 主布局
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(scroll)

    def _create_stat_item(self, title, value, color):
        """创建统计项"""
        card = ElevatedCardWidget()
        card.setObjectName("statItem")
        card.setMinimumWidth(150)
        
        layout = QVBoxLayout(card)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(5)
        
        title_label = CaptionLabel(title)
        title_label.setObjectName("statTitle")
        layout.addWidget(title_label)
        value_label = BodyLabel(value)
        value_label.setObjectName("statValue")
        value_label.setStyleSheet(f"color: {color}; font-size: 18px; font-weight: bold;")
        layout.addWidget(value_label)
        
        return card
        
    def _update_stat_item(self, card, value):
        """更新统计项的值"""
        # 找到卡片中的值标签(第二个标签)
        value_label = card.layout().itemAt(1).widget()
        if value_label:
            value_label.setText(value)
            
    def update_charts(self, data):
        # 没有数据时清空图表
        if (not data) or (not data.get('daily_counts')) or (not data.get('defect_types')):
            self.daily_trend_chart.removeAllSeries()
            self.defect_type_chart.removeAllSeries()
            self.defect_type_pie_chart.removeAllSeries()
            # 清空表格
            self.summary_table.setRowCount(0)
            # 清空关键指标
            self._update_stat_item(self.total_detections_label, "0")
            self._update_stat_item(self.total_defects_label, "0")
            self._update_stat_item(self.defect_rate_label, "0%")
            self._update_stat_item(self.latest_detection_label, "无")
            return
        
        # 更新关键指标
        total_inspections = data.get('total_inspections', 0)
        self._update_stat_item(self.total_detections_label, str(total_inspections))
        
        # 计算缺陷总数
        total_defects = sum(data['defect_types'].values()) if data.get('defect_types') else 0
        self._update_stat_item(self.total_defects_label, str(total_defects))
        
        # 计算缺陷率：检测出缺陷的检测次数 / 总检测次数
        defect_rate = 0
        defective_inspections = data.get('defective_inspections', 0)  # 检测出缺陷的检测次数
        if total_inspections > 0:
            defect_rate = (defective_inspections / total_inspections) * 100
        self._update_stat_item(self.defect_rate_label, f"{defect_rate:.2f}%")
        
        # 获取最新检测日期
        latest_date = None
        if data.get('daily_counts') and len(data['daily_counts']) > 0:
            latest_date = max(data['daily_counts'].keys())
            self._update_stat_item(self.latest_detection_label, latest_date.strftime("%Y-%m-%d"))
        else:
            self._update_stat_item(self.latest_detection_label, "无")
        
        # 更新每日缺陷趋势图
        self.update_daily_trend_chart(data['daily_counts'])
        # 更新各缺陷类型统计图（条形图）
        self.update_defect_type_chart(data['defect_types'])
        # 更新各缺陷类型统计图（饼图）
        self.update_defect_type_pie_chart(data['defect_types'])
        # 更新数据汇总表格
        self.update_summary_table(data)

    def update_daily_trend_chart(self, daily_counts):
        # 清除之前的数据和轴
        self.daily_trend_chart.removeAllSeries()
        for axis in self.daily_trend_chart.axes():
            self.daily_trend_chart.removeAxis(axis)

        if not daily_counts:  # 处理无数据情况
            # 设置空图表
            axis_x = QDateTimeAxis()
            axis_y = QValueAxis()
            axis_y.setRange(0, 10)
            self.daily_trend_chart.addAxis(axis_x, Qt.AlignmentFlag.AlignBottom)
            self.daily_trend_chart.addAxis(axis_y, Qt.AlignmentFlag.AlignLeft)
            self.daily_trend_chart.setTitle("每日缺陷趋势 (无数据)")
            return

        # 获取选中的年月
        year = self.year_spin.value()
        month = int(self.month_combo.currentText())

        # 获取当月的所有日期
        days_in_month = calendar.monthrange(year, month)[1]
        dates = [datetime(year, month, day).date() for day in range(1, days_in_month + 1)]

        # 构建完整的日期数据，没有数据的日期设为0
        sorted_daily = {d: daily_counts.get(d, 0) for d in dates}

        # 创建折线图系列
        line_series = QLineSeries()
        line_series.setName("每日缺陷数量")

        # 设置折线样式
        pen = QPen(QColor(255, 0, 0), 2)
        line_series.setPen(pen)

        min_date = None
        max_date = None
        max_count = 0

        # 添加数据点
        for date, count in sorted_daily.items():
            # 将Python日期转换为QDateTime
            qdt = QDateTime(date.year, date.month, date.day, 0, 0, 0)
            timestamp = qdt.toMSecsSinceEpoch()
            line_series.append(timestamp, count)

            # 记录最小/最大日期和最大值
            if min_date is None or qdt < min_date:
                min_date = qdt
            if max_date is None or qdt > max_date:
                max_date = qdt
            if count > max_count:
                max_count = count

        # 创建并设置X轴（时间轴）
        axis_x = QDateTimeAxis()
        axis_x.setFormat("MM-dd")  # 显示月-日格式

        # 检查日期是否为None，如果是则设置默认值
        if min_date is None or max_date is None:
            # 设置为当月第一天和最后一天
            first_day = QDateTime(year, month, 1, 0, 0, 0)
            last_day = QDateTime(year, month, days_in_month, 0, 0, 0)
            axis_x.setMin(first_day)
            axis_x.setMax(last_day)
        else:
            axis_x.setMin(min_date)
            axis_x.setMax(max_date)
        axis_x.setTitleText("日期")

        # 创建并设置Y轴
        axis_y = QValueAxis()
        axis_y.setLabelFormat("%d")
        axis_y.setRange(0, max(10, int(max_count * 1.5)))
        axis_y.setTitleText("缺陷数量")

        # 添加系列和轴到图表
        self.daily_trend_chart.addSeries(line_series)
        self.daily_trend_chart.addAxis(axis_x, Qt.AlignmentFlag.AlignBottom)
        self.daily_trend_chart.addAxis(axis_y, Qt.AlignmentFlag.AlignLeft)

        # 将系列附加到坐标轴
        line_series.attachAxis(axis_x)
        line_series.attachAxis(axis_y)

        # 设置图表标题
        self.daily_trend_chart.setTitle("每日缺陷趋势")

        # 启用图例
        legend = self.daily_trend_chart.legend()
        if legend:
            legend.setVisible(True)
            legend.setAlignment(Qt.AlignmentFlag.AlignBottom)

    def update_defect_type_chart(self, defect_types):
        # 清除之前的数据
        self.defect_type_chart.removeAllSeries()
        
        # 删除现有的坐标轴（如果有）
        for axis in self.defect_type_chart.axes():
            self.defect_type_chart.removeAxis(axis)
            
        if not defect_types:  # 处理无数据情况
            self.defect_type_chart.setTitle("缺陷类型统计 (无数据)")
            # 创建空轴
            axis_x = QBarCategoryAxis()
            axis_x.setCategories(["暂无数据"])
            axis_y = QValueAxis()
            axis_y.setRange(0, 10)
            
            self.defect_type_chart.addAxis(axis_x, Qt.AlignmentFlag.AlignBottom)
            self.defect_type_chart.addAxis(axis_y, Qt.AlignmentFlag.AlignLeft)
            return

        # 对缺陷名称按字母顺序排序
        sorted_defects = sorted(defect_types.items(), key=lambda x: x[0])
        defect_names = [name for name, _ in sorted_defects]
        
        # 创建条形集合和系列
        bar_set = QBarSet("缺陷数量")
        total_defects = sum(count for _, count in sorted_defects)
        
        # 设置每个缺陷类型的数量
        for _, count in sorted_defects:
            bar_set.append(count)
            
        # 创建条形图系列
        bar_series = QBarSeries()
        bar_series.append(bar_set)
        bar_series.setLabelsVisible(True)
        bar_series.setLabelsPosition(QBarSeries.LabelsPosition.LabelsOutsideEnd)
        
        bar_series.setLabelsFormat("@value")
        

        self.defect_type_chart.addSeries(bar_series)
        
        axis_x = QBarCategoryAxis()
        axis_x.setCategories(defect_names)
        self.defect_type_chart.addAxis(axis_x, Qt.AlignmentFlag.AlignBottom)
        bar_series.attachAxis(axis_x)
        
        # 创建Y轴（数量）
        axis_y = QValueAxis()
        max_count = max(count for _, count in sorted_defects) if sorted_defects else 10
        y_max = max(10, int(max_count * 1.5))  
        axis_y.setRange(0, y_max)
        axis_y.setLabelFormat("%d")  
        self.defect_type_chart.addAxis(axis_y, Qt.AlignmentFlag.AlignLeft)
        bar_series.attachAxis(axis_y)
        
        self.defect_type_chart.setTitle("缺陷类型统计")
        
        legend = self.defect_type_chart.legend()
        if legend:
            legend.setVisible(True)
            legend.setAlignment(Qt.AlignmentFlag.AlignBottom)

    def update_defect_type_pie_chart(self, defect_types):
        self.defect_type_pie_chart.removeAllSeries()
        
        if not defect_types: 
            self.defect_type_pie_chart.setTitle("缺陷类型分布 (无数据)")
            empty_series = QPieSeries()
            empty_series.append("暂无数据", 1)
            empty_slice = empty_series.slices()[0]
            empty_slice.setLabelVisible(True)
            self.defect_type_pie_chart.addSeries(empty_series)
            return
        
        sorted_defects = sorted(defect_types.items(), key=lambda x: x[0])
        
        pie_series = QPieSeries()
        total_defects = sum(count for _, count in sorted_defects)
        
        for defect_name, defect_count in sorted_defects:
            percentage = 0.0
            if total_defects > 0:
                percentage = (defect_count / total_defects) * 100
            slice = pie_series.append(f"{defect_name}: {defect_count} ({percentage:.1f}%)", defect_count)
            if slice:
                slice.setLabelVisible(True) 
        
        self.defect_type_pie_chart.addSeries(pie_series)
        
        self.defect_type_pie_chart.setTitle("缺陷类型分布")
        
        legend = self.defect_type_pie_chart.legend()
        if legend:
            legend.setVisible(True)
            legend.setAlignment(Qt.AlignmentFlag.AlignRight)

    def update_summary_table(self, data):
        # 清空表格
        self.summary_table.setRowCount(0)

        if not data or not data.get('defect_types'):
            return

        # 获取缺陷类型数据
        defect_types = data['defect_types']

        # 计算总缺陷数
        total_defects = sum(defect_types.values())

        # 按缺陷数排序，降序
        sorted_defects = sorted(defect_types.items(), key=lambda x: x[1], reverse=True)

        # 更新表格行数
        self.summary_table.setRowCount(len(sorted_defects) + 1)

        # 填充表格数据
        for row, (defect_name, count) in enumerate(sorted_defects):
            self.summary_table.setItem(row, 0, QTableWidgetItem(defect_name))
            self.summary_table.setItem(row, 1, QTableWidgetItem(str(count)))

        # 添加总计行
        self.summary_table.setItem(len(sorted_defects), 0, QTableWidgetItem("总计"))
        self.summary_table.setItem(len(sorted_defects), 1, QTableWidgetItem(str(total_defects)))

        # 设置最后一行样式
        for col in range(2):
            item = self.summary_table.item(len(sorted_defects), col)
            if item:
                item.setForeground(QColor(255, 0, 0))  # 红色

    def export_to_pdf(self):
        try:
            self.summary_button.hide()

            scale_factor = 2 
            width = int(self.width() * scale_factor)
            height = int(self.height() * scale_factor)

            img = QImage(width, height, QImage.Format.Format_ARGB32)
            img.setDotsPerMeterX(int(300 * 39.37))
            img.setDotsPerMeterY(int(300 * 39.37))
            img.fill(Qt.GlobalColor.white) 

            painter = QPainter(img)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)  
            painter.setRenderHint(QPainter.RenderHint.TextAntialiasing) 
            painter.scale(scale_factor, scale_factor)  
            self.render(painter)
            painter.end()

            user_home = os.path.expanduser("~")
            report_dir = os.path.join(user_home, "SteelDefect", "reports")
            os.makedirs(report_dir, exist_ok=True)
            
            # 生成文件名：report+选中时间的年月+目前时间的年月日时分秒
            year_value = self.year_spin.value()
            month_value = self.month_combo.currentText()
            # 确保月份是字符串并用0填充到2位
            month_str = str(month_value).zfill(2)
            current_time = datetime.now().strftime("%Y%m%d%H%M%S")  
            file_name = f"report_{year_value}{month_str}_{current_time}" 

            png_path = os.path.join(report_dir, f"{file_name}.png")
            success = img.save(png_path, "PNG", 100)

            if success:
                abs_path = os.path.abspath(png_path)
                QMessageBox.information(self, "保存成功", f"报告已保存到：\n{abs_path}")
                print(f"报告已保存到: {abs_path}")
            else:
                QMessageBox.warning(self, "保存失败", "报告保存失败，请检查路径权限")
        
        except Exception as e:
            QMessageBox.critical(self, "错误", f"保存报告时发生错误：\n{str(e)}")
        finally:
            self.summary_button.show()
    
    def export_to_excel(self):
        """导出当月详细数据到Excel表格"""
        # 触发数据导出信号，由controller处理
        self.excel_export_requested.emit()
