# Windows Share Guide

## 给朋友前先清理

保留：

- `apps/api/.env`：Supabase 配置
- `start-windows.bat`
- `apps/`
- `ROADMAP.md`
- `STATUS.md`

不要发送：

- `data/app.db`：这里可能有你的 API key、历史记录、路径
- `data/generated/*`：你的生成图片
- `data/reference-assets/*`：你的参考图
- `.venv/`
- `apps/web/node_modules/`

## Windows 使用方式

1. 安装 Python 3.11+。
2. 安装 Node.js LTS。
3. 解压项目文件夹。
4. 双击 `start-windows.bat`。
5. 浏览器打开后，进入设置填写自己的 API key。

脚本会自动：

- 创建 `.venv`
- 安装后端依赖
- 安装前端依赖
- 启动后端 `127.0.0.1:38381`
- 启动前端 `127.0.0.1:5173`
- 打开浏览器

## 打包命令示例

在 macOS 上可以这样创建一个干净副本：

```bash
cp -R /Users/milagro/Desktop/AIGC /tmp/AIGC-Windows
rm -f /tmp/AIGC-Windows/data/app.db
rm -rf /tmp/AIGC-Windows/data/generated/*
rm -rf /tmp/AIGC-Windows/data/reference-assets/*
rm -rf /tmp/AIGC-Windows/.venv
rm -rf /tmp/AIGC-Windows/apps/web/node_modules
```

然后把 `/tmp/AIGC-Windows` 压缩发给朋友。
