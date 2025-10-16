# 自动生成增强数据集说明

## 功能概述

`run-go-evaluation.yml` 工作流现在会自动生成包含 `FAIL_TO_PASS` 和 `PASS_TO_PASS` 字段的增强数据集。

## 工作流程

1. **运行 Pre-patch 测试**
   - 执行原始代码（未打补丁）的测试
   - 记录所有测试的通过/失败状态
   - 保存日志到备份目录

2. **运行 Post-patch 测试**
   - 应用 gold patch（正确的修复补丁）
   - 执行修复后的测试
   - 记录所有测试的通过/失败状态

3. **自动提取测试分类**
   - 对比 pre-patch 和 post-patch 的测试结果
   - **FAIL_TO_PASS**: 修复前失败、修复后通过的测试（验证修复的有效性）
   - **PASS_TO_PASS**: 修复前后都通过的测试（验证没有破坏现有功能）

4. **生成增强数据集**
   - 将提取的 FAIL_TO_PASS 和 PASS_TO_PASS 字段添加到原始任务数据中
   - 保存为 JSONL 格式（与 SWE-bench 格式兼容）
   - 作为 artifact 上传，可供下载

## 输出文件

运行完成后，会生成 3 个 artifacts：

1. **logs-{instance_id}-none**
   - Pre-patch 的完整日志
   - 包含测试输出、报告等

2. **logs-{instance_id}-gold**
   - Post-patch 的完整日志
   - 包含测试输出、报告等

3. **enriched-dataset-{instance_id}** ⭐
   - 增强版的任务数据文件
   - 包含原始数据 + FAIL_TO_PASS + PASS_TO_PASS

## 增强数据集格式示例

```jsonl
{
  "repo": "json-iterator/go",
  "instance_id": "json-iterator__go-128",
  "base_commit": "845d8438db34cc782608bbee7647a522b4e87de0",
  "patch": "...",
  "test_patch": "...",
  "problem_statement": "...",
  "FAIL_TO_PASS": [
    "Test_iterator_use_number"
  ],
  "PASS_TO_PASS": [
    "Test_bad_case",
    "Test_iterator_without_number"
  ]
}
```

## 使用方法

### 方式 1：通过 GitHub Action 下载

1. 进入 GitHub Actions 页面
2. 找到对应的运行记录
3. 在 Artifacts 区域下载 `enriched-dataset-{instance_id}`
4. 解压后获得增强版的 JSONL 文件

### 方式 2：批量处理

如果你有多个任务需要处理，可以：

1. 修改工作流文件中的 `TASK_FILE_PATH`，指向包含多个任务的文件
2. 或者创建一个循环运行多个任务的工作流
3. 收集所有生成的增强数据集，合并成一个完整的数据集文件

## 注意事项

- 确保原始任务文件包含 `patch` 和 `test_patch` 字段
- Go 测试命令需要在 `swebench/harness/constants/go.py` 中正确配置
- 工作流使用测试输出中的 `--- PASS:` 和 `--- FAIL:` 标记来识别测试结果

## 故障排查

### 如果 FAIL_TO_PASS 和 PASS_TO_PASS 为空

1. 检查 `logs_backup` 和 `logs` 目录是否正确创建
2. 检查测试输出文件是否存在
3. 检查测试输出格式是否符合 Go test 的标准格式（`--- PASS:` / `--- FAIL:`）

### 如果某些测试没有被识别

- Go 的子测试（带 `/` 的测试名）会被正确处理
- 确保 test_cmd 在 constants/go.py 中正确配置，只运行相关测试

