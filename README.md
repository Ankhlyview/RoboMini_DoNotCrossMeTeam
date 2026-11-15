# 团队进度仓库

5 人协作的进度记录仓库。**每人一个独立文件夹，只在自己的文件夹里提交**，这样几乎不会产生 Git 冲突。

## 目录结构

```
team-progress/
├─ README.md              # 本文件：仓库说明与总览
├─ CONTRIBUTING.md        # 提交规范（新人先读这个）
├─ .gitattributes         # 换行符 / 二进制文件规则
├─ .gitignore             # 忽略临时文件和大文件
├─ .github/
│  └─ CODEOWNERS          # 目录归属（可选，用于自动请求 Review）
├─ templates/
│  └─ weekly.md           # 周报模板，复制使用
└─ members/
   ├─ Algorithm_A/            # 算法 · A
   │  ├─ README.md            # 我是谁、负责什么、进度索引
   │  └─ logs/                # 按日期存放进度文件
   ├─ ElectricBrazing_Z/      # 电钎焊 · Z
   ├─ ElectronicSoftware_L/   # 电子软件 · L
   ├─ Machinery_H/            # 机械 · H
   └─ Machinery_Z/            # 机械 · Z
      ├─ README.md
      └─ logs/
         └─ 2026-11-15.md     # 示例：一天一个文件
```

> 文件夹名用「分工_姓氏首字母」而不是中文：排序稳定，Windows / macOS / Linux 都不会乱码。真实姓名写在各自的 `README.md` 里。

## 每个人的日常流程

```bash
git clone https://github.com/<你的用户名>/team-progress.git
cd team-progress
```

之后每次提交进度：

```bash
git pull --rebase                 # 先同步别人的提交
# 在 members/你的文件夹/logs/ 下新建 YYYY-MM-DD.md，写今天做了什么
git add members/你的文件夹
git commit -m "progress(你的名字): 2026-11-15 今日进度"
git push
```

详细规则、分支与 PR 流程见 [CONTRIBUTING.md](CONTRIBUTING.md)。

## 三条硬规则

1. **只改自己的目录**：`members/<你的文件夹>/` 之外的文件不要动。
2. **一个日期一个文件**：`logs/2026-11-15.md`，不要所有人共用一个 `进度.md`（否则必然冲突）。
3. **大文件不进 Git**：视频、安装包、超过 50 MB 的设计稿放网盘或 GitHub Release，仓库里只放链接。

## 每周节奏（建议）

| 时间 | 动作 |
| --- | --- |
| 周一 | 各人在自己 `logs/` 里写下本周目标 |
| 周三 | 中期同步，有阻塞当天记录 |
| 周五 | 复制 `templates/weekly.md` 写周报，负责人汇总到 Issue 或 Projects 看板 |

## 总览

| 文件夹 | 成员 | 负责模块 |
| --- | --- | --- |
| [Algorithm_A](members/Algorithm_A/) | 待填写 | 算法 |
| [ElectricBrazing_Z](members/ElectricBrazing_Z/) | 待填写 | 电钎焊 |
| [ElectronicSoftware_L](members/ElectronicSoftware_L/) | 待填写 | 电子软件 |
| [Machinery_H](members/Machinery_H/) | 待填写 | 机械（H） |
| [Machinery_Z](members/Machinery_Z/) | 待填写 | 机械（Z） |
