# 为 Go 仓库生成 SWE-bench 数据

本指南全面概述了为 Go 仓库生成完整 SWE-bench 数据集所需的步骤。这包括收集任务实例（拉取请求）并对其进行评估，以生成 `patch`、`test_patch`、`fail_to_pass` 和 `pass_to_pass` 数据。

## 关键代码和目录

-   **`swebench/collect`**：包含用于从 GitHub 抓取拉取请求并将其转换为“任务实例”的脚本。主要脚本是 `get_tasks_pipeline.py`。
-   **`swebench/harness`**：包含评估框架。测试在此处的受控 Docker 环境中运行，以生成 `fail_to_pass` 和 `pass_to_pass` 结果。主要脚本是 `run_evaluation.py`。
-   **`swebench/harness/constants/go.py`**：**这是一个您需要修改的关键文件。** 它包含 Go 的特定配置，例如不同仓库和任务实例的安装和测试命令。
-   **`.github/workflows`**：包含 CI/CD 流水线。`gold-patch-evaluation.yml` 是一个用于自动化评估过程的有用参考。

---

## 第 1 部分：数据收集（创建任务实例）

第一步是从您的 Go 仓库中收集潜在的任务实例。任务实例本质上是解决特定问题的拉取请求。

### 步骤：

1.  **执行收集流水线：**
    `swebench/collect/get_tasks_pipeline.py` 脚本可自动执行获取 PR 并对其进行筛选的过程。您可以使用提供的 shell 脚本或直接运行它。

    您需要以 `owner/name` 的格式提供您的 GitHub 仓库。您还可以在 `swebench/collect` 目录中创建一个包含 `GITHUB_TOKENS=your_token` 的 `.env` 文件，以提供 GitHub 令牌来获取更高的 API 速率限制。

    ```bash
    cd swebench/collect
    python get_tasks_pipeline.py \
        --repos 'your-go-owner/your-go-repo' \
        --path_prs './prs' \
        --path_tasks './tasks'
    ```

2.  **理解输出：**
    此脚本将在 `tasks` 目录中生成两个主要文件：
    -   `your-go-repo-task-instances.jsonl.all`：包含所有具有关联问题和黄金补丁的有效任务实例。
    -   `your-go-repo-task-instances.jsonl`：`.all` 文件的子集，仅包含也具有关联测试的任务实例。这是您将用于评估的文件。

    JSONL 文件中的每一行代表一个任务实例，并包含 `instance_id`、`repo`、`base_commit` 和 `patch`（来自 PR 的代码更改）等信息。

---

## 第 2 部分：生成测试结果

这是流程中最关键且特定于语言的部分。要获取 `fail_to_pass` 和 `pass_to_pass` 数据，您必须在两种情况下在 SWE-bench 工具链中运行仓库中的测试：应用补丁之前（在 `base_commit` 上）和应用补丁之后。

### 步骤 1：为您的仓库配置评估工具链

评估工具链需要知道如何为您的特定 Go 项目和每个特定任务实例安装依赖项并运行测试。您必须将此配置添加到 `swebench/harness/constants/go.py`。

1.  **将任务实例文件添加到仓库：**
    将您通过上一个工作流生成的任务实例文件（例如 `gorm-task-instances.jsonl`）添加到您的项目根目录中。您需要将它提交到仓库，以便新的工作流可以访问它。

2.  **编辑 `swebench/harness/constants/go.py`：**
    打开此文件并为您的仓库添加一个新字典。键应为您的仓库的 `owner/name`，值将是一个将 `instance_id`（即 PR 编号）映射到其特定安装和测试命令的字典。

    **示例** (`go-gorm/gorm`):
    -   从您的 `.jsonl` 文件中获取 `instance_id` (PR 编号)。
    -   通过查看对应的 PR，找到需要运行的特定测试命令。

    ```python
    # 在 swebench/harness/constants/go.py 中

    # ... 现有的 SPECS 字典 ...

    SPECS_GORM = {
        # 用 gorm-task-instances.jsonl 文件中的 instance_id 替换
        "6850": {
            "docker_specs": {"go_version": "1.21"},
            "install": ["go mod tidy"],
            "test_cmd": ["go test -v -run TestCallbacks ./..."], # 用此 PR 的特定测试替换
        },
        "6835": {
            "docker_specs": {"go_version": "1.21"},
            "install": ["go mod tidy"],
            "test_cmd": ["go test -v -run TestTransaction ./..."], # 用此 PR 的特定测试替换
        },
        # 为每个任务实例添加更多条目
    }

    # 将您的新规范添加到主映射中
    MAP_REPO_VERSION_TO_SPECS_GO = {
        "caddyserver/caddy": SPECS_CADDY,
        # ... 其他仓库 ...
        "go-gorm/gorm": SPECS_GORM,
    }
    ```

3.  **编辑 `swebench/harness/log_parsers/go.py`:**
    确保 `go-gorm/gorm` 也被添加到了 `MAP_REPO_TO_PARSER_GO` 字典中，这样测试日志才能被正确解析。

    ```python
    # 在 swebench/harness/log_parsers/go.py 中
    MAP_REPO_TO_PARSER_GO = {
        # ... 其他仓库 ...
        "go-gorm/gorm": parse_log_gotest,
    }
    ```

### 步骤 2：使用 GitHub Actions 运行 pre-patch 和 post-patch 测试

为了确定哪些测试是从失败变为通过，您需要为每个任务实例运行两次评估：一次不应用补丁（pre-patch），一次应用黄金补丁（post-patch）。新创建的 `evaluate-swe-instance.yml` 工作流可以自动化此过程。

1.  **前往 GitHub Actions 页面** 并找到名为 "Evaluate SWE-bench Instance" 的新工作流。
2.  **运行 Pre-Patch 测试**:
    -   点击 "Run workflow"。
    -   **Repository name**: `go-gorm/gorm`
    -   **Instance ID**: 输入您想测试的 PR 编号 (例如, `6850`)。
    -   **Path to the task instances JSONL file**: 确保文件名与您提交到仓库的文件名一致 (例如, `gorm-task-instances.jsonl`)。
    -   **Patch type**: 选择 `none`。
    -   运行工作流。运行结束后，下载生成的 `logs-INSTANCE_ID-none` 工件。
3.  **运行 Post-Patch 测试**:
    -   再次点击 "Run workflow"。
    -   使用完全相同的参数，但这次将 **Patch type** 设置为 `gold`。
    -   运行工作流并下载 `logs-INSTANCE_ID-gold` 工件。

### 步骤 3：分析日志并构建最终数据集

现在您有了两个日志文件压缩包。解压它们，并在 `test_output.txt` 文件中查看测试结果。

1.  **分析 `none` (Pre-Patch) 日志**: 打开 `...-none` 日志中的 `test_output.txt`。找到所有 `--- FAIL` 的测试用例。这些是初始状态下失败的测试。
2.  **分析 `gold` (Post-Patch) 日志**: 打开 `...-gold` 日志中的 `test_output.txt`。找到所有 `--- PASS` 的测试用例。
3.  **确定 `fail_to_pass` 和 `pass_to_pass`**:
    -   **`fail_to_pass`**: 在 `none` 日志中失败，但在 `gold` 日志中通过的测试列表。
    -   **`pass_to_pass`**: 在 `none` 和 `gold` 日志中都通过的测试列表。
4.  **创建最终的 `.jsonl` 文件**:
    手动创建一个新的 `.jsonl` 文件。复制原始任务实例的 JSON 对象，并添加或填充 `fail_to_pass` 和 `pass_to_pass` 键，值为您在上一步中确定的测试用例名称列表。

对您 `gorm-task-instances.jsonl` 文件中的每一个任务实例重复以上步骤，即可创建出完整的 SWE-bench 评估数据集。

---

## 第 3 部分：使用 GitHub Actions 实现自动化

您可以使用 GitHub Actions 自动化整个数据生成流水线。

-   **现有工作流：**
    -   `pytest.yaml`：这用于测试 `swebench` 库本身，而不是用于数据生成。
    -   `gold-patch-evaluation.yml`：这是一个很好的模板。它展示了如何检出 SWE-bench 代码、设置环境并运行 `swebench.harness.run_evaluation` 脚本。它演示了评估工具链可在 CI 环境中运行。

-   **自动化策略：**
    您可以在 `.github/workflows` 中创建一个新的工作流文件，以自动化您仓库的流程。此工作流可以：
    1.  **按计划或手动触发运行。**
    2.  **运行收集步骤：** 执行 `get_tasks_pipeline.py` 以在您的 Go 仓库中查找新的、未处理的 PR。
    3.  **运行评估步骤：** 对于每个新任务实例，如第 2 部分所述，使用 `run_evaluation.py` 协调两次测试运行（补丁前和补丁后）。
    4.  **存储结果：** 将最终的、丰富的数据 `.jsonl` 文件提交回仓库或作为构建工件上传。

此设置将允许您在 Go 项目中合并新的拉取请求时，持续自动地构建您的 SWE-bench 数据集。

---

## 第 4 部分：替代测试环境

虽然 GitHub Actions 是运行评估的可行选项，但它可能会很慢，特别是对于许多任务。`swebench` 代码库内置了对更高效替代方案的支持。

-   **本地 Docker（默认）：**
    您可以直接在本地计算机上运行 `run_evaluation.py`。它将使用 Docker 为每次测试运行创建隔离的环境。这非常适合调试、开发和较小规模的数据生成。

-   **Modal（推荐用于大规模）：**
    该项目与 [Modal](https://modal.com/)（一个用于在云中运行容器的无服务器平台）直接集成。您会注意到 `run_evaluation.py` 中的 `--modal` 标志和 `swebench/harness/modal_eval` 目录。
    -   **优势：** Modal 允许大规模并行化。您可以在云中同时运行数百个测试评估，而无需管理任何基础架构。这比使用 GitHub Actions 运行器处理大型数据集要快得多，也更具可扩展性。
    -   **工作原理：** 当您使用 `--modal` 标志时，脚本会将每次测试运行的执行卸载到 Modal 平台上的一个单独的、按需的容器中。

-   **其他 CI/CD 平台：**
    任何可以运行 Docker 容器的 CI/CD 平台（如 Jenkins、CircleCI 或 GitLab CI）都可以用于执行评估脚本，类似于 GitHub Actions 的方法。

对于您的用例，首先使用本地 Docker 处理几个任务以确保您的配置正确是一个很好的第一步。对于生成大型数据集，花时间设置 Modal 将提供最佳性能。
