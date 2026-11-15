# RoboMini_DoNotCrossMeTeam

RoboMini 项目组的**进度协作仓库**。5 名成员各自在 `members/` 下拥有独立文件夹，每天把自己的进展写成 Markdown 提交上来，负责人通过提交历史和看板掌握整体进度。

> **核心原则：一人一目录，一天一文件。** 只要只动自己的目录，就几乎不会产生冲突。

---

## 目录结构

```
RoboMini_DoNotCrossMeTeam/
├─ README.md                 # 本文件：使用说明，先读完这一份
├─ templates/
│  ├─ daily.md               # 日报模板
│  └─ weekly.md              # 周报模板
├─ .github/CODEOWNERS        # 目录归属（可选，用于自动请求 Review）
└─ members/
   ├─ Algorithm_A/           # 算法
   │  ├─ README.md           # 我是谁、负责什么、进度索引
   │  └─ logs/               # 每天一个文件
   ├─ ElectricBrazing_Z/     # 电硬
   ├─ ElectronicSoftware_L/  # 电软
   ├─ Machinery_H/           # 机械（H）
   └─ Machinery_Z/           # 机械（Z）
```

团队约定：**进度文件只放在自己的 `logs/` 下**，文件名用日期 `YYYY-MM-DD.md`；方案、图纸、代码放自己目录下的 `docs/`、`src/`。

---

## 一、第一次使用：从零到第一次提交

### 第 1 步：接受邀请（否则打不开仓库）

让仓库负责人操作：仓库 → **Settings** → **Collaborators and teams** → **Add people** → 输入你的 GitHub 用户名。

你会收到一封邮件，点 **Accept invitation**。没接受之前，私有仓库的链接对你是 404，不是仓库不存在。

### 第 2 步：安装 Git

Windows（在 PowerShell 里执行）：

```powershell
winget install --id Git.Git -e
```

macOS：`brew install git`；或到 <https://git-scm.com/downloads> 下载安装。

装完**重开一个终端**，验证：

```bash
git --version
```

### 第 3 步：配置身份（只做一次，全局生效）

```bash
git config --global user.name "张三"
git config --global user.email "你的GitHub邮箱@example.com"
git config --global core.quotepath false
git config --global pull.rebase true
```

- `user.name`：会显示在提交记录里，写真实姓名，方便统计。
- `user.email`：用 GitHub 绑定的邮箱。
- `core.quotepath false`：Windows 下正常显示中文文件名。
- `pull.rebase true`：以后 `git pull` 自动变基，不产生多余的 merge 提交。

### 第 4 步：克隆到本地（只做一次）

```bash
cd D:\你的工作目录
git clone https://github.com/Ankhlyview/RoboMini_DoNotCrossMeTeam.git
cd RoboMini_DoNotCrossMeTeam
```

`git status` 显示 `On branch main` 和 `nothing to commit, working tree clean` 就成功了。

### 第 5 步：第一次提交

```bash
git pull --rebase
# 新建 members/Algorithm_A/logs/2026-11-15.md，随便写两句即可
git add "members/Algorithm_A/logs/2026-11-15.md"
git commit -m "progress(Algorithm_A): 2026-11-15 第一天，读完使用说明"
git push
```

第一次 `push` 会弹出浏览器窗口让你登录 GitHub，授权即可（Git 自带凭据管理器，登录一次后长期有效）。

**如果终端提示输入密码**：GitHub 早已不支持账号密码，不要输。改用浏览器授权；实在弹不出窗口，就去 GitHub → Settings → Developer settings → **Personal access tokens (classic)** 生成 token，勾选 `repo`，把 token 当密码粘贴。

---

## 二、每天怎么提交

```bash
cd D:\你的工作目录\RoboMini_DoNotCrossMeTeam

git pull --rebase        # 1. 先拉别人的提交
# 2. 新建 members/你的文件夹/logs/2026-11-15.md，写今天做了什么
git status               # 3. 看一眼改了哪些文件
git add "members/你的文件夹/logs/2026-11-15.md"   # 4. 只暂存自己的文件
git commit -m "progress(你的文件夹): 2026-11-15 一句话摘要"
git push                 # 5. 推上 GitHub
```

四个动作的分工，别混：

| 命令 | 作用 |
| --- | --- |
| `git add` | 决定「这次提交包含哪些改动」 |
| `git commit` | 把暂存区打包成一个提交，并写说明 |
| `git push` | 上传到 GitHub，别人才能看到 |
| `git pull --rebase` | 先把别人的提交同步下来，再叠上你的 |

### 日报写什么

复制 `templates/daily.md` 的骨架，或直接照这个写：

```markdown
# 2026-11-15

## 今天完成
- 完成相机标定脚本，误差 0.8 px

## 遇到的问题
- 标定板反光，夜间识别率下降

## 明天计划
- 换哑光标定板复测；补 3 组数据

## 相关链接
- PR #12 / 提交 abc1234 / 数据在网盘 xxx
```

同一天要补内容，就改这个文件再提交一次，**不要**新建 `2026-11-15-2.md`。

---

## 三、不想敲命令：直接在网页上提交

GitHub 网页本身就能编辑，适合只补一条记录、身边没装 Git 的情况。

**新建日报**：仓库首页 → 进入 `members/你的文件夹/logs/` → 右上角 **Add file** → **Create new file** → 文件名填 `2026-11-15.md` → 写内容 → 底部 **Commit changes** → 直接提交到 `main`。

**修改已有文件**：打开文件 → 右上角铅笔图标 → 编辑 → **Commit changes**。

**新建文件夹**：在文件名里连路径一起写，例如 `members/Algorithm_A/docs/方案.md`，GitHub 会自动建目录。

优点：零安装、手机上也能用。缺点：一次只能改一个文件、没有本地预览。**日常仍推荐命令行，临时补记录用网页。**

---

## 四、提交信息怎么写

格式：

```
类型(文件夹): 日期 一句话摘要
```

| 类型 | 用在什么时候 |
| --- | --- |
| `progress` | 日常进度、日报 |
| `feat` | 新增功能、文档、图纸 |
| `fix` | 修复问题 |
| `docs` | 改说明、改模板 |

例子：

```
progress(Algorithm_A): 2026-11-15 标定误差降到 0.8px
feat(Machinery_H): 底盘装配图 v2
fix(ElectronicSoftware_L): 修复串口断连
docs: 更新 README 的提交说明
```

括号里只是**标签**，不是路径，Git 不会解析它；写成文件夹名是为了能按人筛选：

```bash
git log --oneline --grep="Algorithm_A"    # 只看自己的提交
git log --oneline -10                     # 看最近 10 条
```

---

## 五、什么时候用分支和 PR

| 情况 | 做法 |
| --- | --- |
| 只改自己 `members/你的文件夹/` 里的文件 | 直接推 `main`，不用想 |
| 改 `README.md`、`templates/`、`.gitignore` 等公共文件 | 开分支 → PR → 自己合并，留个痕迹 |
| 大重构、实验性方案、可能被推翻的代码 | 开分支 `exp/你的文件夹-日期`，成了再合 |

```bash
git checkout -b docs/readme-update
# 改文件
git add README.md
git commit -m "docs: 补充成员分工表"
git push -u origin docs/readme-update
```

然后在网页上点 **Compare & pull request** → 填标题 → **Create pull request** → **Merge pull request**。

PR 的好处：改动有记录、可以评论、可以整批回退。小改动不必走，大改动值得走。

---

## 六、六条硬规矩

1. **只改自己的目录**：`members/你的文件夹/` 之外的文件不要动。
2. **一天一个文件**：`logs/2026-11-15.md`，不要所有人共用一个 `进度.md`。
3. **不用 `git add .`**：它会把你本地的临时文件、编译产物一起提交。始终写具体路径。
4. **大文件不进 Git**：视频、安装包、超过 50 MB 的设计稿放网盘或 GitHub Release，仓库里只放链接。
5. **不放密码和密钥**：一旦推上去就等于公开，删掉也留在历史里。
6. **不用 `git push -f`**：会覆盖别人的提交。push 被拒时先 `git pull --rebase`。

---

## 七、常见问题

| 现象 / 报错 | 原因 | 解决 |
| --- | --- | --- |
| 仓库链接打开 404 | 还没接受邀请 | 让负责人加你为 Collaborator，邮件里点 Accept |
| `fatal: not a git repository` | 当前目录不是仓库 | `cd RoboMini_DoNotCrossMeTeam` 再操作 |
| `Updates were rejected...` | 别人先推了，你本地落后 | `git pull --rebase` 后重新 `git push` |
| `Please tell me who you are` | 没配身份 | 执行第 3 步的两条 `git config` |
| 提示输入密码 / `Support for password authentication was removed` | 用了账号密码 | 浏览器授权，或生成 PAT 当密码 |
| 中文文件名显示成 `\344\270\255` | 编码设置 | `git config --global core.quotepath false` |
| `git status` 看不到刚建的文件 | 被 `.gitignore` 忽略，或文件夹是空的 | Git 不跟踪空目录，确保里面有 `.md` 文件 |
| 提示文件过大 | 单文件超过 100 MB | 改用网盘链接，或联系负责人用 Release |
| `CONFLICT (content)` | 两人改了同一行 | 打开文件删掉 `<<<<<<<` `=======` `>>>>>>>` 标记，保留正确内容，再 `git add` + `git rebase --continue` |

**看不懂的报错，先别强推，截图发群里。**

### 后悔了怎么办

| 想做的事 | 命令 |
| --- | --- |
| 撤销还没提交的修改 | `git restore <文件>` |
| 取消暂存（add 错了） | `git restore --staged <文件>` |
| 撤销最近一次提交，保留改动 | `git reset --soft HEAD~1` |
| 已经 push 了想撤回 | `git revert <提交号>` 然后 `git push` |

最后一条会生成一条「反向提交」，历史保留，安全。

---

## 八、每周节奏

| 时间 | 动作 |
| --- | --- |
| 周一 | 在自己 `logs/` 里写下本周目标 |
| 周三 | 中期同步，有阻塞当天记录 |
| 周五 | 复制 `templates/weekly.md` 写周报，负责人汇总到 Issue 或 Projects |

**负责人每周额外做 10 分钟**：扫一遍提交记录看谁没提交 → 更新下面的分工表 → 处理 PR → 里程碑打 tag（`git tag v0.1 && git push --tags`）。

---

## 九、成员与分工

| 文件夹 | 成员 | 负责模块 | 进度 |
| --- | --- | --- | --- |
| [Algorithm_A](members/Algorithm_A/) | 安 | 算法 | [logs](members/Algorithm_A/logs/) |
| [ElectricBrazing_Z](members/ElectricBrazing_Z/) | 周 | 电硬 | [logs](members/ElectricBrazing_Z/logs/) |
| [ElectronicSoftware_L](members/ElectronicSoftware_L/) | 李 | 电软 | [logs](members/ElectronicSoftware_L/logs/) |
| [Machinery_H](members/Machinery_H/) | 黄 | 机械（H） | [logs](members/Machinery_H/logs/) |
| [Machinery_Z](members/Machinery_Z/) | 周 | 机械（Z） | [logs](members/Machinery_Z/logs/) |

> `README.md` 里可以补上自己的 GitHub 账号和更细的分工。

---

## 十、GitHub 界面速览

| 位置 | 用途 |
| --- | --- |
| **Code** | 文件列表和提交历史，点 `commits` 看谁改了什么 |
| **Issues** | 记任务、报问题，可以指派给人 |
| **Pull requests** | 分支合并请求，顺便当评审记录 |
| **Projects** | 看板视图，每人一列，适合周会过进度 |
| **Settings → Collaborators** | 加人（只有负责人有权限） |

平时只需要两个入口：**Code** 看文件，**commits** 看历史。
