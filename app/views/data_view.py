from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QHeaderView, QTableWidgetItem
from qfluentwidgets import (CardWidget, PushButton, TableWidget, CalendarPicker,
                            ComboBox, LineEdit, ToolButton, FluentIcon, StrongBodyLabel,
                            TitleLabel, BodyLabel, CaptionLabel, ElevatedCardWidget,
                            HeaderCardWidget, SmoothScrollArea)
from qfluentwidgets import SmoothMode

"""数据管理页面设计
该页面负责展示和管理钢材缺陷检测的历史数据。
布局结构:
- 顶部：时间筛选区域，包含开始/结束时间选择器和筛选按钮
- 中部：表格区域，展示检测数据及操作按钮
- 底部：分页控件，实现数据分页浏览功能
"""


class DataView(QWidget):
    """数据管理视图

    负责展示历史检测数据，支持时间筛选和分页浏览

    Signals:
        check_data_signal: 发送查看详情请求，传递数据ID
        page_changed_signal: 页码变化信号，传递新页码
        page_size_changed_signal: 页面大小变化信号，传递新页面大小
    """
    check_data_signal = pyqtSignal(int)
    page_changed_signal = pyqtSignal(int)
    page_size_changed_signal = pyqtSignal(int)

    def __init__(self):
        """初始化数据视图"""
        super().__init__()
        self.setObjectName("data_view")
        self.data = []
        self.from_time = None
        self.to_time = None
        self.current_page = 1
        self.total_pages = 1
        self.page_sizes = [10, 20, 50, 100]  # 预设的每页显示数量选项
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
        title = TitleLabel("数据管理")
        title.setObjectName("pageTitle")
        header_layout.addWidget(title)
        header_layout.addStretch()
        
        main_layout.addLayout(header_layout)

        # 时间筛选区域
        filter_card = HeaderCardWidget("时间筛选")
        filter_layout = QHBoxLayout()
        
        self.from_date_picker = CalendarPicker()
        self.to_date_picker = CalendarPicker()
        self.filter_button = PushButton("筛选")
        
        filter_layout.addWidget(BodyLabel("开始时间:"))
        filter_layout.addWidget(self.from_date_picker)
        filter_layout.addWidget(BodyLabel("结束时间:"))
        filter_layout.addWidget(self.to_date_picker)
        filter_layout.addStretch()
        filter_layout.addWidget(self.filter_button)
        
        filter_card.viewLayout.addLayout(filter_layout)
        main_layout.addWidget(filter_card)

        # 数据表格区域
        table_card = HeaderCardWidget("检测数据")
        self.table_widget = TableWidget()
        self.table_widget.scrollDelagate.verticalSmoothScroll.setSmoothMode(SmoothMode.NO_SMOOTH)
        self.table_widget.setBorderRadius(8)
        self.table_widget.setBorderVisible(True)
        header = self.table_widget.horizontalHeader()
        if header is not None:
            header.setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table_widget.setEditTriggers(TableWidget.EditTrigger.NoEditTriggers)
        self.table_widget.setColumnCount(4)
        self.table_widget.setHorizontalHeaderLabels(["id", "缺陷数量", "时间", "操作"])
        
        table_card.viewLayout.addWidget(self.table_widget)
        main_layout.addWidget(table_card)

        # 分页控件
        pagination_card = HeaderCardWidget("分页控制")
        pagination_layout = QHBoxLayout()
        
        self.page_size_combo = ComboBox()
        self.page_size_combo.addItems([str(size) for size in self.page_sizes])
        self.page_size_combo.setCurrentText('10')
        self.page_size_combo.setFixedWidth(80)
        
        self.first_page_btn = PushButton("首页")
        self.prev_btn = ToolButton(FluentIcon.LEFT_ARROW)
        self.page_edit = LineEdit()
        self.page_edit.setFixedWidth(50)
        self.page_edit.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.page_total_label = StrongBodyLabel('/ 1')
        self.next_btn = ToolButton(FluentIcon.RIGHT_ARROW)
        self.last_page_btn = PushButton("尾页")
        self.goto_btn = PushButton('跳转')
        
        pagination_layout.addWidget(BodyLabel('每页显示:'))
        pagination_layout.addWidget(self.page_size_combo)
        pagination_layout.addStretch()
        pagination_layout.addWidget(self.first_page_btn)
        pagination_layout.addWidget(self.prev_btn)
        pagination_layout.addSpacing(10)
        pagination_layout.addWidget(self.page_edit)
        pagination_layout.addWidget(self.page_total_label)
        pagination_layout.addSpacing(10)
        pagination_layout.addWidget(self.next_btn)
        pagination_layout.addWidget(self.last_page_btn)
        pagination_layout.addSpacing(20)
        pagination_layout.addWidget(self.goto_btn)
        pagination_layout.addStretch()
        
        pagination_card.viewLayout.addLayout(pagination_layout)
        main_layout.addWidget(pagination_card)

        # 设置滚动区域
        scroll.setWidget(main_widget)
        
        # 主布局
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(scroll)

        # 绑定事件
        self.first_page_btn.clicked.connect(lambda: self.page_changed_signal.emit(1))
        self.prev_btn.clicked.connect(self.prev_page)
        self.next_btn.clicked.connect(self.next_page)
        self.last_page_btn.clicked.connect(lambda: self.page_changed_signal.emit(self.total_pages))
        self.goto_btn.clicked.connect(self.jump_to_page)
        self.page_size_combo.currentTextChanged.connect(
            lambda x: self.page_size_changed_signal.emit(int(x))
        )

        self.resize(1280, 720)

    def init_data(self, data):
        """
        初始化表格数据和分页信息
        """
        self.data = data['data']
        total = data['total']
        page_size = data['page_size']
        self.current_page = data['page']
        self.total_pages = (total + page_size - 1) // page_size

        # 更新分页控件状态
        self.update_pagination()
        # 填充表格数据
        self.populate_table()

    def update_pagination(self):
        """
        更新分页控件状态
        """
        self.page_edit.setText(str(self.current_page))
        self.page_total_label.setText(f'/ {self.total_pages}')

        # 更新按钮状态
        self.first_page_btn.setEnabled(self.current_page > 1)
        self.prev_btn.setEnabled(self.current_page > 1)
        self.next_btn.setEnabled(self.current_page < self.total_pages)
        self.last_page_btn.setEnabled(self.current_page < self.total_pages)

    def prev_page(self):
        if self.current_page > 1:
            self.page_changed_signal.emit(self.current_page - 1)

    def next_page(self):
        if self.current_page < self.total_pages:
            self.page_changed_signal.emit(self.current_page + 1)

    def jump_to_page(self):
        """
        跳转到指定页面
        """
        try:
            page = int(self.page_edit.text())
            if 1 <= page <= self.total_pages:
                self.page_changed_signal.emit(page)
            else:
                self.page_edit.setText(str(self.current_page))
        except ValueError:
            self.page_edit.setText(str(self.current_page))

    # 在 ui 上显示数据
    def populate_table(self):
        self.table_widget.setRowCount(len(self.data))
        header = self.table_widget.horizontalHeader()
        if header is not None:
            header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        for row, info in enumerate(self.data):
            self.setup_table_row(row, info)

    def setup_table_row(self, row, info):
        # 赋值其他列
        for clo, value in enumerate(info.values()):
            item = QTableWidgetItem(str(value))
            item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table_widget.setItem(row, clo, item)

        # 添加操作按钮
        button = PushButton("查看", self)
        button.clicked.connect(lambda: self.check_data_signal.emit(info['id']))
        button.setFixedSize(100, 30)

        widget = QWidget()
        button_layout = QHBoxLayout(widget)
        button_layout.addWidget(button)
        button_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        button_layout.setContentsMargins(0, 0, 0, 0)
        self.table_widget.setCellWidget(row, 3, widget)
