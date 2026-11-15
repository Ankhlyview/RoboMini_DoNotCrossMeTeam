# 提交操作指南

面向**第一次用 Git** 的成员。Windows 请在 PowerShell 里执行；macOS / Linux 把 `D:\` 换成自己的路径即可。

---

## 0. 一次性准备（只做一次）

### 0.1 接受邀请

仓库主会在 GitHub 上把你加为 Collaborator，你会收到一封邮件。
点邮件里的 **View invitation → Accept invitation**。

> 没接受邀请前，私有仓库的链接对你是 404，这不是仓库不存在。

### 0.2 安装 Git

Windows（PowerShell 执行）：

```powershell
winget install --id Git.Git -e
```

或到 <https://git-scm.com/downloads> 下载安装，一路默认即可。
装完**重开一个终端**，验证：

```bash
git --version
```

### 0.3 配置身份（只配一次，全局生效）

```bash
git config --global user.name "张三"
git config --global user.email "你的GitHub邮箱@example.com"
git config --global core.quotepath false
git config --global pull.rebase true
```

- `user.name` 会显示在提交记录里，写真实姓名，方便统计进度。
- `user.email` 建议用 GitHub 账号绑定的邮箱。
- `core.quotepath false`：Windows 下正常显示中文文件名。
- `pull.rebase true`：以后 `git pull` 自动变基，不产生多余的 merge 提交。

### 0.4 关于登录（第一次 push 时才会遇到）

第一次 `git push` 会弹出浏览器窗口让你登录 GitHub，点授权即可（Git for Windows 自带 Git Credential Manager，登录一次以后就记住）。

如果终端里让你输入密码，**不要输账号密码**——GitHub 早已不支持，会报：

```
remote: Support for password authentication was removed
```

正确做法：GitHub → 头像 → Settings → Developer settings → **Personal access tokens (classic)** → Generate new token，勾选 `repo`，把生成的 token 当作密码粘贴。

---

## 1. 第一次：克隆仓库

```bash
cd D:\你的工作目录
git clone https://github.com/Ankhlyview/RoboMini_DoNotCrossMeTeam.git
cd RoboMini_DoNotCrossMeTeam
```

验证是否成功：

```bash
git status
```

应该显示 `On branch main` 和 `nothing to commit, working tree clean`。

---

## 2. 每次提交（核心只有 5 步）

```bash
git pull --rebase        # 1. 先拉别人的提交
# 2. 新建 members/你的文件夹/logs/2026-11-15.md，写今天做了什么
git status               # 3. 看一眼改了哪些文件，确认没多带东西
git add "members/你的文件夹/logs/2026-11-15.md"   # 4. 只加自己的文件
git commit -m "progress(你的文件夹): 2026-11-15 一句话摘要"
git push                 # 5. 推上去
```

> `git add` 后面写**具体文件路径**，不要用 `git add .`——那会把你本地所有杂七杂八的文件一起提交。

### 2.1 进度文件写什么

复制这个骨架，每次替换内容即可：

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

规则：**一天一个文件**，文件名用 `YYYY-MM-DD.md`。同一天要补内容就改这个文件再提交一次，不要建 `2026-11-15-2.md`。

### 2.2 提交信息怎么写

```
progress(你的文件夹): 2026-11-15 一句话摘要
```

例子：

```
progress(Algorithm_A): 2026-11-15 标定误差降到 0.8px
progress(Machinery_H): 2026-11-15 底盘装配图 v2
```

> 文件夹名就是 `members/` 下你的那个目录名，比如 `Algorithm_A`。

---

## 3. 不想敲命令？用 VS Code

1. 装 VS Code 和 Git，用 VS Code 打开克隆下来的文件夹。
2. 左侧点 **源代码管理** 图标（或按 `Ctrl+Shift+G`）。
3. 改完文件后，在列表里点文件旁的 **+** 暂存。
4. 上方输入框写提交信息，点 **提交**。
5. 点 **同步更改 / Sync Changes** 推送。

推送前如果提示需要先拉取，点 **拉取（Pull）** 再推。

---

## 4. 出错了怎么办

| 报错 / 现象 | 原因 | 解决 |
| --- | --- | --- |
| `Updates were rejected because the remote contains work...` | 别人先推了，你本地落后 | `git pull --rebase` 后重新 `git push` |
| `fatal: not a git repository` | 当前目录不是仓库 | `cd` 进 `RoboMini_DoNotCrossMeTeam` 再操作 |
| `Support for password authentication was removed` | 用了账号密码 | 改用 PAT 或浏览器登录（见 0.4） |
| `Please tell me who you are` | 没配身份 | 执行 0.3 的两条 `git config` |
| 中文文件名显示成 `\344\270\255` | 编码设置 | `git config --global core.quotepath false` |
| `git status` 里看不到刚建的文件 | 被 `.gitignore` 忽略，或文件夹是空的 | Git 不跟踪空目录，确保里面真的有 `.md` 文件 |
| 提示文件过大 / `large files detected` | 单文件超过 100 MB | 改成网盘链接，或联系仓库主用 Release |
| `error: Your local changes would be overwritten` | 有未提交的修改 | 先 `git stash`，拉取后再 `git stash pop` |
| 提示冲突 `CONFLICT (content)` | 两人改了同一行 | 打开文件删掉 `<<<<<<<` `=======` `>>>>>>>` 标记，保留正确内容，然后 `git add` + `git rebase --continue` |

**记住一条**：任何看不懂的错误，先别用 `git push -f`，截图发群里。强推会覆盖别人的提交。

---

## 5. 提交前自查

- [ ] 只改了自己 `members/你的文件夹/` 里的文件
- [ ] 进度文件在 `logs/` 下，文件名是 `YYYY-MM-DD.md`
- [ ] `git status` 列出的文件都是你打算提交的
- [ ] 没有密码、Token、密钥、身份证号等敏感信息
- [ ] 没有超过 50 MB 的文件
- [ ] 提交信息能看出「谁 + 哪天 + 干了什么」

---

## 6. 后悔了怎么办

| 想做的事 | 命令 |
| --- | --- |
| 撤销还没提交的修改 | `git restore <文件>` |
| 取消暂存（add 错了） | `git restore --staged <文件>` |
| 撤销最近一次提交，保留改动 | `git reset --soft HEAD~1` |
| 已经 push 了想撤回 | `git revert <提交号>` 然后 `git push` |

最后一种会生成一条「反向提交」，历史保留，安全。**不要**用 `git reset --hard` 加 `push -f` 去删远程历史。

---

## 7. 一页速查

```bash
git status                  # 我现在改了什么
git pull --rebase           # 拉最新
git add <具体文件>           # 暂存
git commit -m "progress(文件夹): 日期 摘要"
git push                    # 推送
git log --oneline -5        # 看最近 5 条提交
```

就这 6 条，够用一整个项目。
