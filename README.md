# RoboMini_DoNotCrossMeTeam


---

## 目录结构(重中之重)

```
RoboMini_DoNotCrossMeTeam/
├─ README.md                 # 本文件：使用说明，先读完这一份
├─ templates/                # 可以忽略
│  ├─ daily.md               # 日报模板
│  └─ weekly.md              # 周报模板
├─ .github/CODEOWNERS        # 目录归属（可选，用于自动请求 Review）
└─ members/                  # 每个人的文件夹下放置自己的代码就好，不要改动别人的文件夹(文件夹中带有一个logs的电东西，可以用来写日志)
   ├─ Algorithm_A/           # 算法
   ├─ ElectricBrazing_Z/     # 电硬
   ├─ ElectronicSoftware_L/  # 电软
   ├─ Machinery_H/           # 机械（H）
   └─ Machinery_Z/           # 机械（Z）
```

**重中之重×2：只在自己的对应的文件夹下修改，提交的时候请提交原工程和示例(图片之类的)**

---

## 一.使用GitHub
### 1. 安装git，注册GitHub，登录GitHub(能做到这里我觉得也不用提了)
### 2. 接受成为协作者的邀请
### 3. 配置身份（只做一次）

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
###  4. 克隆到本地（只做一次）

```bash
cd D:\你的工作目录  #(不同操作系统按照自己的来)
git clone https://github.com/Ankhlyview/RoboMini_DoNotCrossMeTeam.git
cd RoboMini_DoNotCrossMeTeam
```
一般来讲克隆之后，你的本地就会有一个上述目录的结构，以后就在自己的对应文件夹里修改和上传。
### 5. 每次提交的时候
以我自己为例，别人请修改Algorithm_A对应自己的文件夹
加入我在members/Algorithm_A/中修改了文件，想要重新提交这个文件夹中的所有内容，就依次在命令行中，输入指令就行。
```bash
git pull --rebase
git add "members/Algorithm_A/"
git commit -m "一句提交附带的话"
git push
```

`git status` 显示 `On branch main` 和 `nothing to commit, working tree clean` 就成功了。

第一次 `push` 会弹出浏览器窗口让你登录 GitHub，授权即可（Git 自带凭据管理器，登录一次后长期有效）。

**如果终端提示输入密码**：GitHub 早已不支持账号密码，不要输。改用浏览器授权；实在弹不出窗口，就去 GitHub → Settings → Developer settings → **Personal access tokens (classic)** 生成 token，勾选 `repo`，把 token 当密码粘贴。



---


## 二、成员与分工

| 文件夹 | 成员 | 负责模块 |  
| --- | --- | --- | 
| [Algorithm_A](members/Algorithm_A/) | 安 | 算法 | 
| [ElectricBrazing_Z](members/ElectricBrazing_Z/) | 周 | 电硬 |
| [ElectronicSoftware_L](members/ElectronicSoftware_L/) | 李 | 电软 | 
| [Machinery_H](members/Machinery_H/) | 黄 | 机械（H） | 
| [Machinery_Z](members/Machinery_Z/) | 周 | 机械（Z） |


---

## 三、注意事项

1. **只改自己的目录**：`members/你的文件夹/` 之外的文件不要动。
2. **不用 `git add .`**：它会把你本地的临时文件、编译产物一起提交。始终写具体路径。
3. **大文件不进 Git**：视频、安装包、超过 50 MB 的设计稿放网盘或 GitHub Release，仓库里只放链接。
4. **不放密码和密钥**：一旦推上去就等于公开，删掉也留在历史里。
5. **不用 `git push -f`**：会覆盖别人的提交。push 被拒时先 `git pull --rebase`。

---

## 四、常见问题

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

## 五、什么时候用分支和 PR(额外内容)

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

## 六、GitHub 界面速览

| 位置 | 用途 |
| --- | --- |
| **Code** | 文件列表和提交历史，点 `commits` 看谁改了什么 |
| **Issues** | 记任务、报问题，可以指派给人 |
| **Pull requests** | 分支合并请求，顺便当评审记录 |
| **Projects** | 看板视图，每人一列，适合周会过进度 |
| **Settings → Collaborators** | 加人（只有负责人有权限） |

平时只需要两个入口：**Code** 看文件，**commits** 看历史。
