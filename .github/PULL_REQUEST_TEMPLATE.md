---
name: Pull Request
about: Submit a pull request / 提交代码变更
title: ''
labels: ''
assignees: ''
---

## 变更类型 (Type of Change)

- [ ] feat: 新功能
- [ ] fix: Bug 修复
- [ ] refactor: 代码重构
- [ ] docs: 文档更新
- [ ] test: 测试相关
- [ ] chore: 构建/工具/依赖
- [ ] perf: 性能优化
- [ ] ci: CI/CD 配置

## 关联 Issue (Related Issues)

请关联相关的 Issue（如适用）：Closes #...

## 变更描述 (Description)

请清晰简洁地描述这次变更的内容和原因。

## 测试计划 (Test Plan)

- [ ] 手动测试了功能正常
- [ ] 在暗色和亮色主题下测试过
- [ ] 在正常/最大化/全屏窗口下测试过布局
- [ ] `cd test/ && python -m unittest discover -v` 全部通过

## Checklist

- [ ] 代码语法已检查（`python -m py_compile`）
- [ ] 未引入新的硬编码颜色值（使用 `Theme.*` 常量）
- [ ] 信息性文本使用 `SelectableLabel` 替代 `QLabel`
- [ ] 异常处理符合项目规范
- [ ] 如添加新插件，已更新 `toolbox.spec` 的 `hiddenimports`
- [ ] 运行了 `verify_packaging.py`（如涉及打包）