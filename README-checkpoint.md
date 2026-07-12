# Steel Defect 项目文档

## 快速开始

使用 Python 3.12 在 conda 环境下安装依赖：

```bash
pip install "PyQt6-Fluent-Widgets[full]" -i https://pypi.org/simple/
pip install -r requirements.txt
```

运行应用程序：

```bash
python main.py
```

> 注意：请确保手动放入模型文件到指定目录

## 项目概述

Steel Defect 是一个钢铁缺陷检测项目，主要组件包括：
- 使用 FastAPI 构建的 API 服务
- 使用 OpenCV 和自定义检测器进行图像处理和缺陷识别
- 数据库用于存储推理结果及缺陷统计信息

## API 接口

- **GET** `/inference_results`  
  分页获取所有推理结果。

- **GET** `/inference_results/{inference_id}`  
  根据 ID 获取单个推理结果。

- **POST** `/inference`  
  上传图片进行缺陷推理。  
  请求参数：
  - `model_name`: 模型名称 (Form)
  - `files`: 上传的图片文件 (File)，支持 JPEG、PNG 格式

## 数据库操作

推理结果及缺陷计数信息分别保存到 `inference_results` 与 `defect_counts` 表中。数据保存完成后，将通过事件总线触发信号更新。

## 应用打包与分发

### 打包应用

在支持的平台上运行 Python 脚本即可打包。脚本会自动：
- 安装 PyInstaller（如需）
- 清理旧的构建文件
- 根据当前平台选择合适的打包选项
- 执行打包操作

### 分发应用

打包完成后，应用程序将位于 `dist/steel_defect` 目录中：

- **Windows**：将目录压缩为 ZIP 文件，用户解压后运行 `steel_defect.exe`
- **macOS**：将目录压缩为 ZIP 或创建 DMG 安装镜像
- **Linux**：将目录压缩为 tar.gz 文件

### 用户安装和使用

用户解压应用程序后：

- **Windows**：双击 `steel_defect.exe` 或使用 `start_windows.bat`
- **macOS**：使用 `start_macos.sh` 或直接运行应用程序
- **Linux**：使用 `start_linux.sh` 脚本

## 注意事项

- **权限设置**：在 Linux/macOS 中，可能需要设置脚本执行权限
- **模型文件**：确保 `model` 目录中包含所有必要的模型文件
- **依赖管理**：PyInstaller 会自动打包大多数依赖，但某些特殊依赖可能需要手动处理
- **跨平台兼容性**：代码使用操作系统中立的路径处理方式，用户数据存储在用户主目录下