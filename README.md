# geosite-dat-builder

基于 [v2fly/domain-list-community](https://github.com/v2fly/domain-list-community) 官方编译工具，
按 `config/rules.txt` 选定的分类编译 `geosite.dat`（xray / mihomo / Clash Meta 通用），
`cn` 分类可叠加 `config/cn-extra.txt` 自定义补充，并通过 **GitHub Actions 每次 commit 自动构建**。

## 目录结构

```
.
├── config/
│   ├── rules.txt            # 分类清单：<可选自定义源>: <geosite 分类名>
│   └── cn-extra.txt         # 追加进 geosite:cn 的自定义补充（v2fly data 语法）
├── tools/build_dlc.py       # 转换器：生成自定义分类 + dat_diy.json（CI 调用）
└── .github/workflows/build.yml  # 每次 commit 自动构建（唯一构建途径）
```

## 工作原理

1. `tools/build_dlc.py` 读取 `config/rules.txt` 的分类清单：右列为产物里的
   geosite 分类名；若左列同名源文件存在于 `config/`（如 `Apple.txt`），会解析并合入
   （`DOMAIN-SUFFIX→domain:`、`DOMAIN→full:`、`DOMAIN-KEYWORD→keyword:`、
   `DOMAIN-REGEX→regexp:`，裸域名默认 `domain:`，`IP-CIDR/GEOIP/MATCH` 等自动跳过），
   否则沿用官方 `domain-list-community` 的同名分类。
2. 生成的分类写入官方仓库 `data/custom/` —— 与官方 `data/` **同名分类自动合并**。
   特别的，`cn` = 官方 cn + （可选 `config/cn.txt`）+ `config/cn-extra.txt`。
3. `go run ./` 编译（allowlist 裁剪，只保留清单里的分类）→ `out/geosite.dat`。

> 第 2、3 步由 GitHub Actions 在云端执行，仓库内不含任何本地构建脚本。
> 每次 commit 到 `main`/`master` 都会触发编译，产物只存在于本次运行的
> Actions Artifact、`dist` 分支与 `latest` Release 中（不入库）。

## GitHub Actions 自动构建

每次 push 到 `main`/`master` 会自动运行 `.github/workflows/build.yml`：

- **build job**：编译并上传 Actions Artifact（可在仓库 Actions 页面按 commit 下载）；
- **publish job**：把产物推送到 `dist` 分支，可直接用 raw URL 拉取最新版：
- **release-latest job**：每次 push 到 `main`/`master` 自动把最新产物发布为
  `latest` Release（始终对应最新一次构建，无需手动打 tag）。

```
https://raw.githubusercontent.com/<你的用户名>/<仓库名>/dist/geosite.dat
# 国内可换 ghproxy 前缀，例如:
https://mirror.ghproxy.com/https://raw.githubusercontent.com/<用户名>/<仓库名>/dist/geosite.dat
```

PR 也会触发编译验证（不发布），支持 `workflow_dispatch` 手动触发。

## GitHub Release（默认 latest，可选打 tag 发版本）

**每次 push 到 `main`/`master`**，`release-latest` job 会自动把当次构建的
`geosite.dat` 与 `geosite.dat.sha256sum` 发布为 tag=`latest` 的 **GitHub Release**
（旧的 `latest` Release 会被删除重建，始终指向最新提交）。可直接用固定 URL 下载最新版：

```
https://github.com/<你的用户名>/<仓库名>/releases/latest/download/geosite.dat
```

若需要带版本号的正式 Release，仍可 push 形如 `v*` 的 tag，会额外生成一个版本化 Release：

```bash
git tag v1.0.0
git push origin v1.0.0
```

可在仓库 Releases 页面看到版本与可下载附件；版本化 Release 也支持带 `-rc`/`-beta` 等后缀的预发布 tag。

## config 规则语法

`config/` 里的规则文件采用 **v2fly/domain-list-community 的 data 语法**（每行一条，`#` 开头为注释，与官方 `data/` 目录完全一致）：

```
example.com           # domain：匹配该域及其子域（裸域名即此类型）
full:example.com      # full：精确匹配完整域名，不含子域
keyword:google        # keyword：域名中包含该关键字
regexp:^ads\..*       # regexp：Go 正则
include:another-list  # include：引用其它分类
example.com @ads      # 规则可附加 @属性（过滤/标识用）
```

> 为兼容起见，生成器也接受少量 Clash 前缀写法并自动转换
> （`DOMAIN-SUFFIX,→domain`、`DOMAIN,→full`、`DOMAIN-KEYWORD,→keyword`、`DOMAIN-REGEX,→regexp`），
> 但**推荐直接使用官方 v2fly 语法**。非域名规则（`IP-CIDR`/`GEOIP`/`MATCH` 等）会被自动忽略。

## 添加 / 修改分类

1. 编辑 `config/rules.txt`：加一行即把该分类纳入产物，如 `Apple: Apple`；
2. 若要给某分类加自定义规则，在 `config/` 放同名源文件（如 `config/Apple.txt`，语法见上）；
   不放则自动沿用官方 `domain-list-community` 的同名分类；
3. 若要增强 cn，编辑 `config/cn-extra.txt`（它会合入 `geosite:cn`）；
4. commit 推送 —— Actions 自动出新的 `geosite.dat`。

> `config/rules.txt` 里的 `cn: cn` 这一行请保留——它负责把 `cn-extra.txt` 的内容合入 cn；
> 若连官方 cn 底库也不想要，可改为自定义 `config/cn.txt` 完全接管 cn 内容。

## 路由用法示例（mihomo / xray）

```yaml
rules:
  - GEOSITE,cn,DIRECT
  - GEOSITE,Apple,DIRECT
  - GEOSITE,Google,PROXY
```
