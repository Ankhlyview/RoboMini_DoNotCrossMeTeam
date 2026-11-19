# 代码阅读指南（Algorithm_A 自瞄包）

> 目标：不是“从第一行读到最后一行”，而是先建立数据流，再沿着**一帧图像**把代码走一遍，最后通过改参数验证理解。
> 建议配合 `README.md` 一起看；本指南里的行号以当前文件为准。

---

## 0. 先跑起来，再看代码（10 分钟）

学习代码前先建立“现象 → 代码”的对应关系：

```bash
# 终端 1
conda deactivate
source /opt/ros/jazzy/setup.bash
source ~/Gitclone/Vision_robomini/robomini_sim/ros2_ws/install/setup.bash
ros2 launch robomini_sim sim.launch.py

# 终端 2
cd ~/Gitclone/RoboMini_DoNotCrossMeTeam/members/Algorithm_A/code
./build.sh
./run.sh fire:=false
```

看：

```bash
ros2 run rqt_image_view rqt_image_view /vision/debug_image
ros2 topic echo /vision/target_pose --once
```

你会看到：绿色 `PENDING 4`、橙色 `ACTIVE 2`、HUD 上的像素/位姿/角度/误差。
先在纸上画出这条链：

```
相机图像
  → 找灯条
  → 聚成靶
  → 判断 pending / active
  → pending 像素反投影成 3D 位姿
  → 由枪口解 yaw/pitch
  → 发布 /vision_to_gimbal (mode 1/2)
  → launcher_node → Gazebo 发球
```

如果这条链你能自己复述，后面的代码只是它的分段实现。

---

## 1. 阅读顺序（按依赖，不要按目录）

| 顺序 | 文件 | 为什么先看它 | 预计时间 |
|---|---|---|---|
| 1 | `README.md` 第 3、4 节 | 先知道输入输出和公式 | 15 min |
| 2 | `robomini_vision/geometry.py` | 纯 Python、无 ROS，最容易单步验证 | 2~3 h |
| 3 | `test/test_geometry.py` | 用测试反推每个函数的约定 | 30 min |
| 4 | `robomini_vision/detector.py` | 传统视觉部分，和图像直接对应 | 2 h |
| 5 | `test/test_detector.py` | 合成图测试，理解“4 根 vs 2 根” | 30 min |
| 6 | `robomini_vision/aim_node.py` | ROS 接线、跟踪、开火状态机 | 3 h |
| 7 | `config/params.yaml` + `launch/aim.launch.py` | 参数如何进入节点 | 30 min |
| 8 | 仿真侧（可选） | 明白 3 发/s、mode 语义从哪来 | 2 h |

**不要**一上来读 `aim_node.py` 的 500 行；它大部分是 ROS 样板和调试输出，核心只有 `on_image()` 一条主线。

---

## 2. 全局数据流（对应到函数）

```
/camera/image_raw ─┐
/camera/camera_info ├─► AimNode.on_image()                    aim_node.py:261
/gimbal_to_vision ──┘        │
                             ├─► RuneDetector.detect()          detector.py:173
                             │       ├─ mask()                  detector.py:99
                             │       ├─ bars()                  detector.py:110
                             │       ├─ _cluster()              detector.py:142
                             │       └─ 4根→pending / 2根→active
                             │
                             ├─► geometry.pixel_to_plane()      geometry.py:239
                             │       ├─ camera_pose()           geometry.py:201
                             │       ├─ pixel_ray()             geometry.py:215
                             │       └─ ray_plane()             geometry.py:228
                             │
                             ├─► geometry.snap_to_rune()        geometry.py:281
                             ├─► geometry.aim_at()              geometry.py:354
                             │       ├─ muzzle_position()       geometry.py:348
                             │       └─ solve_pitch()           geometry.py:316
                             │
                             ├─► _update_track()/_predict_theta() aim_node.py:228/252
                             └─► _publish_command()             aim_node.py:364
                                      │
                                      ▼
                              /vision_to_gimbal (mode 1/2)
```

---

## 3. 逐文件读法

### 3.1 `geometry.py`（先读这个）

重点函数：

| 行 | 函数 | 读的时候问自己 |
|---|---|---|
| 42~84 | `CAMERA_OFFSET` / `MUZZLE_OFFSET` / `PITCH_PIVOT_OFFSET` / `R_ROS_IN_PL` / `TEAM_GEOMETRY` | 三个安装偏移分别是什么？为什么俯仰轴不在 `pitch_link` 原点上？ |
| 187 | `pitch_link_origin(side, yaw, pitch)` | 俯仰时 `pitch_link` 原点为什么会平移？ |
| 201 | `camera_pose(side, yaw, pitch)` | 相机位置为什么还要加 `Rz(β+yaw)·Rx(pitch)·offset`？ |
| 215 | `pixel_ray(u,v,k)` | 像素如何变成归一化射线？`fx, cx` 从哪来？ |
| 228 | `ray_plane(...)` | 为什么能和 `y=∓0.116` 求交？`t` 的符号代表什么？ |
| 239 | `pixel_to_plane(...)` | 这一步得到的是“靶心”还是“靶面上任意一点”？ |
| 263 | `target_point(side, theta)` | 为什么靶心一定在半径 0.35 的圆上？ |
| 281 | `snap_to_rune(...)` | `residual` 大说明什么？为什么能过滤背面靶？ |
| 293 | `target_quaternion(...)` | 位姿的 x/y/z 轴分别代表什么？ |
| 309 | `yaw_from_delta(...)` | 蓝方 `yaw=0` 朝 +Y、红方朝 −Y，公式为什么统一？ |
| 316 | `solve_pitch(...)` | 二分为什么成立？区间为什么是 −10°~+45°？ |
| 348 | `muzzle_position(...)` | 枪口为什么随 pitch 移动？ |
| 354 | `aim_at(...)` | 为什么要迭代 6 次？ |
| 374 | `flight_time(...)` | 这个时间后面给谁用？（预测提前量） |

> 注意 `PITCH_PIVOT_OFFSET = 0.145`：SDF 的 `<joint><pose>` 相对 child link，
> 俯仰关节轴在 `pitch_link` 原点上方 0.145 m。相机和枪口都绕这个轴转，
> `pitch_link_origin()` 负责补这段平移；忽略它会让 pitch≈0.3 rad 时枪口偏约 4 cm。

**最快的学习方式**：打开 Python REPL 直接调用：

```bash
cd ~/Gitclone/RoboMini_DoNotCrossMeTeam/members/Algorithm_A/code/ros2_ws/src/robomini_vision
/usr/bin/python3
```

```python
from robomini_vision import geometry as g
K = [1108.5118865966797, 0, 640, 0, 1108.5120105743408, 360, 0, 0, 1]

p = g.target_point("blue", 0.4)          # 蓝方机关圆上 theta=0.4 的靶心
uv = g.world_to_pixel(p, K, "blue", 0.2, 0.3)
print(uv)
print(g.pixel_to_plane(uv[0], uv[1], K, "blue", 0.2, 0.3))   # 应回到 p
print(g.aim_at("blue", p, 12.0))          # 应该打向 p 的 yaw/pitch
```

再把 `side` 换成 `"red"` 重复一次；红方能通过，说明你理解了 `base_yaw=π`。

### 3.2 `detector.py`

| 行 | 内容 | 关键点 |
|---|---|---|
| 33 附近 | `TEAM_HSV` | 蓝 H 上限 117 是为了避开 H=120 的蓝色场线 |
| 45 | `Detection` | 状态、像素、灯条数、ratio、quality 都在这里 |
| 61 | `RuneDetector.__init__` | 阈值/聚类半径/最小绿通道都可参数化 |
| 99 | `mask()` | HSV 阈值 + 3×3 开运算 |
| 110 | `bars()` | 连通域过滤：面积、长宽、**G 通道**（去掉纯色场线） |
| 142 | `_cluster()` | 单链接聚类：距离 < 85 px 的灯条属于同一块靶 |
| 173 | `detect()` | 面积加权中心 → PCA → 4 根 pending / 2 根 active → quality |
| 226 | `draw_detections()` | 绿色 pending、橙色 active |

读的时候重点想清楚：

- 为什么 pending 的 4 根灯条质心 = 靶心？（对称布局）
- 为什么 active 的 2 根灯条中点 = 靶心？（反向对称）
- `ratio` 为什么能区分“十字”和“两条平行线”？
- 为什么场线的 G 通道≈0，而灯条 G 通道很大？

### 3.3 `aim_node.py`

这是 ROS 接线层。先只看 `on_image()`（261 行）的主干，其他都是辅助：

```
on_image:
  1. 限频 process_rate
  2. cv_bridge 转 BGR
  3. detector.detect
  4. 对每个 pending: _track_theta → 像素到 3D + 吸附圆
  5. 选一个（优先靠近上帧预测）
  6. _update_track → 估 ω
  7. _predict_theta → 加提前量
  8. aim_at → yaw/pitch
  9. 对准 + 质量 + 稳定帧数 → mode 2，否则 mode 1
 10. 发布命令/位姿/调试图/日志
 11. 没目标 → 短时外推 / 回机关中心搜索
```

其他函数按需看：

| 行 | 函数 | 作用 |
|---|---|---|
| 50 | `__init__` | 参数、订阅/发布、状态初始化 |
| 165 | `on_gimbal` | 拿实测 yaw/pitch、弹数 |
| 179 | `on_hit` | 命中统计（来自 `/rune/hit`） |
| 200 | `_track_theta` | 像素→平面→吸附圆；残差过大丢弃 |
| 214 | `_estimate_omega` | 角度解包 + 线性拟合 |
| 228 | `_update_track` | 目标切换检测（跳变 >0.4 rad 重置） |
| 252 | `_predict_theta` | `θ + ω·(t_flight + lead_latency)` |
| 261 | `on_image` | **主线** |
| 364 | `_publish_command` | 前馈、mode、发布 |
| 394 | `_publish_pose` | `/vision/target_pose` |
| 409 | `_debug` | 画框/HUD/调试图/存图 |
| 473 | `_log_state` | 1 Hz 日志 |

注意：**节点是单线程 `rclpy.spin`**，图像回调里做检测；`process_rate` 限频到 20 Hz，调试图 10 Hz，所以不会把 CPU 打满。

---

## 4. 跟着一帧走（把日志和代码对上）

以固定靶阶段的一条日志为例（数值来自实测，做了四舍五入）：

```
pend px=(644,470) n=4 q=0.96
pose=(+0.321,-0.116,+1.067) theta=+0.410
aim=(-0.163,+0.344) meas=(-0.161,+0.343)
err=(-0.10,+0.06)deg aligned=True fire=False shots=0 hits=0
```

对照代码：

1. `detector.detect()` 在 `(644,470)` 找到 4 根蓝灯条 → `pending`，`quality≈0.96`；
2. `pixel_to_plane()`：
   - `d = ((644-640)/1108.5, (470-360)/1108.5, 1) ≈ (0.0036, 0.0993, 1)`
   - 相机在 `(0, -2.034, 0.570)`，光轴朝 +Y；
   - 与 `y=-0.116` 求交 → `p ≈ (0.321, -0.116, 1.067)`；
3. `snap_to_rune()`：`θ=atan2(1.067-0.928, 0.321)=0.410`，吸附到圆上，残差几毫米；
4. `aim_at()`：
   - 枪口 `(0, -1.975, 0.495)`（pitch 会移动它）
   - `yaw≈-0.163`（蓝方朝 +Y，目标在右前方 → 负 yaw）
   - 解弹道得 `pitch≈0.344`（约 19.7°）
5. `_publish_command(mode=1)`；云台伺服到位后 `meas≈(-0.161, 0.343)`，误差 0.1°；
6. 下一帧 `aligned=True` → `mode=2`，launcher 以 3 发/s 发球；
7. 命中后 `/rune/hit` 给出 `valid=true, score=30`。

建议你在 `pixel_to_plane`、`snap_to_rune`、`aim_at` 三处各加一行 `print`，用 `./run.sh fire:=false` 跑 5 秒，观察数值是否和日志一致。

---

## 5. 动手实验（比读十遍有用）

| 实验 | 怎么改 | 预期现象 | 学到什么 |
|---|---|---|---|
| 放宽蓝色 H 上限 | `detector.py` 的 `TEAM_HSV` 117→120 | 蓝色场线被当成灯条，出现假 active | 为什么要卡 H 上限 |
| 关掉 G 通道过滤 | `min_green: 0` | 红色场线/logo 被识别成 active | 纯色场线 vs 带白灯条 |
| 把 `fire` 关掉 | `./run.sh fire:=false` | HUD `fire=False`，云台仍跟踪 | mode 1/2 的区别 |
| 把提前量设为 0 | `lead_latency:=0.0`，测 big | 高速段落在靶后，命中率下降 | 预测的作用 |
| 降低处理频率 | `process_rate:=5` | 云台明显滞后、big 打不中 | 采样率与控制延迟 |
| 放大吸附容差 | `max_snap_error:=0.005` | pending 时有时无 | 圆约束在过滤什么 |
| 打红方 | `./run.sh side:=red` | 红方同样工作 | `base_yaw=π` 的必要性 |
| 看真值误差 | `compare_ground_truth:=true` | 日志出现 `gt_err=xx mm` | 位姿解算精度 |

改完 Python 文件或 `params.yaml` 后，重新执行 `./build.sh`（colcon 很快），再重启 `./run.sh`；`--symlink-install` 在这里只是安装方式，不保证源码热更新。改 C++ 仿真插件才需要重编仿真。

---

## 6. 调试工具

```bash
# 识别画面（最直观）
ros2 run rqt_image_view rqt_image_view /vision/debug_image

# 待激活靶位姿
ros2 topic echo /vision/target_pose --once

# 云台实测与弹数
ros2 topic echo /gimbal_to_vision --once
ros2 topic echo /launcher/blue/state --once

# 命中与比分
ros2 topic echo /rune/hit
ros2 topic echo /score --once

# 与仿真真值对比（只诊断）
./run.sh compare_ground_truth:=true

# 保存标注图
./run.sh save_dir:=$PWD/Pic/vision_debug save_every:=2.0

# 单元测试
cd ros2_ws/src/robomini_vision
/usr/bin/python3 -m pytest -q
/usr/bin/python3 -m pytest -q -k geometry
/usr/bin/python3 -m pytest -q -k detector
```

学习时建议在以下位置打断点/加日志（ROS 节点不方便断点，优先日志）：

- `aim_node.py:200` `_track_theta` 返回前：打印 `point/theta/residual`
- `aim_node.py:261` `on_image`：打印 `len(pending)`、最终 `mode`
- `aim_node.py:364` `_publish_command`：打印 `yaw,pitch,mode`
- `geometry.py:239` `pixel_to_plane`：打印 `d/t/p`

---

## 7. 常见误区（读代码时最容易卡住）

1. **`yaw` 是关节角，不是世界方位角**：`0` 指本方前方（蓝 +Y、红 −Y），正 = 向左。
2. **红方所有世界坐标都多一个 `base_yaw=π`**：`TEAM_GEOMETRY` 里已经处理，但自己写公式时容易忘。
3. **`GimbalToVision.q` 在仿真红方不含安装偏航**：所以本包用 `yaw/pitch` 算相机位姿；这不是“多此一举”。
4. **靶的编号 `i` 是按初始角度 `θ0` 固定的**，机关转动后 `target_angles` 不再有序。
5. **`pending` 是唯一有效靶**；`active` 已打过，不能再打。
6. **日志里的 `pose` 是当前帧测量值，`target` 是加了提前量的预测值**；`compare_ground_truth` 比的是前者。
7. **工程没有 TF**：相机外参是常量，写死自 `launcher/model.sdf`；改相机安装位置必须同步改常量。
8. **图像是 best-effort QoS**：订阅必须 `qos_profile_sensor_data`，否则一帧都收不到。
9. **`mode=2` 是“按住扳机”**：持续发布才连发；不满足条件要主动回 `mode=1`。
10. **射速 3 发/s 是 launcher_node 与插件双重限制**；发得再快也不会更密。
11. **目标切换会让 `settle` 清零**：新 pending 需要连续 2 帧稳定才允许开火，避免打错靶。
12. **`res` 是吸附残差（毫米）**：不是像素误差；大残差通常说明检测到了背面/场线。

---

## 8. 建议的学习计划

### 第 1 天：几何 + 检测

- 上午：`geometry.py` + `test_geometry.py`，手推一遍“像素→平面→圆→yaw/pitch”；
- 下午：`detector.py` + `test_detector.py`，用 `color_detection.py` 调一次 HSV；
- 晚上：`./run.sh fire:=false`，把日志数值和代码对上。

### 第 2 天：ROS 节点 + 闭环

- 上午：`aim_node.py` 的 `on_image` 主线，画一张自己的流程图；
- 下午：测 big（`set_mode big`，a/ω 取极端值），观察 `omega/lead/err`；
- 晚上：改 `lead_latency`、`process_rate`、`fire_tolerance` 做对比实验。

### 进阶

- 用 `ros2 bag record` 录一段相机+云台，离线回放调检测；
- 把 `snap_to_rune` 换成靶板四角 `solvePnP`，对比位姿；
- 把线性 `ω` 预测换成 Kalman/常加速度；
- 把 `detector` 的 HSV 换成自适应亮度/白平衡。

---

## 9. 仿真侧只读三处（理解接口来源）

如果想知道“为什么是 3 发/s、mode 2 到底做了什么”，看这三处就够：

| 文件 | 位置 | 内容 |
|---|---|---|
| `robomini_sim/.../launcher_node.py` | `_on_vision`、`_fire`、`_publish_gimbal_to_vision` | ROS 指令 → gz JSON；限速；`/gimbal_to_vision` 回传 |
| `robomini_sim/.../rune_referee.py` | `_srv_set_mode`、`_on_gz_hit`、`_sync_outputs` | 裁判状态机、模式/灯效、命中判定 |
| `robomini_sim/gz_plugins/src/RobominiSim.cc` | `ServoAxis`、`UpdateRunes`、`DetectHit`、`Fire` | 云台伺服、机关转速、扫掠命中、发球 |

对应接口定义：

```
robomini_interfaces/msg/VisionToGimbal.msg
robomini_interfaces/msg/GimbalToVision.msg
robomini_interfaces/msg/RuneState.msg
robomini_interfaces/srv/SetRuneMode.srv
```

先读 msg/srv 的注释，再读节点实现；注释里已经把字段语义、坐标系、频率写清楚了。

---

## 10. 一句话

**先跑、再画数据流、然后按 `geometry → detector → aim_node` 的顺序读，最后用改参数和日志验证每一段。**
不要从 `aim_node.py` 第一行开始读；把它当成“把前面两个模块接起来”的胶水，会轻松很多。
