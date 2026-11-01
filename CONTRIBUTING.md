# 参与贡献

## 新增来源

编辑 server/sources.json，提供唯一 id、名称、公开 RSS 地址、类别、语言、权重、刷新间隔（最少 300 秒）、enabled、kind 和署名要求。运行 python server/validate_sources.py 验证。界面修改保存为本机覆盖配置。不得提交个人配置、缓存、Cookie 或密钥。

## 每周精选

使用 GitHub 的推荐文章或工具 Issue 模板投稿。维护者核查链接和推荐理由，将条目写入 content/weekly/YYYY-Www.md，见 TEMPLATE.md。提交 PR，审阅合并后自动展示 published 条目；draft 不展示。未发布 GitHub 前可直接提交 Markdown 文件。

## 验证

python -m unittest discover -s tests

规则分组不等于事实核查，不支持跨语言语义匹配。
