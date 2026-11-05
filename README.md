# ITIF 信息台

**Information · Technology · Insights · Finance**  
资讯 · 科技 · 洞察 · 财经

**汇聚中外资讯，看见科技与市场。** 原创作者：**雨花石子记** · 测试网址：[ITIF.CN](https://itif.cn)。

面向中文用户的免费开源资讯聚合工具：国内热榜、全球 RSS、规则精选、事件聚合、周刊与行情，点击标题直达来源。Python 3.10+ 后台（网页解析使用 Scrapling），原生 HTML/CSS/JavaScript 前端，无需 npm 构建，无数据库，无付费接口要求。

## PHP 虚拟主机部署

新增 PHP 8.5 公开浏览版：GitHub Actions 定时抓取，虚拟主机缓存展示，无数据库、无常驻进程。请使用 `itif-php85.zip`，详见 [部署指南](docs/HOSTING-PHP.md)。源码仓库：[yuhuashiziji/ITIF](https://github.com/yuhuashiziji/ITIF)。

## 本地快速启动

```bash
python -m pip install -r requirements.txt
python server/app.py
```

访问 <http://127.0.0.1:8765/#/home>。Windows 也可双击 `启动服务.cmd`。不要直接打开 HTML：抓取、翻译和行情依赖 Python 后台。首次运行没有缓存，等待来源逐步更新；个别来源失败不影响其他来源。关闭运行终端停止服务。

可选：复制 `server/config.example.json` 为 `server/config.json`，调整关注标的和订阅。页面来源管理的修改、已抓取内容与精选设置只保存本机，已被 `.gitignore` 排除。

## 功能

- 35个默认来源，中文优先；综合页优先微信、微博、头条、搜狗、历史上的今天、知乎。
- RSS/Atom、网站 feed 自动发现及 `rsshub://`；条件请求、独立调度、失败退避和聚合 `/rss.xml`。
- 置顶、已读、未读与收藏；这些阅读记录仅在浏览器 localStorage 中保存。
- 规则每日精选、相似标题事件分组、Markdown 周刊及来源启停/权重/刷新间隔。
- A股、美股、数字货币免费公开行情；更新时间、来源和失败状态可见。
- 页内“中文 / English / 原文”翻译，无跳转；后续滚动与刷新按需处理新内容。
- 桌面三列、平板双列、手机单列；RSS抽屉、暗色与减少动态效果支持。

## 免费数据与边界

RSS 来源见 `server/sources.json`。A股与美股优先腾讯公开行情，美股缺失时尝试 Yahoo Finance；币价优先 Binance 公共只读数据域名，备用 CoinGecko。USDT 不等同美元，涨跌口径以组件说明为准。行情仅供信息展示，不用于交易或保证实时性。

微博与历史上的今天使用60s公开实例，头条与知乎使用其公开接口。微信、搜狗暂无稳定免费实时榜单，预留来源并标记历史快照；源码包不附带抓取存档，首次启动可能为空。公共接口可能变更、延迟、限流或下线。软件许可证不赋予第三方新闻、行情或图像的再分发权。

财经日历和GitHub趋势为明确标注的演示组件。精选是可解释规则，事件分组是标题词项相似度，不代表人工核查或跨语言语义分析。默认不把英文内容自动改写。

## 页内翻译

点击右上角“中 / EN”，选择中文、English或原文。文字在本页替换，文章链接不变；恢复原文会取消等待并还原文本。选择语言后对可见内容翻译，滚动和站内重绘后继续。刷新整个浏览器页面后默认回到原文。

固定界面标签使用本地词典，动态文字通过本机 `/api/translate` 请求免费 MyMemory；每次最多500字节，按UTF-8拆分，带内存缓存。匿名额度为5000字符/天，按服务方当时规则执行；没有填邮箱、Cookie或密钥。失败/额度不足保留原文，可重新选择语言重试。[API文档](https://mymemory.translated.net/doc/spec.php) · [额度说明](https://mymemory.translated.net/doc/usagelimits.php)

点击翻译会向服务商发送当前可见的公开文本；输入框、配置表单、收藏内容及其侧栏副本、个人关键词说明和代码区不会发送。用户自定义来源默认标为本地私有，其标题和事件也跳过外部翻译。默认不开启，不加载第三方脚本。品牌、来源名和数字保留原样。仅支持中英互译；其他语种不保证正确识别。长于1600字符的单个文本块跳过，原文站点正文与第三方页面不在本站翻译范围内。

可以自建 [LibreTranslate](https://github.com/LibreTranslate/LibreTranslate)，下载中英模型后设置：

```powershell
# PowerShell；服务地址由本机管理员配置，非网页输入
$env:LIBRETRANSLATE_URL='http://127.0.0.1:5000'
python server/app.py
```

LibreTranslate 独立安装、独立许可，本项目不附带其镜像或模型。自建消耗本机资源，无须购买翻译API。默认MyMemory适合个人阅读，不是无限量商业翻译服务。

## 测试与发布

```bash
python -m unittest discover -s tests
node tests/test_frontend.js
python tools/package_release.py
```

JavaScript 使用 `node --check server/translate.js` 等作语法检查；Node不是运行网站的必需条件。GitHub Actions 在提交与PR时运行离线单元测试和脚本语法检查，不抓取新闻、不消耗翻译额度。

GitHub托管源码，GitHub Pages不能运行Python后台。当前服务只绑定127.0.0.1，并限制Host/Origin；Python 版是本地运行工具，不应直接修改绑定地址后开放。公网可使用独立的 PHP 公开浏览版，它关闭配置写入接口。见 [GitHub发布指南](docs/PUBLISHING.md)。

## 目录

- `server/`：抓取、调度、行情、编辑与翻译服务，以及前端脚本。
- `每日聚合站_融合版.html`：现有入口文件名，页面品牌为ITIF信息台。
- `content/weekly/`：可投稿的原创周刊与模板。
- `tests/`、`.github/`：测试与贡献流程。
- `docs/`、`DESIGN.md`：发布、隐私、参考来源和设计说明。

## 许可与贡献

本项目原创软件代码采用 [MIT](LICENSE) 许可。新闻、行情、第三方服务、字体和模型按各自条款处理。接口适配独立实现，设计/项目参考见 [致谢](docs/REFERENCES.md)。欢迎提交来源与修复，见 [CONTRIBUTING.md](CONTRIBUTING.md)。

公网RSS和行情抓取采用直连，并检查实际连接的对端IP，拒绝内网及回环地址；不会自动使用系统代理。由管理员配置的自建LibreTranslate是明确允许的本地服务例外。

## 网页采集升级

新增央视、界面、新华与第一财经的公开首页适配器，使用 Scrapling 提取并校验文章链接。平台热榜与网页精选明确区分，失败来源保留状态，不生成假新闻。见 [采集说明](docs/COLLECTION.md)。
