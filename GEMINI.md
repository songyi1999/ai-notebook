Always respond in 中文
1.修改时注意不能影响现有的功能。非必要不删除代码。
2.不要删除注释。
3.每个功能模块有详细的注释。重要的代码行使用单行注释。
4. 重点：不要随意修改现有的代码，除非明确让你修改或会引发冲突，错误。
5. 不要随意替换原来的功能，需要仔细看过原来的实现理解了逻辑才能修改。
6. 开发时提供的技术解决方案务必尽量简洁。
7. 打印详细日志，包含运行时间，行数，调用的函数名称，类名，文件名，方便排查错误。
8.把项目涉及到的类，函数，的功能描述，调用传入参数传出参数，保存在哪个文件，统一保存在 readme.md 的函数列表项中，方便统一查看，避免建立重复和冲突的类。
9.把项目中涉及到的全局和环境变量，统一保存在 readme.md 的变量说明项中，避免产生重复或冲突的类。
10. 每次更新或创建，删除 函数或变量时，都要维护 readme.md

11.

功能完备性测试要求：
对前端，后端，及 dataset 数据提取，都需要维护一个测试列表。对实现的功能写测试脚本，确保功能都可用。当做任何修改或新增时，都需要 1 维护测试用例：新增新功能测试用例，去除已移除的功能测试用例，修改修改的功能测试用例。  2.测试所有的测试用例，确保修改不会引入新的异常。
python 请使用 pytest，对于 FastAPI，官方推荐的 TestClient (基于 httpx) 结合 pytest ，前端测试分为组件测试和端到端测试。

组件测试: Jest + React Testing Library (RTL)，专注于单个组件的渲染和交互。
端到端测试: Cypress 或 Playwright，模拟真实用户在浏览器中的完整操作流程。
总结与执行流程
建立测试脚本: 在每个模块下（Dataset, backend, frontend）创建 tests 目录，并按照上述建议编写测试用例。

创建总控脚本: 在项目根目录下创建一个 run_all_tests.sh 脚本。

12 配置要统一：
本地测试时的配置要和 docker-compose 配置要兼容，不能互相矛盾，导致测试正常但是部署又出错。

任何变量都要统一在一个地方配置不要到处都有配置文件，记得变量不能硬编码。

During you interaction with the user, if you find anything reusable in this project (e.g. version of a library, model name), especially about a fix to a mistake you made or a correction you received, you should take note in the `Lessons` section in the `.cursorrules` file so you will not make the same mistake again.
﻿
You should also use the `task.log` file as a scratchpad to organize your thoughts. Especially when you receive a new task, you should first review the content of the scratchpad, clear old different task if necessary, first explain the task, and plan the steps you need to take to complete the task. You can use todo markers to indicate the progress, e.g.
[X] Task 1
[ ] Task 2
Also update the progress of the task in the Scratchpad when you finish a subtask.
Especially when you finished a milestone, it will help to improve your depth of task accomplishment to use the scratchpad to reflect and plan.
The goal is to help you maintain a big picture as well as the progress of the task. Always refer to the Scratchpad when you plan the next step.

You are an agent - please keep going until the user’s query is completely resolved, before ending your turn and yielding back to the user. Only terminate your turn when you are sure that the problem is solved.

If you are not sure about file content or codebase structure pertaining to the user’s request, use your tools to read files and gather the relevant information: do NOT guess or make up an answer.

You MUST plan extensively before each function call, and reflect extensively on the outcomes of the previous function calls. DO NOT do this entire process by making function calls only, as this can impair your ability to solve the problem and think insightfully.

始终查看 README.md 记录项目最新情况。
持续更新和维护 README.md 文件。
项目中的数据库结构、字段、请在 DATABASE.md 中更新和维护。

任何逻辑的编写和修改，始终参考 DATABASE.md.

记得最小优化原则，每次紧紧围绕主题，仅修改必要限度的代码，不需要优化和修改与当前任务无关代码。
尽量使用最简洁的方案解决问题，不要炫技。
- Only modify code directly relevant to the specific request. Avoid changing unrelated functionality.
- Never replace code with placeholders like `// ... rest of the processing ...`. Always include complete code.
- Break problems into smaller steps. Think through each step separately before implementing.
- Always provide a complete PLAN with REASONING based on evidence from code and logs before making changes.
- Explain your OBSERVATIONS clearly, then provide REASONING to identify the exact issue. Add console logs when needed to gather more information.
代码行数越少越好（减少冗余代码）

像10倍效率的资深开发者一样处理。

在完全实现功能前不要停止。
修改代码修复错误前先写三段推理段落再开始修改代码。

每个文件顶部注释完整路径。

每3~4行代码需加1行注释，解释非直观逻辑。

新功能开发前进行逻辑解释并需要确认。

在修复问题时仅仅修改与问题直接相关的代码，并且必须解释推理过程。

必须提供基于代码证据的完整修改计划后再动手。

先说明观察结论再动手。

配置文件应该包含项目技术概览：功能描述，核心文件，关键算法等。

# 开发规范与标准

## 基本原则

1. **最小优化原则**：每次仅围绕主题，仅修改必要限度的代码，不需要优化和修改与当前任务无关代码
2. **功能保护**：修改时注意不能影响现有的功能，非必要不删除代码
3. **注释保护**：不要删除注释，每个功能模块有详细的注释，重要的代码行使用单行注释
4. **谨慎修改**：不要随意修改现有的代码，除非明确让你修改或会引发冲突、错误
5. **理解优先**：不要随意替换原来的功能，需要仔细看过原来的实现理解了逻辑才能修改
6. **方案简洁**：开发时提供的技术解决方案务必尽量简洁

## 日志规范

打印详细日志，包含：
- 运行时间
- 行数
- 调用的函数名称
- 类名
- 文件名
- 方便排查错误的详细信息

## 文档维护要求

### README.md 维护
把项目涉及到的类、函数的功能描述、调用传入参数传出参数、保存在哪个文件，统一保存在 [README.md](mdc:README.md) 的函数列表项中，方便统一查看，避免建立重复和冲突的类。

把项目中涉及到的全局和环境变量，统一保存在 [README.md](mdc:README.md) 的变量说明项中，避免产生重复或冲突的类。

每次更新或创建、删除函数或变量时，都要维护 README.md。

### DATABASE.md 维护
任何逻辑的编写和修改，始终参考 [DATABASE.md](mdc:DATABASE.md)。

项目中的数据库结构、字段、请在 [DATABASE.md](mdc:DATABASE.md) 中更新和维护。

## 测试要求

### 功能完备性测试
对前端、后端、及 dataset 数据提取，都需要维护一个测试列表。对实现的功能写测试脚本，确保功能都可用。

当做任何修改或新增时，都需要：
1. **维护测试用例**：新增新功能测试用例，去除已移除的功能测试用例，修改修改的功能测试用例
2. **测试所有的测试用例**：确保修改不会引入新的异常

### 测试技术栈
- **Python**：使用 pytest
- **FastAPI**：官方推荐的 TestClient (基于 httpx) 结合 pytest
- **前端组件测试**：Jest + React Testing Library (RTL)，专注于单个组件的渲染和交互
- **端到端测试**：Cypress 或 Playwright，模拟真实用户在浏览器中的完整操作流程

### 测试脚本组织
在每个模块下（ backend, frontend）创建 tests 目录，并按照上述建议编写测试用例。

在项目根目录下创建一个 run_all_tests.sh 脚本作为总控脚本。

## 配置统一性

### 配置兼容性
本地测试时的配置要和 docker-compose 配置要兼容，不能互相矛盾，导致测试正常但是部署又出错。

### 变量管理
任何变量都要统一在一个地方配置，不要到处都有配置文件。

记住变量不能硬编码，都要通过环境变量或配置文件管理。

## 代码质量

### 重用性
在与用户交互过程中，如果发现项目中任何可重用的内容（例如库的版本、模型名称），特别是关于修复错误或收到的更正，应该在 `.cursorrules` 文件的 `Lessons` 部分记录，以免再次犯同样的错误。

### 进度跟踪
使用 [task.log]文件作为草稿本来组织思路。特别是当收到新任务时，应该：
1. 首先查看草稿本的内容
2. 如有必要，清除旧的不同任务
3. 首先解释任务，并计划完成任务需要采取的步骤
4. 可以使用 todo 标记来指示进度，例如 [X] Task 1、[ ] Task 2
5. 完成子任务时更新草稿本中的任务进度
6. 特别是当完成里程碑时，使用草稿本进行反思和规划会有助于提高任务完成的深度

目标是帮助维护大局观以及任务的进度。在规划下一步时始终参考草稿本。

