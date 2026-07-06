# 贡献指南 (Contributing Guide)

欢迎贡献！请花几分钟阅读以下指南，让协作更顺畅。

## 目录

- [行为准则](#行为准则)
- [开发环境](#开发环境)
- [如何贡献](#如何贡献)
- [分支策略](#分支策略)
- [提交规范](#提交规范)
- [代码规范](#代码规范)
- [测试](#测试)
- [Issue 报告](#issue-报告)
- [Pull Request 流程](#pull-request-流程)

---

## 行为准则

本项目已采用 [Contributor Covenant](CODE_OF_CONDUCT.md) 作为行为准则，所有贡献者都应遵守。

## 开发环境

```bash
# 克隆仓库
git clone https://github.com/yansheng836/python-toolbox.git
cd python-toolbox

# 安装依赖
pip install -r requirements.txt

# 运行应用
python main.py

# 运行测试
cd test/ && python -m unittest discover -v
```

## 如何贡献

### 🐛 报告 Bug

1. 先搜索 [Issues](https://github.com/yansheng836/python-toolbox/issues) 确认是否已有相同报告
2. 使用 Bug Report 模板提交 Issue

### 💡 功能建议

1. 先搜索 Issues 确认是否已有类似建议
2. 使用 Feature Request 模板提交 Issue

### 🔧 提交代码

请遵循以下开发流程：

1. **Research** — 先在 GitHub 搜索已有的实现模式，避免重复造轮子
2. **Plan** — 复杂功能先创建 Issue 讨论方案
3. **Implement** — 遵循 [TDD](https://en.wikipedia.org/wiki/Test-driven_development) 实践
4. **PR** — 创建 Pull Request（参考下方 PR 流程）

## 分支策略

- `main` — 稳定分支，始终可部署
- `feat/*` — 功能开发分支（如 `feat/add-webp-support`）
- `fix/*` — Bug 修复分支（如 `fix/crash-on-empty-list`）

```bash
git checkout -b feat/my-feature
# ... 开发 ...
git commit
git push -u origin feat/my-feature
# 创建 Pull Request → main
```

## 提交规范

提交信息格式：

```
<type>: <中文描述>

<可选正文>
```

| Type | 说明 |
|------|------|
| `feat` | 新功能 |
| `fix` | Bug 修复 |
| `refactor` | 重构 |
| `docs` | 文档更新 |
| `test` | 测试相关 |
| `chore` | 构建/工具/依赖 |
| `perf` | 性能优化 |
| `ci` | CI/CD 配置 |

示例：

```
feat: 新增图片缩放百分比模式
fix: 修复空文件列表导致崩溃的问题
docs: 更新 README 安装说明
```

## 代码规范

### Python

- UTF-8 编码，LF (`\n`) 行尾
- 遵循 PEP 8 风格
- 模块级 docstring 说明用途
- 异常处理：只在有意义的地方捕获，必须报告错误信息

### PyQt6

- **颜色** — 使用 `Theme` 常量，禁止硬编码颜色值
- **文本** — 用户可复制的信息使用 `SelectableLabel` 替代 `QLabel`
- **布局** — 响应式布局，不使用 `addStretch()` 在布局末尾
- **主题** — 所有插件必须实现 `update_theme()`，在暗色和亮色主题下测试

### 代码复用

相同或相似代码出现 2 次以上，必须抽象为共享组件。共享组件位于：

- `common/` — 通用辅助类和函数
- `toolbox.py` 中的 `ToolPlugin`、`Theme`、`Card` 等基础类

### 语法检查

修改 Python 文件后必须运行：

```bash
python -m py_compile <file.py>
```

## 测试

测试文件位于 `test/` 目录，以 `test_` 前缀命名。

```bash
cd test/ && python -m unittest discover -v
```

添加功能时请创建对应的测试文件。

## Issue 报告

- 请使用 Issue 模板创建
- Bug 报告需包含：复现步骤、期望行为、实际行为、运行环境
- 功能建议需说明：使用场景、预期效果

## Pull Request 流程

1. **Fork** 本仓库并创建功能分支
2. **编写测试** — 先写测试，再实现功能
3. **实现功能** — 确保所有测试通过
4. **代码审查** — 对照 [CLAUDE.md](CLAUDE.md) 检查规范
5. **运行测试** — 确保不破坏现有功能
6. **语法检查** — `python -m py_compile`
7. **提交 PR** — 使用 PR 模板填写描述

### PR Checklist

- [ ] 代码语法已检查（`python -m py_compile`）
- [ ] 所有测试通过
- [ ] 在暗色和亮色主题下测试过
- [ ] 响应式布局正常
- [ ] 未引入新的硬编码颜色值
- [ ] 异常处理符合规范
- [ ] 如添加新插件，已更新 `toolbox.spec` 的 `hiddenimports`

---

再次感谢你的贡献！ 🙏
