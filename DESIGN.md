# ITIF 信息台界面规范

## 方向
中文信息编辑台：每天打开先找来源与标题，再决定是否深入阅读。真实数据、原文链接、语言和更新时间构成界面主体。使用 design-taste-frontend 的 app screen 流程；方向为 Accent ladder（seed 254512264）。保留已有顶部三条主路由和中文系统字体，避免额外字体下载。主色由抽取方案的覆盆子色调整为本站朱红色。

## 视觉参考与采用范围
- [Awwwards 编辑类案例](https://www.awwwards.com/websites/magazine-newspaper-blog/)：编辑网格、明确标题层级、安静导航。
- [North East 参考图](https://www.awwwards.com/inspiration/north-east)：克制用色和内容分区；未复制图片或布局。
- [Mouthwash 案例](https://www.awwwards.com/sites/mouthwash)：清晰的刊头与编辑节奏；本站采用自己的双页线稿标记。
- [Webby 动效评审说明](https://winners.webbyawards.com/2026/websites-and-mobile-sites/features-design/best-use-of-animation-or-motion-graphics/362474/scorching-cells)：动效服务使用体验。本站仅用操作反馈和抽屉进入动效。

这些是方向参考，并不代表本站获得奖项或达到评审认证。参考图不作为产品资源打包。新闻聚合工具没有添加营销首屏、装饰照片或滚动劫持。ui-ux-pro-max-skill 在当前可用技能目录中未找到，本次未声称使用它。

## 基础规范
- 背景 #f3f4f4，面板白色，正文 #172122，辅助文字 #626e70；朱红 #b73537 用于排序、选中状态与上涨数据，绿色表示下跌。涨跌保留正负号。
- 字体 Segoe UI / PingFang SC / Microsoft YaHei / sans-serif；主标题32，来源16，新闻14，正文15，元数据11–12px。手机新闻15px。行情数字使用 tabular-nums。
- 内容最大宽1600px；桌面40px边距、卡片20px间距、侧栏248px；平板28px边距，手机16px。
- 面板8px圆角、1px边框，不使用静止投影；抽屉作为浮层保留阴影。
- 桌面3列来源，1200px以下2列，600px以下1列；980px以下侧栏进入内容下方。手机分类和阅读导航单行滑动，搜索框单独一行。
- 首页默认显示每来源5条，最多两行标题，支持展开全文列表。历史快照和抓取失败均保留标签。中文排序规则由 reader.js 控制。
- 桌面收藏/翻译在悬停及键盘聚焦时出现；已收藏与手机持续显示。键盘焦点明确，收藏按钮具有文章名和 aria-pressed。
- 状态与次要推荐默认收起；RSS 使用原生 dialog，支持关闭按钮和 Escape，保留焦点管理。
- 微交互120–220ms；prefers-reduced-motion 下关闭过渡与动画。刷新忙碌状态绑定真实请求。

## 实现入口
- 每日聚合站_融合版.html：引用设计层、首页列表长度和搜索空结果。
- server/design.css：设计令牌与各路由样式、响应式与减少动画。
- server/design.js：刊头、原创标记、真实工作台热榜、阅读说明、侧栏折叠。
- server/live.js：真实刷新状态、来源状态排序。
- server/reader.js：收藏可访问名称、翻译按钮可访问名称。
- server/app.py：提供 /design.css 与 /design.js。

## 验证与边界
已在真实浏览器检查1440、768、390px，首页31个来源；检查暗色、搜索无结果、收藏加入与取消、RSS抽屉展开/关闭、来源表单和工作台行情。测试收藏已取消；主题恢复亮色，视窗恢复默认。

22项现有后端测试通过，三个脚本 node --check 通过。设计层 lint 为0 FAIL、1 WARN；警告是有意保留的抽屉浮层阴影。技能 CDP 自动 inspector 启动失败（Page.enable超时），因此不能将本次结果描述为完整 inspector 通过；用真实浏览器截图和DOM边界检查补验。未进行人工屏幕阅读器全流程或多品牌实体手机验证。

免费数据源仍可能超时；微信、搜狗历史快照不是当天新闻。财经日历和GitHub趋势仍是已有演示组件，已明确标记，未当成实时数据宣传。

## 0.1.0 页内翻译与命名

品牌为ITIF信息台：Information · Technology · Insights · Finance，域名标识ITIF.CN。原Google外链翻译已删除，改用中英/原文菜单及MyMemory或自建LibreTranslate，不改变文章URL。翻译只处理可见的公开页面文本，动态内容在滚动及重绘后按需翻译；恢复原文立即生效。来源名、输入/配置/代码区保留原样，长文本和失败保留原文。相关实现见server/translate.js和translation.py。
