"""시황 영상 렌더(클라우드·로컬 공용). 사용: python render_ep.py 대본.json 시작프레임 끝프레임 출력.mp4
프레임 번호만으로 그림을 정하므로 어디서 잘라도 이어 붙이면 같은 영상이 됨."""
import sys, os, json, math, subprocess, numpy as np, cv2
from PIL import Image, ImageDraw, ImageFont
HERE = os.path.dirname(os.path.abspath(__file__))
W, H, FPS = 1920, 1080, 30
FF = os.environ.get("FFMPEG", "ffmpeg")
FONT = HERE + "/fonts/NotoSansCJK-Bold.ttc"
def font(s): return ImageFont.truetype(FONT, s, index=1)  # KR
# ---------- 대본 → 시간표 (줄 길이로 시간 배분, 총 180초) ----------
S = json.load(open(sys.argv[1])); L = S["lines"]
w = np.array([len(t) for _, t in L], float); dur = w / w.sum() * 180.0
st = np.concatenate([[0], np.cumsum(dur)])
NF = int(round(st[-1] * FPS))
def line_at(t): return min(int(np.searchsorted(st, t, side="right") - 1), len(L) - 1)
# ---------- 고양이 라이브러리(클립 프레임 미리 풀기) ----------
CROP = {"멍": (228, 0, 845, 704, 472, 539), "모": (254, 0, 1168, 704, 410, 316)}
def load(name):
    who = name[0]; x0, y0, x1, y1, cw, ch = CROP[who]
    p = subprocess.run([FF, "-v", "error", "-i", f"{HERE}/cats/{name}.mp4", "-vf",
        f"crop={x1-x0}:{y1-y0}:{x0}:{y0},scale={cw}:{ch}:flags=lanczos,fps=30", "-f", "rawvideo", "-pix_fmt", "rgb24", "-"],
        capture_output=True, check=True)
    return np.frombuffer(p.stdout, np.uint8).reshape(-1, ch, cw, 3)
LIB = {k: load(k) for k in ["멍_말하기A", "멍_말하기B", "멍_듣기", "모_말하기A", "모_말하기B", "모_듣기"]}
def pingpong(a, i):
    n = len(a); c = 2 * n - 2; i %= c; return a[i if i < n else c - i]
def cat_frame(who, t):
    i = line_at(t); spk = "멍" if L[i][0] == "멍" else "모"
    key = f"{who}_말하기{'AB'[i % 2]}" if spk == who else f"{who}_듣기"
    f = int((t - st[i]) * FPS) + i * 37
    img = pingpong(LIB[key], f).astype(np.float32)
    # 줄이 바뀔 때 0.2초 겹쳐 넘기기
    if i > 0 and t - st[i] < 0.2:
        pk = f"{who}_말하기{'AB'[(i-1) % 2]}" if (L[i-1][0] == who) else f"{who}_듣기"
        a = (t - st[i]) / 0.2; img = img * a + pingpong(LIB[pk], int((t - st[i-1]) * FPS) + (i-1) * 37).astype(np.float32) * (1 - a)
    return img, spk == who
def breathe(img, t, seed):
    h, w_ = img.shape[:2]; s = 1.012 + 0.006 * math.sin(2 * math.pi * t / 3.7 + seed)
    dx = 2.2 * math.sin(2 * math.pi * t / 7.9 + seed * 2); dy = 1.2 * math.sin(2 * math.pi * t / 3.7 + seed)
    M = np.array([[s, 0, (1 - s) * w_ / 2 + dx], [0, s, (1 - s) * h + dy]], np.float32)
    return cv2.warpAffine(img, M, (w_, h), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)
def label_img(text, col):
    im = Image.new("RGBA", (220, 56), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    d.rounded_rectangle((0, 0, 219, 55), 14, fill=col + (235,)); d.text((110, 27), text, font=font(30), fill="white", anchor="mm")
    return np.array(im)
LAB = {"멍": label_img("멍뭉이", (210, 60, 60)), "모": label_img("모카 · 뉴욕", (40, 150, 90))}
RECT = {"멍": (1420, 520), "모": (1490, 160)}
def blend(fr, rgba, x, y):
    h, w_ = rgba.shape[:2]; a = rgba[..., 3:4].astype(np.float32) / 255
    roi = fr[y:y+h, x:x+w_].astype(np.float32); fr[y:y+h, x:x+w_] = (roi * (1 - a) + rgba[..., :3] * a).astype(np.uint8)
def put(fr, who, t):
    img, on = cat_frame(who, t); img = breathe(img, t, 0.0 if who == "멍" else 1.7)
    x, y = RECT[who]; h, w_ = img.shape[:2]
    cv2.rectangle(fr, (x - 6, y - 6), (x + w_ + 5, y + h + 5), (255, 214, 90) if on else (70, 90, 130), 6)
    fr[y:y+h, x:x+w_] = np.clip(img, 0, 255).astype(np.uint8)
    blend(fr, LAB[who], x + 12, y + h - 70)
# ---------- 배경: 움직이는 네이비 + 격자 + 제목 + 차트 + 자막 ----------
yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
def wrap(text, f, maxw):
    out, cur = [], ""
    for wd in text.split(" "):
        nx = (cur + " " + wd).strip()
        if f.getlength(nx) > maxw and cur: out.append(cur); cur = wd
        else: cur = nx
    return out + [cur]
CAP = {}
def caption(i):
    if i not in CAP:
        f = font(46); ls = wrap(L[i][1], f, 1220); hh = 40 + 64 * len(ls)
        im = Image.new("RGBA", (1300, hh), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
        d.rounded_rectangle((0, 0, 1299, hh - 1), 22, fill=(8, 14, 34, 215))
        for k, s in enumerate(ls): d.text((40, 20 + 64 * k), s, font=f, fill=(255, 236, 160) if L[i][0] == "멍" else (190, 240, 210))
        CAP[i] = np.array(im)
    return CAP[i]
TITLE = np.array((lambda im: (ImageDraw.Draw(im).text((0, 0), S["title"], font=font(54), fill="white"), im)[1])(Image.new("RGBA", (1300, 80), (0, 0, 0, 0))))
rng = np.random.default_rng(7); price = np.cumsum(rng.normal(0.05, 1, 8000)) + 100
def frame(n):
    t = n / FPS
    g = 0.5 + 0.5 * np.sin(xx / 320 + t * 0.6) * np.cos(yy / 280 - t * 0.4)
    fr = np.stack([12 + 14 * g, 22 + 22 * g, 52 + 40 * g], -1).astype(np.uint8)
    off = int(t * 30) % 90; fr[:, off::90] = (34, 52, 92); fr[off::90, :] = (34, 52, 92)
    blend(fr, TITLE, 90, 60)
    # 차트 패널
    cv2.rectangle(fr, (90, 170), (1340, 700), (20, 34, 70), -1)
    i = line_at(t); seg = price[i * 120: i * 120 + 60 + int((t - st[i]) * 40)]
    xs = np.linspace(130, 1300, len(seg)).astype(np.int32); ys = (660 - (seg - seg.min()) / (np.ptp(seg) + 1e-6) * 440).astype(np.int32)
    cv2.polylines(fr, [np.stack([xs, ys], 1)], False, (120, 230, 140), 6, cv2.LINE_AA)
    cv2.circle(fr, (int(xs[-1]), int(ys[-1])), 13, (255, 200, 70), -1, cv2.LINE_AA)
    c = caption(i); blend(fr, c, 90, min(1050 - c.shape[0], 730))
    put(fr, "모", t); put(fr, "멍", t)
    return fr
if __name__ == "__main__":
    s, e, out = int(sys.argv[2]), min(int(sys.argv[3]), NF), sys.argv[4]
    enc = subprocess.Popen([FF, "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
        "-c:v", "libx264", "-crf", "19", "-preset", "veryfast", "-g", "30", "-keyint_min", "30", "-sc_threshold", "0", "-pix_fmt", "yuv420p", out], stdin=subprocess.PIPE)
    for n in range(s, e):
        enc.stdin.write(frame(n).tobytes())
        if (n - s) % 600 == 0: print(out, f"{(n - s) / max(1, e - s) * 100:.0f}%", flush=True)
    enc.stdin.close(); enc.wait(); print("done", out, e - s, flush=True)
