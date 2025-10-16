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

### 关键先决条件：配置您的仓库

评估工具链需要知道如何为您的特定 Go 项目和每个特定任务实例安装依赖项并运行测试。您必须将此配置添加到 `swebench/harness/constants/go.py`。

1.  **编辑 `swebench/harness/constants/go.py`：**

    打开此文件并为您的仓库添加一个新字典。键应为您的仓库的 `owner/name`，值将是一个将 `instance_id`（即 PR 编号）映射到其特定安装和测试命令的字典。

    **示例：** 假设您的仓库是 `my-org/my-app`，并且您正在从 PR `#123` 创建一个任务。您将添加如下条目：

    ```python
    # 在 swebench/harness/constants/go.py 中
    
    # ... 现有的 SPECS 字典 ...
    
    SPECS_MY_APP = {
        "123": {
            "docker_specs": {"go_version": "1.23.8"}, # 指定所需的 Go 版本
            "install": ["go mod download"],          # 安装依赖项的命令
            "test_cmd": ["go test -v ./... -run TestSpecificFeature"], # 运行相关测试的确切命令
        },
        # ... 来自您仓库的其他 PR ...
    }
    
    # 将您的新规范添加到主映射中
    MAP_REPO_VERSION_TO_SPECS_GO = {
        "caddyserver/caddy": SPECS_CADDY,
        # ... 其他仓库 ...
        "my-org/my-app": SPECS_MY_APP, # 在此处添加您的仓库
    }
    
    # 如果测试输出非标准，您可能还需要添加日志解析器
    # 但对于 `go test`，现有的 `parse_log_gotest` 应该可以工作。
    ```

### 生成测试数据的步骤：

要全面了解测试结果，您需要在 `base_commit` 上使用和不使用补丁的情况下运行评估工具链。然后将这两次运行的结果结合起来，以确定哪些测试在补丁前失败但在补丁后通过（`fail_to_pass`），以及哪些测试在两种情况下都通过（`pass_to_pass`）。工具链尚无自动执行此操作的单个命令，因此您需要创建一个脚本来协调这些运行。

单个任务实例的一般流程是：

1.  **在 `base_commit` 上运行测试（补丁前）：** 执行 `run_evaluation.py` 而不应用任何补丁，以确定测试的初始状态。这将告诉您哪些测试失败了。
2.  **使用黄金补丁运行测试（补丁后）：** 再次执行 `run_evaluation.py`，但这次提供您收集的任务实例中的 `patch`。这将显示修复后哪些测试通过了。
3.  **合并结果：** 比较两次运行的结果，以填充最终数据集实例的 `fail_to_pass` 和 `pass_to_pass` 字段。

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
