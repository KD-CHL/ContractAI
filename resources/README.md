# 演示资源

本目录只包含用于开发、测试和产品演示的合成规则与知识条目，不代表任何司法辖区的法律意见，也不能替代执业律师审阅。

- `demo_risk_rules.json`：确定性风险命中规则。每条规则都有稳定 ID、版本、触发依据和 `knowledge_refs`。
- `demo_knowledge_base.json`：规则所引用的合成知识条目。每条记录保留来源类型、版本、时间戳和内容摘要，便于从风险结论回溯到演示依据。

资源之间的目标追溯路径为：`rule_id -> knowledge_refs[] -> knowledge_id -> provenance`。基础服务会自动加载 `demo_knowledge_base.json`（可用 `CONTRACT_GUARD_KNOWLEDGE_PATH` 替换）；`demo_risk_rules.json` 是规则发布格式示例，当前默认扫描器仍使用代码内置规则，不会自动加载该文件。生产环境应换成经法务批准、受版本控制且具有适用法域和生效日期的真实知识库与规则发布流程，并保留审批记录。
