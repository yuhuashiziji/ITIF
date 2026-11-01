> 新增 PHP 8.5 公网部署方案，见 [PHP 虚拟主机部署](HOSTING-PHP.md)。以下本地 Python 服务说明仍适用于开发运行；不要把它直接绑定公网。

# 发布 ITIF 信息台到 GitHub

## 使用已经清理的源码包

1. 解压 `itif-source.zip`，进入其中 `itif` 文件夹。
2. 在本机执行 `python -m unittest discover -s tests`，再运行 `python server/app.py` 验证。
3. 在GitHub创建空仓库，推荐名称 `itif`，描述：中文优先的开源新闻、RSS与行情聚合信息台。
4. 上传itif文件夹中的所有内容到仓库根目录。使用Git提交能确保`.github`与`.gitignore`一起上传：

```bash
git init
git add .
git commit -m "Initial release of ITIF"
git branch -M main
# 将下一行的YOUR_ACCOUNT替换为你的GitHub账号
git remote add origin https://github.com/YOUR_ACCOUNT/itif.git
git push -u origin main
```

上面的仓库地址是示例，不代表已创建仓库。发布包未替你推送、设置DNS或配置ITIF.CN。品牌全称：Information · Technology · Insights · Finance（资讯·科技·洞察·财经）；中文名ITIF信息台。

## 包含的文件

入口HTML、server源码/前端资源/公共来源配置、config.example.json、tests、周刊与模板、README、MIT许可证、贡献说明、设计文档、隐私和参考说明、CI与Issue/PR模板、可重复打包工具，以及启动脚本。MANIFEST.json列出每个文件的SHA256。

原工程的个人config.json、server/data、日志、备份、抓取缓存/页面、历史方案、开发截图和临时文件均不在包内。历史快照数据不打包，开源版初次启动需实际抓取。

## GitHub 与网站托管的区别

[GitHub Pages](https://docs.github.com/en/pages/getting-started-with-github-pages/creating-a-github-pages-site)只托管静态网站，不能运行本项目Python调度、RSS、翻译和行情后台。本版不附带会误导使用者的Pages发布工作流。

仓库发布后，访客可以克隆并在自己的电脑运行。ITIF.CN作为在线网站需要另外选择能运行Python进程的主机；当前127.0.0.1服务尚未提供公网多人访问、认证、HTTPS和配置权限隔离。不要直接把它暴露到公网。

## 后续发布

在项目根执行 `python tools/package_release.py`，会在dist下生成新的干净源码ZIP。工具按白名单收录文件，并拒绝个人配置、缓存、日志、密钥和开发机器路径；不要从原工程目录整文件夹上传。更新版本记录后建立Git标签和Release即可。

许可为MIT，版权署名雨花石子记及ITIF contributors。它授权本项目原创软件，不授权第三方新闻或行情的再分发；来源不可用或免费翻译额度用尽不应自动改用付费服务。

## 公开作者信息

原创作者：雨花石子记。测试网址：[ITIF.CN](https://itif.cn)。作者说明见AUTHORS.md。
