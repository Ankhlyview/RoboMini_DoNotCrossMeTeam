import cv2
import numpy as np
import json
import os

# ============ 全局变量 ============
WINDOW = "Color Tuner"
CONFIG_FILE = "hsv_config.json"
IMAGE_PATH = r"D:\robomini\team-progress\members\Algorithm_A\Pic\robomini_214153.png"

# 6 个滑动条对应 HSV 上下限
TAGS = ["H_min", "H_max", "S_min", "S_max", "V_min", "V_max"]
INIT = [0, 180, 0, 255, 0, 255]

# 上次保存的阈值（按 s 保存、l 加载）
saved_lower = None
saved_upper = None


def nothing(x):
    pass


def build_trackbars():
    cv2.namedWindow(WINDOW, cv2.WINDOW_NORMAL)
    cv2.resizeWindow(WINDOW, 600, 200)

    # H: 0~180 (OpenCV 特性), S/V: 0~255
    cv2.createTrackbar("H_min", WINDOW, INIT[0], 180, nothing)
    cv2.createTrackbar("H_max", WINDOW, INIT[1], 180, nothing)
    cv2.createTrackbar("S_min", WINDOW, INIT[2], 255, nothing)
    cv2.createTrackbar("S_max", WINDOW, INIT[3], 255, nothing)
    cv2.createTrackbar("V_min", WINDOW, INIT[4], 255, nothing)
    cv2.createTrackbar("V_max", WINDOW, INIT[5], 255, nothing)


def read_trackbars():
    vals = [cv2.getTrackbarPos(t, WINDOW) for t in TAGS]
    lower = np.array(vals[0:6:2], dtype=np.uint8)   # [H_min, S_min, V_min]
    upper = np.array(vals[1:6:2], dtype=np.uint8)   # [H_max, S_max, V_max]
    return lower, upper


def set_trackbars(lower, upper):
    """从数组写入滑动条（用于加载配置）"""
    vals = [lower[0], upper[0], lower[1], upper[1], lower[2], upper[2]]
    for t, v in zip(TAGS, vals):
        cv2.setTrackbarPos(t, WINDOW, int(v))


def get_mask(hsv, lower, upper, red_wrap=False):
    """
    生成掩膜。
    red_wrap=True 时把红色首尾相接的两段都包含进来
    （即 H 范围内允许 0 和 180 同时生效）
    """
    if red_wrap:
        # 把 [H_min, H_max] 理解成"环绕"区间
        # 例如 H_min=170, H_max=10 表示 170~180 和 0~10
        l1 = np.array([lower[0], lower[1], lower[2]])
        u1 = np.array([180,       upper[1], upper[2]])
        l2 = np.array([0,         lower[1], lower[2]])
        u2 = np.array([upper[0], upper[1], upper[2]])
        mask = cv2.inRange(hsv, l1, u1) | cv2.inRange(hsv, l2, u2)
    else:
        mask = cv2.inRange(hsv, lower, upper)
    return mask


def put_text_cn(img, text, org, color=(0, 255, 0)):
    """用简单方式画英文标签（中文需要 PIL，这里用英文避免依赖）"""
    cv2.putText(img, text, org, cv2.FONT_HERSHEY_SIMPLEX, 0.55, color, 1, cv2.LINE_AA)


def main(image_path=IMAGE_PATH, red_wrap=False):
    global saved_lower, saved_upper

    # 支持中文路径
    img = cv2.imdecode(np.fromfile(IMAGE_PATH, dtype=np.uint8), cv2.IMREAD_COLOR)
    if img is None:
        raise FileNotFoundError(f"无法读取图片: {image_path}")

    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    build_trackbars()

    print("=== 操作说明 ===")
    print("Q / Esc : 退出")
    print("S       : 保存当前阈值到", CONFIG_FILE)
    print("L       : 从文件加载阈值")
    print("R       : 切换红色环绕模式（红色需要特殊处理时用）")
    print("空格    : 打印当前 lower/upper 到控制台\n")

    # 缩放窗口，避免大图撑满屏幕
    scale = 1.0
    h, w = img.shape[:2]
    if max(h, w) > 1000:
        scale = 1000 / max(h, w)
        disp_img = cv2.resize(img, None, fx=scale, fy=scale)
        disp_hsv = cv2.resize(hsv, None, fx=scale, fy=scale)
    else:
        disp_img, disp_hsv = img, hsv

    while True:
        lower, upper = read_trackbars()

        # 防止 min > max
        if lower[0] > upper[0]:
            lower[0], upper[0] = upper[0], lower[0]

        mask = get_mask(disp_hsv, lower, upper, red_wrap=red_wrap)
        result = cv2.bitwise_and(disp_img, disp_img, mask=mask)

        # 在结果上标注数值，方便抄回代码
        info = f"H[{lower[0]},{upper[0]}] S[{lower[1]},{upper[1]}] V[{lower[2]},{upper[2]}]"
        put_text_cn(result, info, (10, 25))
        put_text_cn(result, f"red_wrap={'ON' if red_wrap else 'OFF'}", (10, 50),
                    (0, 255, 255) if red_wrap else (200, 200, 200))

        # 三窗口并排显示
        cv2.imshow(WINDOW, np.vstack([
            np.hstack([disp_img, cv2.cvtColor(mask, cv2.COLOR_GRAY2BGR)]),
            np.hstack([result, np.zeros_like(disp_img)])
        ]))

        key = cv2.waitKey(30) & 0xFF
        if key in (ord("q"), 27):
            break

        elif key == ord(" "):
            print(f"lower = [{lower[0]:>3}, {lower[1]:>3}, {lower[2]:>3}]"
                  f"  upper = [{upper[0]:>3}, {upper[1]:>3}, {upper[2]:>3}]")

        elif key == ord("s"):
            cfg = {"lower": lower.tolist(), "upper": upper.tolist(),
                   "red_wrap": red_wrap}
            with open(CONFIG_FILE, "w", encoding="utf-8") as f:
                json.dump(cfg, f, indent=2)
            print(f"✅ 已保存到 {CONFIG_FILE}: {cfg}")

        elif key == ord("l"):
            if os.path.exists(CONFIG_FILE):
                with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                    cfg = json.load(f)
                set_trackbars(np.array(cfg["lower"]), np.array(cfg["upper"]))
                red_wrap = cfg.get("red_wrap", False)
                print(f"📂 已加载: {cfg}")
            else:
                print("⚠️  配置文件不存在，先按 S 保存一次")

        elif key == ord("r"):
            red_wrap = not red_wrap
            print(f"🔁 红色环绕模式: {'ON' if red_wrap else 'OFF'}")

    cv2.destroyAllWindows()


if __name__ == "__main__":
    # 红色提取时把 red_wrap 设为 True
    main("test.jpg", red_wrap=False)