# 指南：批量拆分任务实例文件

本指南说明了如何使用 `select_instance.py` 脚本将一个包含多个 SWE-bench 任务实例的大型 `.jsonl` 文件拆分为多个独立的、每个实例一个的文件。

## 为何要批量拆分？

在运行初始数据收集后，您会得到一个包含所有潜在任务实例列表的单一文件（例如，`gorm-task-instances.jsonl`）。为了便于评估和分析，将每个任务实例放在各自的文件中通常更为方便。本脚本可自动化该过程。

## 如何使用

`select_instance.py` 脚本（已重命名以反映其新用途）接受一个源文件和一个输出目录作为输入。

### 命令

```bash
python swebench/collect/select_instance.py \
    --source_file [您的源文件路径] \
    --output_dir [您的输出目录路径]
```

### 参数

-   `--source_file`: 您想要拆分的 `.jsonl` 文件的路径。
    -   *示例*: `data-go/gorm/gorm-task-instances.jsonl`
-   `--output_dir`: 用于保存单个任务实例文件的目录路径。如果该目录不存在，脚本将创建它。
    -   *示例*: `data/tasks/gorm_instances`

### 使用示例

要将 `gorm-task-instances.jsonl` 文件拆分到一个名为 `gorm_instances` 的新目录中，您可以在项目根目录下运行以下命令：

```bash
python swebench/collect/select_instance.py \
    --source_file data-go/gorm/gorm-task-instances.jsonl \
    --output_dir data/tasks/gorm_instances
```

### 脚本功能

对于 `source_file` 中的每一行，脚本将执行以下操作：
1.  读取 JSON 对象。
2.  提取 `instance_id`。
3.  根据 `instance_id` 创建一个安全的文件名（例如，`go-gorm/gorm/6850` 会变成 `go-gorm_gorm_6850.jsonl`）。
4.  将该单个实例的 JSON 对象写入其在指定的 `output_dir` 中的新文件。

运行后，`output_dir` 目录将包含一组 `.jsonl` 文件，每个文件对应源文件中的一个任务实例。
