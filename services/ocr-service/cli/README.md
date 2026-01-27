# OCR CLI 命令行工具

OCR服务的命令行接口，支持从终端直接调用OCR功能。

## 安装

```bash
# 添加到PATH
export PATH="$PATH:/path/to/one-data-studio/services/ocr-service/cli"

# 或创建软链接
sudo ln -s /path/to/one-data-studio/services/ocr-service/cli/ocr_cli.py /usr/local/bin/ocr-cli
```

## 使用方法

### 健康检查

```bash
ocr-cli health
```

### 文档提取

```bash
# 自动检测文档类型
ocr-cli extract document.pdf

# 指定文档类型
ocr-cli extract invoice.pdf --type invoice

# 保存结果到文件
ocr-cli extract contract.pdf --type contract -o result.json

# 安静模式
ocr-cli extract document.pdf -q
```

### 批量处理

```bash
# 处理多个文件
ocr-cli batch file1.pdf file2.pdf file3.pdf

# 处理整个目录
ocr-cli batch ./documents/

# 保存批量结果
ocr-cli batch ./documents/ -o results.json

# 指定文档类型
ocr-cli batch ./invoices/ --type invoice
```

### 文档类型检测

```bash
ocr-cli detect document.pdf
```

### 模板管理

```bash
# 列出所有模板
ocr-cli templates list

# 筛选特定类型
ocr-cli templates list --type invoice

# 显示所有模板（包括禁用的）
ocr-cli templates list --all

# 获取支持的文档类型
ocr-cli templates types

# 加载默认模板
ocr-cli templates load-defaults
```

### 服务信息

```bash
ocr-cli server --info
```

## 命令参考

| 命令 | 描述 |
|------|------|
| `health` | 检查服务健康状态 |
| `extract` | 提取单个文档 |
| `batch` | 批量处理文档 |
| `detect` | 自动检测文档类型 |
| `templates list` | 列出模板 |
| `templates load-defaults` | 加载默认模板 |
| `templates types` | 获取支持的文档类型 |
| `server --info` | 显示服务信息 |

## 选项

| 选项 | 描述 | 默认值 |
|------|------|--------|
| `--url` | OCR服务地址 | http://localhost:8007 |
| `--type, -t` | 文档类型 | auto |
| `--output, -o` | 输出文件路径 | - |
| `--timeout` | 超时时间（秒） | 300 |
| `--quiet, -q` | 安静模式 | false |
| `--all, -a` | 显示所有 | false |

## 退出码

| 退出码 | 含义 |
|--------|------|
| 0 | 成功 |
| 1 | 错误 |
| 130 | 用户取消 |

## 示例

### 处理发票并提取金额

```bash
# 提取发票
ocr-cli extract invoice.pdf --type invoice -o result.json

# 使用jq提取金额
cat result.json | jq '.structured_data.total_amount'
```

### 批量处理并统计

```bash
# 处理所有发票
ocr-cli batch ./invoices/ --type invoice -o results.json

# 统计成功数量
cat results.json | jq '[.[] | select(.status == "completed")] | length'
```

### 集成到脚本

```bash
#!/bin/bash
# check_invoice.sh

for file in invoices/*.pdf; do
    echo "Processing $file..."
    result=$(ocr-cli extract "$file" --type invoice -o -)

    status=$(echo "$result" | jq -r '.status')
    if [ "$status" = "completed" ]; then
        amount=$(echo "$result" | jq -r '.structured_data.total_amount')
        echo "  Amount: $amount"
    else
        echo "  Failed to process"
    fi
done
```
