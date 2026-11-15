# 提交规范

## 0. 准备

- 已接受仓库的 Collaborator 邀请（邮箱里点接受）。
- 本机装好 Git，并配置身份：

```bash
git config --global user.name "你的名字"
git config --global user.email "你的邮箱@example.com"
git config --global core.quotepath false   # Windows 下正常显示中文文件名
```

## 1. 克隆

```bash
git clone https://github.com/<仓库所有者>/team-progress.git
cd team-progress
```

## 2. 每天提交进度

```bash
git pull --rebase
# 新建 members/<你的文件夹>/logs/2026-11-15.md
git add members/<你的文件夹>
git commit -m "progress(<你的文件夹>): 2026-11-15 完成视觉标定脚本"
git push
```

`git pull --rebase` 的作用：把你本地的提交「垫」在别人的提交之后，避免产生无意义的 merge 提交。

## 3. 进度文件写什么

最少四行，多了不限：

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

## 4. 分支与 PR（推荐，不是必须）

小团队可以直接推 `main`；想让进度可回溯、可评论时用分支：

```bash
git checkout -b progress/<你的文件夹>-2026-11-15
git add members/<你的文件夹>
git commit -m "progress(<你的文件夹>): 2026-11-15 ..."
git push -u origin progress/<你的文件夹>-2026-11-15
```

然后在 GitHub 页面点 **Compare & pull request**，自己合并即可（自审也留痕）。

分支命名：`progress/<名字>-<日期>`、`feat/<名字>-<主题>`、`fix/<名字>-<主题>`。

## 5. 提交信息格式

```
progress(<你的文件夹>): 2026-11-15 一句话摘要
feat(<你的文件夹>): 新增 XXX 功能
fix(<你的文件夹>): 修复 XXX
docs: 更新 README
```

## 6. 冲突了怎么办

只改自己目录的话基本不会冲突。真遇到：

```bash
git pull --rebase
# 打开冲突文件，保留正确内容，删掉 <<<<<<< ======= >>>>>>> 标记
git add <冲突文件>
git rebase --continue
```

实在搞不定：`git rebase --abort` 回到操作前，然后在群里问，不要强推。

## 7. 公共文件（README、模板、配置）

- 改动前先在群里说一声，或开一个 PR 让大家看一眼。
- 不要直接改别人的 `members/` 目录。

## 8. 不要提交的东西

- 超过 50 MB 的单个文件（GitHub 硬限制 100 MB）。
- 密码、Token、密钥（一旦推上去就视为泄露，必须立刻更换）。
- 编译产物、`node_modules/`、临时文件（已在 `.gitignore` 里）。

## 9. 查看进度

- 仓库首页的提交历史：`https://github.com/<所有者>/team-progress/commits/main`
- 按人筛选：`git log --author="你的名字" --oneline`
- 图形化：`git log --graph --oneline --all`
