"""Figuras del informe IEEE (salida en PDF vectorial + PNG de control)."""
import sys
from pathlib import Path

import cv2
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch
import torch

repo = Path(sys.argv[1])
out = Path(sys.argv[2])
out.mkdir(parents=True, exist_ok=True)
plt.rcParams.update({"font.family": "serif", "font.size": 8, "axes.linewidth": 0.6})
COL_W = 3.5  # ancho de columna IEEE en pulgadas


def save(fig, name):
    fig.savefig(out / f"{name}.pdf", bbox_inches="tight", pad_inches=0.02)
    fig.savefig(out / f"{name}.png", bbox_inches="tight", pad_inches=0.02, dpi=200)
    plt.close(fig)


# --- Fig. 1: pipeline -------------------------------------------------------
steps = [
    ("Cámara 30 fps|+ GPS (GPX)", "Captura"),
    ("YOLO26-S (V4)|+ ByteTrack", "Visión"),
    ("ROI y|severidad|por área", "Visión"),
    ("Georreferencia|(GPX +|calibración)", "Visión"),
    ("PostGIS|DBSCAN|2,5 m", "Backend"),
    ("API REST|Django", "Backend"),
    ("Mapa React|+ Leaflet|+ feedback", "Frontend"),
]
steps = [(t.replace("|", chr(10)), g) for t, g in steps]
colors = {"Captura": "#dbe7f5", "Visión": "#e3f1df", "Backend": "#f6e6d4", "Frontend": "#efe0f2"}
n = len(steps)
fig, ax = plt.subplots(figsize=(7.16, 1.0))
ax.set_xlim(0, n); ax.set_ylim(0, 1); ax.axis("off")
w, h, y = 0.80, 0.66, 0.25
for i, (txt, grp) in enumerate(steps):
    x = i + 0.1
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.02,rounding_size=0.05",
                                fc=colors[grp], ec="#444", lw=0.6))
    ax.text(x + w / 2, y + h / 2, txt, ha="center", va="center", fontsize=6.2, linespacing=1.1)
    if i < n - 1:
        ax.annotate("", xy=(i + 1.1, y + h / 2), xytext=(x + w + 0.02, y + h / 2),
                    arrowprops=dict(arrowstyle="-|>", lw=0.7, color="#333"))
for grp, x0, x1 in [("Captura", 0, 1), ("Procesamiento offline (Python)", 1, 4),
                    ("Backend", 4, 6), ("Frontend", 6, 7)]:
    ax.text((x0 + x1) / 2, 0.06, grp, ha="center", va="bottom", fontsize=6.8, style="italic",
            color="#333")
save(fig, "fig_pipeline")

# --- Fig. 2: mAP por tamaño (V4, Roboflow) ----------------------------------
cats = ["Todos", "Chicos", "Medianos", "Grandes"]
m50 = [60.8, 0.0, 43.2, 75.3]
m5095 = [28.3, 0.0, 15.8, 38.3]
m75 = [27.3, 0.0, 8.3, 42.5]
fig, ax = plt.subplots(figsize=(COL_W, 1.55))
import numpy as np
x = np.arange(len(cats)); bw = 0.26
for k, (vals, lab, c) in enumerate([(m50, "mAP@50", "#3b6ea8"), (m75, "mAP@75", "#7fa7d6"),
                                    (m5095, "mAP@50-95", "#c9d9ee")]):
    bars = ax.bar(x + (k - 1) * bw, vals, bw, label=lab, color=c, ec="#333", lw=0.4)
    for b, v in zip(bars, vals):
        ax.text(b.get_x() + b.get_width() / 2, v + 1.2, f"{v:.1f}", ha="center", va="bottom",
                fontsize=5.4)
ax.set_xticks(x, cats); ax.set_ylabel("%"); ax.set_ylim(0, 85)
ax.spines[["top", "right"]].set_visible(False)
ax.legend(ncol=3, fontsize=6.5, frameon=False, loc="lower center", bbox_to_anchor=(0.5, 1.0))
ax.grid(axis="y", lw=0.3, alpha=0.6)
save(fig, "fig_map_tamano")

# --- Fig. 3: curvas de validación V4 (desde el checkpoint) -------------------
ck = torch.load(repo / "weights" / "weights_v4_monoclass.pt", map_location="cpu", weights_only=False)
tr = ck["train_results"]
n = len(tr["metrics/mAP50(B)"])
it = list(range(1, n + 1))
fig, ax = plt.subplots(figsize=(COL_W, 1.45))
for key, lab, c in [("metrics/precision(B)", "Precisión", "#3b6ea8"),
                    ("metrics/recall(B)", "Recall", "#d0853b"),
                    ("metrics/mAP50(B)", "mAP@50", "#4f9a4f"),
                    ("metrics/mAP50-95(B)", "mAP@50-95", "#8a5aa8")]:
    ax.plot(it, [v * 100 for v in tr[key]], lw=0.8, label=lab, color=c)
ax.set_xlabel("Registro de validación (época)"); ax.set_ylabel("%"); ax.set_ylim(0, 100)
ax.spines[["top", "right"]].set_visible(False)
ax.legend(ncol=4, fontsize=6.2, frameon=False, loc="lower center", bbox_to_anchor=(0.5, 1.0))
ax.grid(lw=0.3, alpha=0.6)
save(fig, "fig_curvas_v4")

# --- Fig. 4: ejemplo de detección real --------------------------------------
from ultralytics import YOLO
img_path = repo / "capture/record_tests/recording_frames/sesion_20261107_174903/sesion_20261107_174903_f000214.jpg"
model = YOLO(str(repo / "weights" / "weights_v4_monoclass.pt"))
r = model.predict(str(img_path), conf=0.3, verbose=False)[0]
im = cv2.imread(str(img_path))
H = im.shape[0]
cv2.line(im, (0, int(0.45 * H)), (im.shape[1], int(0.45 * H)), (0, 200, 255), 3)
for (x1, y1, x2, y2), c in zip(r.boxes.xyxy.tolist(), r.boxes.conf.tolist()):
    cv2.rectangle(im, (int(x1), int(y1)), (int(x2), int(y2)), (0, 0, 255), 4)
    cv2.putText(im, f"bache {c:.2f}", (int(x1), int(y1) - 10), cv2.FONT_HERSHEY_SIMPLEX, 1.3,
                (0, 0, 255), 3)
im = cv2.resize(im, (1200, int(1200 * H / im.shape[1])))
cv2.imwrite(str(out / "fig_ejemplo.jpg"), im, [cv2.IMWRITE_JPEG_QUALITY, 85])
print("listo:", sorted(p.name for p in out.iterdir()))
