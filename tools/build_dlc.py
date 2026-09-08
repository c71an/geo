#!/usr/bin/env python3
"""
读取 config/rules.txt（geosite 分类清单）与 config/cn-extra.txt（cn 自定义补充），
把自定义规则写入 domain-list-community/data/custom/（与官方同名分类自动合并），
并生成 allowlist 用的 dat_diy.json，供 `go run ./ --datprofile=dat_diy.json` 编译使用。

用法: python tools/build_dlc.py
前置: 目录下需存在 domain-list-community/（官方仓库 clone，GitHub Actions 会自动拉取）
"""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CONFIG = ROOT / "config"
REPO_DATA = ROOT / "domain-list-community" / "data"
CUSTOM = REPO_DATA / "custom"
RULES_FILE = CONFIG / "rules.txt"
CN_EXTRA_FILE = CONFIG / "cn-extra.txt"

# Clash 前缀 -> v2fly 规则类型
PREFIX_MAP = {
    "DOMAIN-SUFFIX": "domain",   # 该域及其子域
    "DOMAIN": "full",            # Clash DOMAIN 为精确匹配
    "DOMAIN-KEYWORD": "keyword",
    "DOMAIN-REGEX": "regexp",
}
# 非域名规则，忽略
SKIP_PREFIX = ("IP-CIDR", "IP-CIDR6", "GEOIP", "SRC-IP-CIDR", "MATCH",
               "PROCESS-NAME", "RULE-SET", "AND", "OR", "NOT", "FINAL")

# v2fly 列表名允许字符（加载时会被转大写）
NAME_RE = re.compile(r"^[A-Za-z0-9!-]+$")


def parse_rule(raw: str):
    """一行 -> (type, value) 或 None。type ∈ domain|full|keyword|regexp"""
    line = raw.split("#", 1)[0].strip()
    if not line:
        return None
    line = re.sub(r"^-\s*", "", line).strip()          # 兼容 yaml 列表项 "- xxx"
    if line.lower().startswith("payload"):            # 跳过 yaml payload: 头
        return None
    # 已是 v2fly 语法则原样保留
    m = re.match(r"^(domain|full|keyword|regexp):(.+)$", line, re.I)
    if m:
        return m.group(1).lower(), m.group(2).strip().lower()
    head, _, val = line.partition(",")
    head_up = head.upper()
    if head_up in PREFIX_MAP:
        return PREFIX_MAP[head_up], val.strip().lower()
    if head_up.startswith(SKIP_PREFIX) or "," in line:
        return None                                    # 未知前缀/带逗号 → 非纯域名规则
    return "domain", line.lower()                      # 裸域名 → domain:


def parse_lines(text: str):
    out = []
    for ln in text.splitlines():
        r = parse_rule(ln)
        if r:
            out.append(r)
    return out


def read_source(src: str):
    """可选自定义源：config/<src> 或 config/<src>.txt；不存在返回空（沿用官方分类）"""
    for cand in (CONFIG / src, CONFIG / f"{src}.txt"):
        if cand.is_file():
            return parse_lines(cand.read_text(encoding="utf-8", errors="ignore"))
    return []


def main():
    if not REPO_DATA.is_dir():
        sys.exit("[Fatal] 缺少 domain-list-community/（GitHub Actions 会自动 clone；本地请先 git clone）")

    # 1) 解析 rules.txt 映射
    maps = []
    for ln in RULES_FILE.read_text(encoding="utf-8").splitlines():
        line = ln.split("#", 1)[0].strip()
        if ":" not in line:
            continue
        src, cat = (x.strip() for x in line.split(":", 1))
        if src and cat:
            maps.append((src, cat))
    if not maps:
        sys.exit("[Fatal] rules.txt 为空或格式错误（每行应为: 源文件 : 分类）")

    # 2) 清理上次生成的自定义分类
    if CUSTOM.is_dir():
        for f in CUSTOM.iterdir():
            if f.is_file():
                f.unlink()
    CUSTOM.mkdir(parents=True, exist_ok=True)

    extra_cn = parse_lines(CN_EXTRA_FILE.read_text(encoding="utf-8")) if CN_EXTRA_FILE.is_file() else []
    allowlist = []

    for src, cat in maps:
        key = cat.lower()
        if not NAME_RE.match(key):
            print(f"  [skip] {src:24s} -> 非法分类名 {cat!r}（仅允许字母数字 ! -）")
            continue

        rules = read_source(src)
        if key == "cn":                               # cn = (可选 config/cn.txt) + cn-extra
            rules += extra_cn
        rules = sorted(set(rules))                    # 去重 + 排序，保证产物可复现

        official = REPO_DATA / key
        has_custom = bool(rules)
        has_official = official.is_file() and official.stat().st_size > 0

        if has_custom:
            (CUSTOM / key).write_text(
                "".join(f"{t}:{v}\n" for t, v in rules), encoding="utf-8")
            print(f"  [gen]  {src:24s} -> geosite:{cat}  ({len(rules)} 条)")
        elif has_official:
            print(f"  [use]  {src:24s} -> geosite:{cat}  (config 中无源文件，沿用官方同名分类)")
        else:
            print(f"  [skip] {src:24s} -> config 无源文件且官方无此分类，已忽略")
            continue

        allowlist.append(cat)

    # 3) 生成 datprofile：仅保留 allowlist 分类，输出文件名定为 geosite.dat
    tasks = [{"name": "geosite.dat", "mode": "allowlist", "lists": allowlist}]
    (ROOT / "dat_diy.json").write_text(
        json.dumps(tasks, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"\n共 {len(allowlist)} 个分类 → dat_diy.json 已生成，随后编译出 out/geosite.dat")


if __name__ == "__main__":
    main()
