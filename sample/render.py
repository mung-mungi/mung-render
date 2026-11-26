"""테스트용 샘플 렌더: 1080p 네이비 배경 + 움직이는 격자 + 선 차트 + 반투명 합성.
사용: python render.py 시작프레임 끝프레임 출력.mp4  (프레임 번호만으로 그려서 어디서 잘라도 같은 그림)"""
import sys, subprocess, numpy as np, cv2
W, H, FPS = 1920, 1080, 30
s, e, out = int(sys.argv[1]), int(sys.argv[2]), sys.argv[3]
ff = sys.argv[4] if len(sys.argv) > 4 else "ffmpeg"
yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
rng = np.random.default_rng(7)
price = np.cumsum(rng.normal(0, 1, 2000)) + 100
blob = np.zeros((360, 360, 4), np.uint8)
cv2.circle(blob, (180, 180), 160, (60, 170, 240, 200), -1)
cv2.circle(blob, (180, 180), 110, (250, 250, 250, 230), -1)
p = subprocess.Popen([ff, "-loglevel", "error", "-y", "-f", "rawvideo", "-pix_fmt", "bgr24",
    "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-preset", "veryfast",
    "-crf", "20", "-pix_fmt", "yuv420p", "-g", "60", out], stdin=subprocess.PIPE)
for f in range(s, e):
    t = f / FPS
    # 움직이는 네이비 그라데이션 배경
    g = 0.5 + 0.5 * np.sin(xx / 300 + t * 0.8) * np.cos(yy / 260 - t * 0.5)
    img = np.stack([70 + 40 * g, 30 + 15 * g, 15 + 10 * g], -1).astype(np.uint8)
    # 흐르는 격자
    off = int(t * 40) % 80
    img[:, off::80] = (110, 70, 45); img[off::80, :] = (110, 70, 45)
    # 그려지는 선 차트
    n = 60 + int(t * 45)
    seg = price[f % 300: f % 300 + n]
    xs = np.linspace(160, 1500, len(seg)).astype(np.int32)
    ys = (780 - (seg - seg.min()) / (np.ptp(seg) + 1e-6) * 500).astype(np.int32)
    cv2.polylines(img, [np.stack([xs, ys], 1)], False, (80, 220, 120), 6, cv2.LINE_AA)
    cv2.circle(img, (int(xs[-1]), int(ys[-1])), 14, (60, 200, 255), -1, cv2.LINE_AA)
    cv2.putText(img, f"SAMPLE  {t:5.2f}s   {seg[-1]:7.2f}", (160, 160), cv2.FONT_HERSHEY_DUPLEX, 2.2, (255, 255, 255), 3, cv2.LINE_AA)
    # 오른쪽 아래 반투명 합성(고양이 자리 대신)
    x0, y0 = 1500 + int(20 * np.sin(t * 3)), 680
    roi = img[y0:y0+360, x0:x0+360].astype(np.float32)
    a = blob[..., 3:4] / 255.0
    img[y0:y0+360, x0:x0+360] = (roi * (1 - a) + blob[..., :3] * a).astype(np.uint8)
    img = cv2.GaussianBlur(img, (3, 3), 0)
    p.stdin.write(img.tobytes())
p.stdin.close(); p.wait()
