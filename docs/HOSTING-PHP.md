# PHP 8.5 虚拟主机部署

适用于 PHP/静态虚拟主机；不需要数据库、SSH、Python 或主机后台常驻进程。原创作者：雨花石子记。项目测试域名 ITIF.CN。

## 上传网站

1. 下载并解压 `itif-php85.zip`，上传解压后的全部文件到网站根目录。网站入口是 `index.php`；若根目录已有 `index.html`，主机可能优先打开旧页面，请先备份旧站并调整默认首页顺序为 index.php 优先。
2. 不要上传源码包替代部署包。部署包内无需再执行安装命令。
3. PHP 选择 8.5，启用 cURL、OpenSSL、JSON，允许网站目录写入。程序会创建 `runtime/` 缓存目录，不使用数据库。
4. 打开 `https://5o5o.com/index.php#/home`。检查 `https://5o5o.com/api.php?action=health`：应返回 `ok: true`。部署目录改变时，用对应路径访问这两个地址。
5. RSS 地址是 `api.php?action=rss`，支持根目录及子目录部署，无需伪静态规则。

为了避免覆盖原站，可先上传到主机允许的一个子目录，例如 `itif/`；若子目录额度已用完，使用根目录前先备份旧站。子目录地址为 `https://5o5o.com/itif/`。更新部署时保留主机端的 `config.php` 和 `runtime/`，上传其余文件。

## GitHub 自动更新

仓库：<https://github.com/yuhuashiziji/ITIF>。在 Actions 中选择 **Refresh public feeds → Run workflow** 执行首次抓取。默认 UTC 每小时 17、47 分尝试更新；北京时间同样为每小时 17、47 分。

工作流只读取 `server/sources.json` 与 `server/config.example.json`，写入 `public-data/snapshot.json`。不会读取本机配置、私人订阅、阅读记录或本地缓存。来源刷新间隔与失败退避仍然生效。公开仓库标准 GitHub 托管运行器通常免计费，配额与服务规则以 GitHub 当时政策为准。

主机每五分钟最多向 GitHub 检查一次，使用短连接超时、文件锁与原子缓存，适配进程数较少的虚拟主机。上游不可用时继续展示缓存或随包公开快照，并标示过期/失败。页面刷新按钮读取快照，不会强迫 GitHub 立即抓取。快照不是实时行情。

GitHub 定时任务可能排队、延迟，长期无仓库活动也可能自动停用；需要在 Actions 查看实际运行结果，不能保证无人维护永久运行。首次上传工作流后需先手动运行一次，之后观察定时运行。

若 Actions 日志提示写入权限不足，仓库管理员按 GitHub 提示允许本仓库工作流写入 contents；本工作流只提交一个公开数据文件，不需填写个人令牌或第三方付费 API 密钥。更换仓库时复制 `config.example.php` 为 `config.php`，修改 owner、repo、branch，不能填任意远程网址。

## 公网行为与隐私

公开站点仅允许浏览，不提供修改来源、精选规则或服务器配置的接口。来源启停和权重在仓库修改，经下一次工作流生效。收藏、已读和置顶仅存当前浏览器。

翻译在本页完成，不跳转；固定标签使用本地词典，公开标题通过 MyMemory 匿名接口按需翻译。免费额度按主机出口 IP 共享，本站默认保守限制为每日 4500 字符并缓存结果，不是无限量服务；其他站点共享同一个主机出口 IP 时仍可能提前耗尽服务方额度。失败保留原文。输入框、收藏和私有标记内容不外发。缓存只存公开翻译文本，不记录访客 IP、Cookie 或浏览历史。缓存文件有 PHP 执行保护，不依赖 Apache .htaccess。

主机必须正确执行 PHP，不能把 PHP 源码作为静态文件公开。若页面直接显示 PHP 代码，请先停止对外访问并检查 PHP 站点配置。HTTPS 证书校验始终开启。

软件开源许可不包含第三方新闻和行情的版权授权。默认只公开标题、来源、原文链接与必要时间/行情字段，不公开新闻正文。微信、搜狗没有稳定免费来源时展示不可用状态，不伪造实时内容。

## 本地重建

```bash
python tools/build_public_snapshot.py
python tools/package_php.py --output dist
```

不联网的构建检查可先执行 `python tools/build_public_snapshot.py --offline`，它明确生成空来源及等待抓取状态，不生成演示新闻。

故障排查：health 为 503 时检查文件完整性、runtime 写入权限；页面只有随包快照时检查 Actions 是否成功提交数据、raw.githubusercontent.com 是否可达；旧页面仍出现时清理浏览器缓存并明确打开 index.php。不要关闭 TLS 校验解决连接失败。
