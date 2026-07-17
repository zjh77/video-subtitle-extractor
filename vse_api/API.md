# VSE Web API 接口设计文档

本文档描述的是当前实现已经对齐的 API 契约：

- 先上传文件
- 文件归属于某部短剧
- 再基于 `file_id` 创建提取任务

## 1. 设计目标

适用场景：

- 上传一部短剧的多集视频
- 每个视频文件单独创建字幕提取任务
- 调用方按短剧维度管理素材
- 调用方轮询任务状态并下载 `srt/txt`

核心设计：

1. 文件接口与任务接口分离
2. 上传时显式传入 `drama_name`
3. 一个文件通常对应一集
4. 一个任务对应一个文件

## 2. 数据模型

## 2.1 文件对象

文件对象表示一个已经上传到服务端的视频文件。

```json
{
  "id": "file_01hf8v6b7n6m5k4j3h2g1f0e9d",
  "drama_name": "示例短剧",
  "episode_label": "01",
  "original_filename": "ep01.mp4",
  "stored_filename": "ep01.mp4",
  "stored_path": "E:\\short\\tools\\vse-data\\files\\file_01hf...\\ep01.mp4",
  "size_bytes": 24567890,
  "mime_type": "video/mp4",
  "status": "ready",
  "created_at": "2026-06-04T10:00:00.000000+00:00"
}
```

### 文件状态

- `uploading`: 正在上传
- `ready`: 上传完成，可用于创建任务
- `deleted`: 已删除

## 2.2 任务对象

任务对象表示一次字幕提取任务。

```json
{
  "id": "job_01hf8vf1d0x4wkqay9h2r3m4n5",
  "file_id": "file_01hf8v6b7n6m5k4j3h2g1f0e9d",
  "drama_name": "示例短剧",
  "episode_label": "01",
  "status": "running",
  "mode": "fast",
  "language": "ch",
  "generate_txt": true,
  "subtitle_ymin": null,
  "subtitle_ymax": null,
  "subtitle_xmin": null,
  "subtitle_xmax": null,
  "progress": 52.3,
  "stage": "ocr=31.0, frame=100.0, post=26.0",
  "result_srt_path": null,
  "result_txt_path": null,
  "error_message": null,
  "created_at": "2026-06-04T10:01:00.000000+00:00",
  "started_at": "2026-06-04T10:01:02.000000+00:00",
  "finished_at": null
}
```

### 任务状态

- `queued`
- `running`
- `succeeded`
- `failed`

## 3. 接口总览

## 3.1 文件接口

- `POST /api/files`
- `GET /api/files`
- `GET /api/files/{file_id}`
- `DELETE /api/files/{file_id}`

## 3.2 任务接口

- `POST /api/jobs`
- `GET /api/jobs`
- `GET /api/jobs/{job_id}`
- `GET /api/jobs/{job_id}/logs`
- `GET /api/jobs/{job_id}/files/srt`
- `GET /api/jobs/{job_id}/files/txt`
- `DELETE /api/jobs/{job_id}`

## 4. 文件接口

## 4.1 上传视频文件

`POST /api/files`

用途：

- 上传单个视频文件
- 归属到某部短剧
- 可选标记集数

### Content-Type

`multipart/form-data`

### 表单字段

| 字段 | 必填 | 类型 | 说明 |
|---|---|---|---|
| `file` | 是 | file | 视频文件 |
| `drama_name` | 是 | string | 短剧名称 |
| `episode_label` | 否 | string | 集数标识，如 `01`、`E02` |
| `filename` | 否 | string | 希望保存的展示文件名 |

### 说明

- `drama_name` 是业务主字段，其他项目后续可按它聚合查询
- `filename` 是展示名，不一定等于服务端最终安全落盘名
- 服务端应保留原始名称，同时生成安全文件名用于落盘

### 请求示例

```bash
curl -X POST "http://127.0.0.1:8010/api/files" \
  -F "file=@D:/videos/ep01.mp4" \
  -F "drama_name=示例短剧" \
  -F "episode_label=01" \
  -F "filename=episode_01.mp4"
```

### 响应示例

```json
{
  "id": "file_01hf8v6b7n6m5k4j3h2g1f0e9d",
  "drama_name": "示例短剧",
  "episode_label": "01",
  "original_filename": "ep01.mp4",
  "stored_filename": "episode_01.mp4",
  "stored_path": "E:\\short\\tools\\vse-data\\files\\file_01hf...\\episode_01.mp4",
  "size_bytes": 24567890,
  "mime_type": "video/mp4",
  "status": "ready",
  "created_at": "2026-06-04T10:00:00.000000+00:00"
}
```

## 4.2 文件列表

`GET /api/files`

### 查询参数

| 参数 | 必填 | 类型 | 默认值 | 说明 |
|---|---|---|---|---|
| `drama_name` | 否 | string | - | 按短剧名称过滤 |
| `limit` | 否 | int | `100` | 返回条数 |

### 请求示例

```bash
curl "http://127.0.0.1:8010/api/files?drama_name=示例短剧&limit=50"
```

### 响应示例

```json
{
  "items": [
    {
      "id": "file_01hf8v6b7n6m5k4j3h2g1f0e9d",
      "drama_name": "示例短剧",
      "episode_label": "01",
      "original_filename": "ep01.mp4",
      "stored_filename": "episode_01.mp4",
      "stored_path": "E:\\short\\tools\\vse-data\\files\\file_01hf...\\episode_01.mp4",
      "size_bytes": 24567890,
      "mime_type": "video/mp4",
      "status": "ready",
      "created_at": "2026-06-04T10:00:00.000000+00:00"
    }
  ]
}
```

## 4.3 查询单个文件

`GET /api/files/{file_id}`

### 响应

返回单个文件对象。

## 4.4 删除文件

`DELETE /api/files/{file_id}`

支持查询参数：

- `force=true`

### 行为

- 删除文件记录
- 删除上传的原始视频文件
- 默认情况下，如果该文件已有任务，返回 `409`
- 当 `force=true` 时，会先删除该文件关联的所有任务及其产物，再删除文件

### 请求示例

普通删除：

```bash
curl -X DELETE "http://127.0.0.1:8010/api/files/file_01hf8v6b7n6m5k4j3h2g1f0e9d"
```

级联删除：

```bash
curl -X DELETE "http://127.0.0.1:8010/api/files/file_01hf8v6b7n6m5k4j3h2g1f0e9d?force=true"
```

### 响应示例

```json
{
  "status": "deleted"
}
```

## 5. 任务接口

## 5.1 创建任务

`POST /api/jobs`

用途：

- 基于已上传文件创建字幕提取任务
- 不再把“上传文件”和“创建任务”耦合在同一个接口中

### Content-Type

`application/json`

### 请求体

```json
{
  "file_id": "file_01hf8v6b7n6m5k4j3h2g1f0e9d",
  "mode": "fast",
  "language": "ch",
  "generate_txt": true,
  "subtitle_area": {
    "ymin": 900,
    "ymax": 1040,
    "xmin": 80,
    "xmax": 1840
  }
}
```

### 字段说明

| 字段 | 必填 | 类型 | 默认值 | 说明 |
|---|---|---|---|---|
| `file_id` | 是 | string | - | 已上传文件 ID |
| `mode` | 否 | string | `fast` | 提取模式 |
| `language` | 否 | string | `ch` | 识别语言 |
| `generate_txt` | 否 | boolean | `true` | 是否生成 txt |
| `subtitle_area` | 否 | object | - | 手动指定字幕区域 |

### 响应示例

```json
{
  "id": "job_01hf8vf1d0x4wkqay9h2r3m4n5",
  "file_id": "file_01hf8v6b7n6m5k4j3h2g1f0e9d",
  "drama_name": "示例短剧",
  "episode_label": "01",
  "status": "queued",
  "mode": "fast",
  "language": "ch",
  "generate_txt": true,
  "subtitle_ymin": 900,
  "subtitle_ymax": 1040,
  "subtitle_xmin": 80,
  "subtitle_xmax": 1840,
  "progress": 0,
  "stage": "queued",
  "result_srt_path": null,
  "result_txt_path": null,
  "error_message": null,
  "created_at": "2026-06-04T10:01:00.000000+00:00",
  "started_at": null,
  "finished_at": null
}
```

## 5.2 任务列表

`GET /api/jobs`

### 查询参数

| 参数 | 必填 | 类型 | 默认值 | 说明 |
|---|---|---|---|---|
| `drama_name` | 否 | string | - | 按短剧名称过滤 |
| `status` | 否 | string | - | 按任务状态过滤 |
| `limit` | 否 | int | `100` | 返回条数 |

### 请求示例

```bash
curl "http://127.0.0.1:8010/api/jobs?drama_name=示例短剧&limit=20"
```

## 5.3 查询单个任务

`GET /api/jobs/{job_id}`

返回单个任务对象。

## 5.4 查询任务日志

`GET /api/jobs/{job_id}/logs`

### 响应示例

```json
{
  "job_id": "job_01hf8vf1d0x4wkqay9h2r3m4n5",
  "content": "[2026-06-04 18:01:02] Running extractor for: ...\n[2026-06-04 18:02:10] Job completed successfully.\n"
}
```

## 5.5 下载 SRT

`GET /api/jobs/{job_id}/files/srt`

成功时返回文件流。

## 5.6 下载 TXT

`GET /api/jobs/{job_id}/files/txt`

成功时返回文件流。

## 5.7 删除任务

`DELETE /api/jobs/{job_id}`

### 行为

- 删除任务记录
- 删除任务日志、中间文件、输出文件
- 不删除原始上传文件

### 响应示例

```json
{
  "status": "deleted"
}
```

## 6. 推荐调用流程

对于一部短剧的多集视频，推荐这样接：

1. 对每一集调用 `POST /api/files`
2. 记录返回的 `file_id`
3. 按需对每个 `file_id` 调 `POST /api/jobs`
4. 轮询 `GET /api/jobs/{job_id}`
5. 成功后下载 `srt/txt`

## 7. 多集短剧示例

假设你上传一部短剧《春夜回响》的三集视频：

### 第一步：上传三个文件

- `drama_name=春夜回响`
- `episode_label=01`
- `episode_label=02`
- `episode_label=03`

拿到：

- `file_a`
- `file_b`
- `file_c`

### 第二步：分别创建任务

```json
POST /api/jobs
{
  "file_id": "file_a",
  "mode": "fast",
  "language": "ch",
  "generate_txt": true
}
```

对 `file_b`、`file_c` 重复同样流程。

### 第三步：按任务轮询

- `GET /api/jobs/{job_id}`
- 直到 `status == "succeeded"`

### 第四步：下载结果

- `GET /api/jobs/{job_id}/files/srt`
- `GET /api/jobs/{job_id}/files/txt`

## 8. 字段约定建议

为了让你的其他项目接入更稳定，我建议统一遵守下面约定：

## 8.1 `drama_name`

- 用于业务展示和聚合查询
- 保留原始中文名称
- 不建议调用方依赖它来推导磁盘路径

## 8.2 `episode_label`

建议保持字符串类型，不要强制 int。

推荐值示例：

- `01`
- `02`
- `E01`
- `SP1`

## 8.3 `filename`

上传时可以传展示名，但服务端应自行生成安全落盘名。

## 9. 错误返回建议

建议统一使用：

```json
{
  "detail": "错误说明"
}
```

常见错误：

- `400`: 参数错误
- `404`: 文件或任务不存在
- `409`: 文件状态不允许创建任务，或删除文件时仍存在关联任务
- `422`: 请求格式校验失败

## 10. 当前实现建议

结合你当前场景，我建议第一版按下面方式实现：

- 不做分片上传
- 一次上传一个完整视频文件
- 允许重复上传同名视频
- 用 `drama_name + episode_label + file_id` 做业务定位
- 保留任务与文件分离的结构
