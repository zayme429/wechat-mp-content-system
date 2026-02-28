# 多用户个性化文章系统架构设计

## 需求背景

不同用户有不同的内容需求：
- **保险代理人**：需要保险客户经营、保险获客类文章，避免技术术语
- **科技从业者**：需要AI工具、数字化转型类文章，可以接受技术概念
- **其他行业**：各有不同的专业领域和受众

## 架构方案

### 1. 用户分层

```
用户层
├── 保险行业用户
│   ├── 保险代理人（主要受众）
│   ├── 保险团队长
│   └── 保险内容运营
├── 科技行业用户
│   ├── 产品经理
│   ├── 技术从业者
│   └── 企业管理者
└── 其他行业用户
    └── 可配置自定义偏好
```

### 2. 数据隔离方案

**方案A：按用户隔离（推荐）**
- 每个用户有自己的文章库视图
- 用户只能看到自己的文章
- 适合多人共用系统

**方案B：按领域隔离（当前采用）**
- 不同领域文章分类存储
- 用户选择关注的领域
- 同一领域文章共享
- 适合同领域团队协作

### 3. 用户配置模型

```python
user_profile = {
    "user_id": "唯一标识",
    "name": "用户名称",
    "industry": "行业 (insurance/tech/finance/...)",
    "role": "角色 (agent/manager/creator)",
    "preferences": {
        "primary_topic": "主要主题",
        "content_style": "内容风格",
        "avoid_technical": "是否避免技术术语",
        "target_audience": "目标读者",
        "forbidden_words": ["禁用词汇列表"],
        "preferred_words": ["推荐用词列表"]
    }
}
```

### 4. 生成策略差异化

**保险行业生成策略**：
```
主题：保险客户经营（给客户看的）
├── 故事案例派 - 客户信任建立故事
├── 话术实战派 - 可直接用的话术模板
├── 情感连接派 - 关系维护技巧
├── 转介绍技巧派 - 老客户带新客户
└── 服务差异化派 - 用服务赢客户

主题：保险获客（给代理人看的）
├── 社群经营派 - 微信群运营方法
├── 缘故激活派 - 激活亲戚朋友
├── 观念教育派 - 教育客户保险意识
├── 问题解决派 - 应对客户拒绝
└── 长期主义派 - 持续经营心态
```

**科技行业生成策略**：
```
主题：AI工具应用
├── 深度分析派 - 技术原理解读
├── 实战教程派 - 操作步骤详解
├── 工具测评派 - 产品对比评测
├── 效率提升派 - 工作流优化
└── 趋势预测派 - 行业发展前瞻
```

### 5. 实施计划

#### Phase 1：用户识别（已完成）
- [x] 创建用户偏好管理模块
- [x] 支持用户画像配置
- [x] 支持行业专属生成策略

#### Phase 2：内容隔离（待实施）
- [ ] Web界面增加用户选择
- [ ] 文章库按用户/领域筛选显示
- [ ] 生成文章时关联用户ID

#### Phase 3：个性化优化（待实施）
- [ ] 学习用户偏好（从审核历史）
- [ ] 推荐相似文章
- [ ] 生成策略动态调整

## 当前配置

### 保险用户默认配置
```json
{
  "industry": "insurance",
  "role": "agent",
  "target_audience": "保险代理人（保险业务员）",
  "avoid_technical": true,
  "primary_topic": "保险客户经营",
  "secondary_topic": "保险获客",
  "forbidden_words": [
    "数字化", "SaaS", "CRM", "私域流量", "数据中台",
    "算法", "API", "接口", "部署", "架构"
  ],
  "preferred_words": [
    "跟进", "回访", "约访", "促成", "缘故客户",
    "转介绍", "保单", "保障", "理赔", "服务"
  ]
}
```

## 使用方法

### 1. 创建保险用户
```python
from article_library.user_manager import create_insurance_user

create_insurance_user(
    user_id='agent_zhang',
    name='张代理人',
    email='zhang@example.com'
)
```

### 2. 获取用户配置生成文章
```python
from article_library.user_manager import get_user_config
from article_library.insurance_generator import InsuranceArticleGenerator

# 获取用户配置
config = get_user_config('agent_zhang')

# 根据配置生成文章
gen = InsuranceArticleGenerator()
articles = gen.generate_insurance_articles(
    topic=config['focus_areas'][0],
    count=5
)
```

### 3. Web界面选择用户
访问 `http://154.9.252.35:8080/library?user=agent_zhang`
只显示该用户的文章和偏好主题。

## 后续优化方向

1. **用户自助配置**：Web界面让用户自己设置偏好
2. **审核反馈学习**：根据用户审核历史优化生成策略
3. **文章推荐**：基于用户偏好推荐已有文章
4. **A/B测试**：对比不同生成策略的效果
