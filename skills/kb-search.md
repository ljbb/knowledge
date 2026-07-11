---
name: kb-search
description: 在 DevOps & Infra 知识库中搜索知识
type: meta
---

# 知识库搜索

## 触发条件
当用户询问 DevOps、Infra、运维、自动化、Harbor 相关问题时。

## 执行流程
1. 分析用户意图，提取搜索关键词
2. 调用搜索：
   ```bash
   python kb.py search "<关键词>" --category <可选分类>
   ```
3. Engine 返回匹配结果列表（id、title、摘要、匹配度）
4. 向用户展示候选项，确认需要的知识
5. 加载对应知识 Skill，展开完整操作指引

## 可用分类
- infra-daily: Infra 日常操作
- infra-violation: Infra violation 修复
- automation: 自动化
- harbor: Harbor 平台
