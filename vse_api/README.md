# VSE Web API

这个目录提供一个独立的 `FastAPI` 后端，把当前仓库里的字幕提取能力包装成任务型 Web 服务。

接口文档见：[API.md](E:/short/tools/vse2.0/vse_api/API.md)

## 配置文件

配置文件路径：

```text
E:\short\tools\vse2.0\vse_api\config.json
```

当前支持：

- `storage.data_root`: 数据目录
- `server.host`: 监听地址
- `server.port`: 监听端口

默认配置：

```json
{
  "server": {
    "host": "0.0.0.0",
    "port": 8010
  },
  "storage": {
    "data_root": "D:\\short\\vse-data"
  }
}
```

## 数据目录

默认数据目录：

```text
D:\short\vse-data
```

SQLite 默认位置：

```text
D:\short\vse-data\app.db
```

## 安装依赖

在现有环境 `E:\short\venv\vse` 中执行：

```powershell
E:\short\venv\vse\python.exe -m pip install -r vse_api\requirements.txt
```

## 启动

```powershell
cd E:\short\tools\vse2.0
E:\short\venv\vse\python.exe -m vse_api.run
```

如果配置文件保持默认端口，打开：

- [http://127.0.0.1:8010/docs](http://127.0.0.1:8010/docs)

## 当前接口

- `GET /health`
- `POST /api/files`
- `GET /api/files`
- `GET /api/files/{file_id}`
- `DELETE /api/files/{file_id}`
- `POST /api/jobs`
- `GET /api/jobs`
- `GET /api/jobs/{job_id}`
- `GET /api/jobs/{job_id}/logs`
- `GET /api/jobs/{job_id}/files/srt`
- `GET /api/jobs/{job_id}/files/txt`
- `DELETE /api/jobs/{job_id}`

## 当前实现说明

- 文件和任务是分离资源
- 上传文件时需要传 `drama_name`
- 一个文件通常对应一集
- 一个任务绑定一个 `file_id`
- 使用 SQLite 保存文件与任务记录
- 使用本地磁盘保存上传文件、任务日志和结果文件
- 单 worker 串行执行任务，避免底层全局配置在并发下互相污染
