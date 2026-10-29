#!/usr/bin/env python3
"""
SomDeMala — interface gráfica

Rodando direto pelo Python (Ubuntu):
    sudo apt install ffmpeg libxcb-cursor0
    source ~/yt-env/bin/activate
    pip install -U yt-dlp PySide6
    python SomDeMala.py

Para gerar o executável, use build_linux.sh ou build_windows.ps1.
"""

import json
import math
import os
import re
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path

# ----------------------------------------------------------------------------
# Pastas de dados (funciona em Linux, Windows e macOS)
# ----------------------------------------------------------------------------
if sys.platform.startswith("win"):
    DADOS = Path(os.environ.get("APPDATA", Path.home())) / "SomDeMala"
elif sys.platform == "darwin":
    DADOS = Path.home() / "Library" / "Application Support" / "SomDeMala"
else:
    DADOS = Path.home() / ".local" / "share" / "baixador-playlist"
ARQ_HIST = DADOS / "historico.json"
ARQ_CONF = DADOS / "config.json"


if sys.stdout is None or sys.stderr is None:
    DADOS.mkdir(parents=True, exist_ok=True)
    _log = open(DADOS / "registro.log", "a", encoding="utf-8")
    sys.stdout = sys.stdout or _log
    sys.stderr = sys.stderr or _log

try:
    import yt_dlp
    from yt_dlp.utils import DownloadCancelled
except ImportError:
    sys.exit("yt-dlp não encontrado. Rode: pip install -U yt-dlp")

try:
    from PySide6.QtCore import (QAbstractAnimation, QEasingCurve, QPoint, QPointF,
                                QPropertyAnimation, QSequentialAnimationGroup, QSize, Qt,
                                QThread, QTimer, QUrl, Signal)
    from PySide6.QtGui import (QColor, QConicalGradient, QDesktopServices, QPainter, QPen,
                               QRadialGradient)
    from PySide6.QtWidgets import (QApplication, QFileDialog, QFrame, QGraphicsOpacityEffect,
                                   QHBoxLayout, QLabel, QLineEdit, QListWidget, QListWidgetItem,
                                   QMessageBox, QProgressBar, QPushButton, QScrollArea, QSlider,
                                   QSizePolicy, QSplitter, QSplitterHandle, QToolButton,
                                   QVBoxLayout, QWidget)
except ImportError:
    sys.exit("PySide6 não encontrado. Rode: pip install -U PySide6")



def pasta_do_app():
    if getattr(sys, "frozen", False):
        return Path(getattr(sys, "_MEIPASS", Path(sys.executable).parent))
    return Path(__file__).resolve().parent


def localizar_ffmpeg():
    nome = "ffmpeg.exe" if os.name == "nt" else "ffmpeg"
    for base in (pasta_do_app(), pasta_do_app() / "ffmpeg-bin"):
        if (base / nome).exists():
            return str(base)
    return None


FFMPEG_DIR = localizar_ffmpeg()


# ----------------------------------------------------------------------------
# Utilitários
# ----------------------------------------------------------------------------
def ler_json(caminho, padrao):
    try:
        return json.loads(caminho.read_text(encoding="utf-8"))
    except Exception:
        return padrao


def gravar_json(caminho, dados):
    DADOS.mkdir(parents=True, exist_ok=True)
    caminho.write_text(json.dumps(dados, ensure_ascii=False, indent=2), encoding="utf-8")


def pasta_musica_padrao():
    if sys.platform.startswith("linux"):
        try:
            saida = subprocess.run(["xdg-user-dir", "MUSIC"], capture_output=True,
                                   text=True, timeout=2).stdout.strip()
            if saida and saida != str(Path.home()):
                return Path(saida) / "Playlists YouTube"
        except Exception:
            pass
    for nome in ("Música", "Music", "Músicas"):
        if (Path.home() / nome).is_dir():
            return Path.home() / nome / "Playlists YouTube"
    return Path.home() / "Music" / "Playlists YouTube"


def limpar_nome(nome):
    return re.sub(r'[\\/:*?"<>|]', "_", nome).strip() or "Playlist"


def encurtar(caminho):
    casa = str(Path.home())
    return "~" + caminho[len(casa):] if caminho.startswith(casa) else caminho


def abrir_pasta(caminho):
    if Path(caminho).exists():
        QDesktopServices.openUrl(QUrl.fromLocalFile(caminho))


def repolir(w):
    w.style().unpolish(w)
    w.style().polish(w)


# ----------------------------------------------------------------------------
# Cores e temas
# ----------------------------------------------------------------------------
COR_PADRAO = "#f2a541"
PRESETS = ["#f2a541", "#ff6f61", "#e86fae", "#9b7bff", "#4f9dff", "#3fbf8a"]


def hsl(h, s, l):
    return QColor.fromHslF(h % 1.0, max(0.0, min(1.0, s)), max(0.0, min(1.0, l)))


def misturar(a, b, t):
    return QColor.fromRgbF(a.redF() * (1 - t) + b.redF() * t,
                           a.greenF() * (1 - t) + b.greenF() * t,
                           a.blueF() * (1 - t) + b.blueF() * t)


def luminancia(c):
    return 0.2126 * c.redF() + 0.7152 * c.greenF() + 0.0722 * c.blueF()


def montar_paleta(cor, tema):
    """cor=None mantém o visual original (fundo roxo + destaque âmbar)."""
    acento = QColor(cor or COR_PADRAO)
    branco, preto = QColor("#ffffff"), QColor("#000000")

    if cor is None:
        h, k = 280 / 360, 1.0
    else:
        h = acento.hslHueF()
        k = 0.0 if h < 0 else min(1.0, acento.hslSaturationF() * 1.3)
        h = max(h, 0.0)

    if tema == "escuro" and cor is None:
        p = {  # exatamente o visual da primeira versão
            "fundo": QColor("#1a1420"), "painel": QColor("#241b2c"), "cartao": QColor("#2c2236"),
            "borda": QColor("#382b44"), "campo": QColor("#1a1420"), "tag": QColor("#33263e"),
            "tag_hover": QColor("#3f2f4c"), "texto": QColor("#f3ece4"), "texto2": QColor("#d8cfe0"),
            "suave": QColor("#a597b0"), "fraco": QColor("#8f8399"), "rolagem": QColor("#43344f"),
            "off_bg": QColor("#4a3a3a"), "off_txt": QColor("#9b8f8f"),
        }
    elif tema == "escuro":
        p = {
            "fundo": hsl(h, .23 * k, .10), "painel": hsl(h, .24 * k, .14),
            "cartao": hsl(h, .22 * k, .17), "borda": hsl(h, .22 * k, .22),
            "campo": hsl(h, .23 * k, .10), "tag": hsl(h, .25 * k, .20),
            "tag_hover": hsl(h, .25 * k, .25), "texto": hsl(h, .30 * k, .93),
            "texto2": hsl(h, .20 * k, .84), "suave": hsl(h, .15 * k, .65),
            "fraco": hsl(h, .12 * k, .56), "rolagem": hsl(h, .20 * k, .27),
            "off_bg": hsl(h, .12 * k, .25), "off_txt": hsl(h, .08 * k, .58),
        }
    else:
        p = {
            "fundo": hsl(h, .28 * k, .92), "painel": hsl(h, .35 * k, .975),
            "cartao": hsl(h, .35 * k, .995), "borda": hsl(h, .20 * k, .85),
            "campo": hsl(h, .25 * k, .945), "tag": hsl(h, .35 * k, .91),
            "tag_hover": hsl(h, .35 * k, .87), "texto": hsl(h, .25 * k, .14),
            "texto2": hsl(h, .18 * k, .28), "suave": hsl(h, .12 * k, .42),
            "fraco": hsl(h, .10 * k, .56), "rolagem": hsl(h, .15 * k, .78),
            "off_bg": hsl(h, .12 * k, .86), "off_txt": hsl(h, .08 * k, .58),
        }

    escuro = tema == "escuro"
    p["acento"] = acento
    p["acento_hover"] = misturar(acento, branco, .18) if escuro else misturar(acento, preto, .10)
    p["sobre_acento"] = hsl(h, .5 * k, .10) if luminancia(acento) > .45 else branco
    if cor is None and escuro:
        p["sobre_acento"] = QColor("#2a1a08")
    p["tag_txt"] = misturar(acento, branco, .35) if escuro else misturar(acento, preto, .35)
    p["destaque"] = acento if escuro else misturar(acento, preto, .25)
    p["novo"] = misturar(p["cartao"], acento, .12)
    p["sucesso"] = QColor("#6fd0bf") if escuro else QColor("#22917f")
    p["sobre_sucesso"] = QColor("#10302b") if escuro else branco
    p["erro"] = QColor("#ff7a7a") if escuro else QColor("#c94040")
    return p


def montar_estilo(p):
    c = {k: v.name() for k, v in p.items()}
    return f"""
QWidget {{ color: {c['texto']}; font-family: "Ubuntu", "Segoe UI", "Noto Sans", sans-serif; font-size: 14px; }}
QWidget#raiz {{ background: {c['fundo']}; }}
QFrame#painel {{ background: {c['painel']}; border-radius: 18px; }}

QLabel#marca {{ color: {c['suave']}; font-size: 13px; font-weight: 600; }}
QLabel#titulo {{ font-size: 24px; font-weight: 700; }}
QLabel#sub {{ color: {c['suave']}; font-size: 13px; }}
QLabel#vazio {{ color: {c['fraco']}; font-size: 14px; }}
QLabel#nomePlaylist {{ font-size: 19px; font-weight: 700; color: {c['destaque']}; }}
QLabel#atual {{ color: {c['texto2']}; font-size: 13px; }}

QScrollArea, QWidget#listaInterna, QWidget#caixaProg {{ background: transparent; border: none; }}

QLineEdit {{
    background: {c['campo']}; border: 1px solid {c['borda']}; border-radius: 10px;
    padding: 13px 14px; font-size: 14px; selection-background-color: {c['acento']};
    selection-color: {c['sobre_acento']};
}}
QLineEdit:focus {{ border: 1px solid {c['acento']}; }}
QLineEdit:disabled {{ color: {c['fraco']}; }}

QPushButton#primario {{
    background: {c['acento']}; color: {c['sobre_acento']}; border: none; border-radius: 10px;
    padding: 13px; font-size: 15px; font-weight: 700;
}}
QPushButton#primario:hover {{ background: {c['acento_hover']}; }}
QPushButton#primario:disabled {{ background: {c['off_bg']}; color: {c['off_txt']}; }}

QPushButton#secundario {{
    background: transparent; color: {c['texto2']}; border: 1px solid {c['borda']};
    border-radius: 8px; padding: 7px 14px;
}}
QPushButton#secundario:hover {{ border-color: {c['acento']}; color: {c['destaque']}; }}
QPushButton#secundario:disabled {{ color: {c['fraco']}; border-color: {c['borda']}; }}

QPushButton#amostra {{
    background: {c['acento']}; border: 3px solid {c['painel']}; border-radius: 15px;
    min-width: 24px; max-width: 24px; min-height: 24px; max-height: 24px;
}}
QPushButton#amostra:hover {{ border-color: {c['borda']}; }}
QPushButton#iconeTema {{
    background: {c['painel']}; color: {c['texto2']}; border: 1px solid {c['borda']};
    border-radius: 15px; font-size: 15px;
    min-width: 28px; max-width: 28px; min-height: 28px; max-height: 28px; padding: 0;
}}
QPushButton#iconeTema:hover {{ border-color: {c['acento']}; color: {c['destaque']}; }}

QToolButton#trocar {{
    background: {c['painel']}; color: {c['texto2']}; border: 1px solid {c['borda']};
    border-radius: 15px; font-size: 16px; font-weight: 700;
}}
QToolButton#trocar:hover {{ border-color: {c['acento']}; color: {c['destaque']}; }}

QLabel#tag {{
    background: {c['tag']}; color: {c['tag_txt']}; border-radius: 7px;
    padding: 4px 10px; font-size: 12px;
}}
QLabel#tag:hover {{ background: {c['tag_hover']}; }}

QFrame#cartao {{ background: {c['cartao']}; border: 1px solid {c['borda']}; border-radius: 12px; }}
QFrame#cartao[novo="true"] {{ border: 1px solid {c['acento']}; background: {c['novo']}; }}
QLabel#cartaoNome {{ font-size: 15px; font-weight: 600; }}
QLabel#cartaoInfo {{ color: {c['suave']}; font-size: 12px; }}
QLabel#selo {{
    background: {c['sucesso']}; color: {c['sobre_sucesso']}; border-radius: 6px;
    padding: 2px 8px; font-size: 11px; font-weight: 700;
}}

QLabel#voador {{
    background: {c['acento']}; color: {c['sobre_acento']}; border-radius: 10px;
    padding: 10px 16px; font-size: 15px; font-weight: 700;
}}

QProgressBar {{ background: {c['campo']}; border: none; border-radius: 5px; max-height: 10px; min-height: 10px; }}
QProgressBar::chunk {{ background: {c['acento']}; border-radius: 5px; }}
QProgressBar#barraAtual {{ max-height: 6px; min-height: 6px; border-radius: 3px; }}
QProgressBar#barraAtual::chunk {{ background: {c['sucesso']}; border-radius: 3px; }}

QListWidget {{ background: {c['campo']}; border: none; border-radius: 10px; padding: 6px; outline: none; }}
QListWidget::item {{ padding: 7px 8px; border-radius: 6px; }}

QFrame#popup {{ background: {c['painel']}; border: 1px solid {c['borda']}; border-radius: 14px; }}
QSlider::groove:horizontal {{ height: 6px; background: {c['campo']}; border-radius: 3px; }}
QSlider::handle:horizontal {{ width: 16px; height: 16px; margin: -5px 0; border-radius: 8px; background: {c['acento']}; }}

QScrollBar:vertical {{ background: transparent; width: 8px; margin: 0; }}
QScrollBar::handle:vertical {{ background: {c['rolagem']}; border-radius: 4px; min-height: 30px; }}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{ background: transparent; }}
QToolTip {{ background: {c['painel']}; color: {c['texto']}; border: 1px solid {c['borda']}; padding: 6px; }}
"""


# ----------------------------------------------------------------------------
# Download em segundo plano
# ----------------------------------------------------------------------------
class Baixador(QThread):
    info = Signal(str, list)
    musica_inicio = Signal(int)
    musica_progresso = Signal(int, float)
    musica_fim = Signal(int, str)       # "ok" | "existe" | "erro"
    concluido = Signal(dict)
    falhou = Signal(str)
    cancelado = Signal()

    def __init__(self, url, pasta_base):
        super().__init__()
        self.url = url
        self.pasta_base = Path(pasta_base)
        self._cancelar = False

    def cancelar(self):
        self._cancelar = True

    def run(self):
        try:
            with yt_dlp.YoutubeDL({"extract_flat": "in_playlist", "quiet": True,
                                   "no_warnings": True}) as ydl:
                dados = ydl.extract_info(self.url, download=False)
        except Exception as e:
            self.falhou.emit(f"Não foi possível ler a playlist.\n\n{e}")
            return

        entradas = [e for e in (dados.get("entries") or []) if e]
        if not entradas and dados.get("_type", "video") == "video":
            entradas = [dados]
        if not entradas:
            self.falhou.emit("Nenhuma música encontrada. Confira se a playlist "
                             "está como Pública ou Não listada.")
            return

        nome = dados.get("title") or "Playlist"
        pasta = self.pasta_base / limpar_nome(nome)
        pasta.mkdir(parents=True, exist_ok=True)
        self.info.emit(nome, [e.get("title") or e.get("id") or "Sem título" for e in entradas])

        presentes = 0
        for i, entrada in enumerate(entradas):
            if self._cancelar:
                break
            self.musica_inicio.emit(i)
            url_video = (entrada.get("webpage_url") or entrada.get("url")
                         or f"https://www.youtube.com/watch?v={entrada.get('id')}")

            def gancho(d, i=i):
                if self._cancelar:
                    raise DownloadCancelled()
                if d.get("status") == "downloading":
                    total = d.get("total_bytes") or d.get("total_bytes_estimate")
                    if total:
                        self.musica_progresso.emit(i, d.get("downloaded_bytes", 0) / total * 100)

            opcoes = {
                "format": "bestaudio/best",
                "outtmpl": str(pasta / f"{i + 1:02d} - %(title)s.%(ext)s"),
                "postprocessors": [
                    {"key": "FFmpegExtractAudio", "preferredcodec": "mp3",
                     "preferredquality": "192"},
                    {"key": "FFmpegMetadata"},
                    {"key": "EmbedThumbnail"},
                ],
                "writethumbnail": True,
                "download_archive": str(pasta / ".baixados.txt"),
                "progress_hooks": [gancho],
                "quiet": True,
                "no_warnings": True,
                "noprogress": True,
            }
            if FFMPEG_DIR:
                opcoes["ffmpeg_location"] = FFMPEG_DIR

            try:
                with yt_dlp.YoutubeDL(opcoes) as ydl:
                    try:
                        ja_tem = ydl.in_download_archive(entrada)
                    except Exception:
                        ja_tem = False
                    if ja_tem:
                        presentes += 1
                        self.musica_fim.emit(i, "existe")
                        continue
                    ydl.download([url_video])
                presentes += 1
                self.musica_fim.emit(i, "ok")
            except DownloadCancelled:
                break
            except Exception:
                if self._cancelar:
                    break
                self.musica_fim.emit(i, "erro")

        if self._cancelar:
            self.cancelado.emit()
            return

        self.concluido.emit({
            "nome": nome, "pasta": str(pasta), "total": len(entradas), "ok": presentes,
            "data": datetime.now().isoformat(timespec="minutes"), "url": self.url,
        })


# ----------------------------------------------------------------------------
# Componentes visuais
# ----------------------------------------------------------------------------
class Tag(QLabel):
    """Etiqueta clicável com o caminho da pasta; abrevia o meio se não couber."""
    clicked = Signal()

    def __init__(self, texto="", parent=None):
        super().__init__(parent)
        self.setObjectName("tag")
        self.setCursor(Qt.PointingHandCursor)
        self.definir(texto)

    def definir(self, texto):
        self._completo = texto
        self.setToolTip(f"{texto}\nClique para abrir a pasta")
        self._ajustar()
        self.updateGeometry()

    def sizeHint(self):
        m = self.contentsMargins()
        largura = self.fontMetrics().horizontalAdvance(self._completo) + m.left() + m.right() + 4
        return QSize(largura, super().sizeHint().height())

    def minimumSizeHint(self):
        return QSize(60, super().minimumSizeHint().height())

    def resizeEvent(self, evento):
        super().resizeEvent(evento)
        self._ajustar()

    def _ajustar(self):
        largura = max(self.contentsRect().width(), 20)
        self.setText(self.fontMetrics().elidedText(self._completo, Qt.ElideMiddle, largura))

    def mousePressEvent(self, evento):
        if evento.button() == Qt.LeftButton:
            self.clicked.emit()


class CartaoHistorico(QFrame):
    def __init__(self, reg, ultima=False):
        super().__init__()
        self.setObjectName("cartao")
        lay = QVBoxLayout(self)
        lay.setContentsMargins(16, 14, 16, 14)
        lay.setSpacing(6)

        topo = QHBoxLayout()
        nome = QLabel(reg["nome"])
        nome.setObjectName("cartaoNome")
        nome.setWordWrap(True)
        topo.addWidget(nome, 1)
        self.selo = QLabel("Última baixada")
        self.selo.setObjectName("selo")
        self.selo.setVisible(ultima)
        topo.addWidget(self.selo, 0, Qt.AlignTop)
        lay.addLayout(topo)

        try:
            quando = datetime.fromisoformat(reg["data"]).strftime("%d/%m/%Y às %H:%M")
        except Exception:
            quando = ""
        info = QLabel(f"{reg.get('ok', 0)} de {reg.get('total', 0)} músicas, em {quando}")
        info.setObjectName("cartaoInfo")
        lay.addWidget(info)

        tag = Tag(encurtar(reg["pasta"]))
        tag.clicked.connect(lambda: abrir_pasta(reg["pasta"]))
        lay.addWidget(tag, 0, Qt.AlignLeft)

    def marcar_ultima(self, sim):
        self.selo.setVisible(sim)


# ---- Divisória com botão de trocar lados ------------------------------------
class AlcaDivisoria(QSplitterHandle):
    def __init__(self, orientacao, divisoria):
        super().__init__(orientacao, divisoria)
        self.setToolTip("Arraste para redimensionar.\nClique duas vezes para voltar a 50/50.")
        self.botao = QToolButton(self)
        self.botao.setObjectName("trocar")
        self.botao.setText("⇄")
        self.botao.setFixedSize(30, 30)
        self.botao.setCursor(Qt.PointingHandCursor)
        self.botao.setToolTip("Trocar os lados de posição")
        self.botao.clicked.connect(divisoria.trocar_lados)

    def resizeEvent(self, evento):
        super().resizeEvent(evento)
        self.botao.move((self.width() - 30) // 2, (self.height() - 30) // 2)

    def paintEvent(self, evento):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        cor = QColor(self.splitter().cor_grip)
        cor.setAlphaF(0.55 if self.underMouse() else 0.3)
        p.setPen(QPen(cor, 3, Qt.SolidLine, Qt.RoundCap))
        x, meio = self.width() / 2, self.height() / 2
        p.drawLine(QPointF(x, meio - 64), QPointF(x, meio - 26))
        p.drawLine(QPointF(x, meio + 26), QPointF(x, meio + 64))

    def enterEvent(self, e):
        self.update()
        super().enterEvent(e)

    def leaveEvent(self, e):
        self.update()
        super().leaveEvent(e)

    def mouseDoubleClickEvent(self, evento):
        self.splitter().setSizes([1, 1])
        self.splitter().splitterMoved.emit(0, 1)


class Divisoria(QSplitter):
    trocou = Signal()

    def __init__(self):
        super().__init__(Qt.Horizontal)
        self.cor_grip = QColor("#888888")
        self.setHandleWidth(34)
        self.setChildrenCollapsible(False)

    def createHandle(self):
        return AlcaDivisoria(self.orientation(), self)

    def trocar_lados(self):
        tamanhos = self.sizes()
        self.insertWidget(1, self.widget(0))
        self.setSizes(tamanhos[::-1])
        for i in range(self.count()):  # transição suave
            w = self.widget(i)
            efeito = QGraphicsOpacityEffect(w)
            w.setGraphicsEffect(efeito)
            anim = QPropertyAnimation(efeito, b"opacity", self)
            anim.setDuration(320)
            anim.setStartValue(0.25)
            anim.setEndValue(1.0)
            anim.setEasingCurve(QEasingCurve.OutCubic)
            anim.finished.connect(lambda w=w: w.setGraphicsEffect(None))
            anim.start(QAbstractAnimation.DeleteWhenStopped)
        self.trocou.emit()


# ---- Círculo de cores ------------------------------------------------------
class RodaCores(QWidget):
    mudou = Signal()

    def __init__(self):
        super().__init__()
        self.setFixedSize(210, 210)
        self.setCursor(Qt.CrossCursor)
        self.h, self.s, self.v = 0.0, 1.0, 1.0

    def cor(self):
        return QColor.fromHsvF(self.h, self.s, self.v)

    def definir(self, cor):
        self.h = max(cor.hsvHueF(), 0.0)
        self.s, self.v = cor.hsvSaturationF(), cor.valueF()
        self.update()

    def _raio(self):
        return min(self.width(), self.height()) / 2 - 12

    def paintEvent(self, evento):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        c = QPointF(self.width() / 2, self.height() / 2)
        r = self._raio()

        conica = QConicalGradient(c, 0)
        for i in range(7):
            conica.setColorAt(i / 6, QColor.fromHsvF((i / 6) % 1.0, 1.0, self.v))
        p.setPen(Qt.NoPen)
        p.setBrush(conica)
        p.drawEllipse(c, r, r)

        branco = QColor.fromHsvF(0, 0, self.v)
        transp = QColor(branco)
        transp.setAlphaF(0)
        radial = QRadialGradient(c, r)
        radial.setColorAt(0, branco)
        radial.setColorAt(1, transp)
        p.setBrush(radial)
        p.drawEllipse(c, r, r)

        ang = self.h * 2 * math.pi
        pos = QPointF(c.x() + math.cos(ang) * self.s * r, c.y() - math.sin(ang) * self.s * r)
        p.setBrush(self.cor())
        p.setPen(QPen(QColor("white"), 3))
        p.drawEllipse(pos, 9, 9)
        p.setPen(QPen(QColor(0, 0, 0, 110), 1))
        p.setBrush(Qt.NoBrush)
        p.drawEllipse(pos, 11, 11)

    def _escolher(self, pt):
        dx = pt.x() - self.width() / 2
        dy = self.height() / 2 - pt.y()
        self.h = (math.atan2(dy, dx) / (2 * math.pi)) % 1.0
        self.s = min(math.hypot(dx, dy) / self._raio(), 1.0)
        self.update()
        self.mudou.emit()

    def mousePressEvent(self, e):
        self._escolher(e.position())

    def mouseMoveEvent(self, e):
        if e.buttons() & Qt.LeftButton:
            self._escolher(e.position())


class SeletorCor(QWidget):
    """Janelinha que abre ao clicar na bolinha de cor."""
    cor_escolhida = Signal(object)   # str "#rrggbb" ou None (padrão)
    fechou = Signal()

    def __init__(self, parent=None):
        super().__init__(parent, Qt.Popup | Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        fora = QVBoxLayout(self)
        fora.setContentsMargins(0, 0, 0, 0)
        caixa = QFrame()
        caixa.setObjectName("popup")
        fora.addWidget(caixa)

        lay = QVBoxLayout(caixa)
        lay.setContentsMargins(18, 16, 18, 16)
        lay.setSpacing(10)
        titulo = QLabel("Cor principal")
        titulo.setStyleSheet("font-weight: 700; font-size: 15px;")
        lay.addWidget(titulo)

        self.roda = RodaCores()
        self.roda.mudou.connect(self._emitir)
        lay.addWidget(self.roda, 0, Qt.AlignHCenter)

        linha_brilho = QHBoxLayout()
        rot = QLabel("Brilho")
        rot.setObjectName("sub")
        linha_brilho.addWidget(rot)
        self.brilho = QSlider(Qt.Horizontal)
        self.brilho.setRange(35, 100)
        self.brilho.valueChanged.connect(self._mudou_brilho)
        linha_brilho.addWidget(self.brilho, 1)
        lay.addLayout(linha_brilho)

        linha_presets = QHBoxLayout()
        linha_presets.setSpacing(8)
        for hexa in PRESETS:
            b = QPushButton()
            b.setFixedSize(26, 26)
            b.setCursor(Qt.PointingHandCursor)
            b.setToolTip(hexa)
            b.setStyleSheet(f"QPushButton {{ background: {hexa}; border: none; border-radius: 13px; }}"
                            f"QPushButton:hover {{ border: 2px solid white; }}")
            b.clicked.connect(lambda _=False, h=hexa: self._preset(h))
            linha_presets.addWidget(b)
        linha_presets.addStretch(1)
        lay.addLayout(linha_presets)

        padrao = QPushButton("Restaurar cores originais")
        padrao.setObjectName("secundario")
        padrao.setCursor(Qt.PointingHandCursor)
        padrao.clicked.connect(self._padrao)
        lay.addWidget(padrao)

    def abrir(self, cor_atual, ancora):
        self.roda.definir(QColor(cor_atual or COR_PADRAO))
        self.brilho.blockSignals(True)
        self.brilho.setValue(int(self.roda.v * 100))
        self.brilho.blockSignals(False)
        self.adjustSize()
        pos = ancora.mapToGlobal(QPoint(ancora.width() - self.width(), ancora.height() + 8))
        self.move(pos)
        self.show()

    def _mudou_brilho(self, valor):
        self.roda.v = valor / 100
        self.roda.update()
        self._emitir()

    def _emitir(self):
        self.cor_escolhida.emit(self.roda.cor().name())

    def _preset(self, hexa):
        self.roda.definir(QColor(hexa))
        self.brilho.blockSignals(True)
        self.brilho.setValue(int(self.roda.v * 100))
        self.brilho.blockSignals(False)
        self.cor_escolhida.emit(None if hexa == COR_PADRAO else hexa)

    def _padrao(self):
        self.roda.definir(QColor(COR_PADRAO))
        self.cor_escolhida.emit(None)

    def hideEvent(self, e):
        super().hideEvent(e)
        self.fechou.emit()


# ----------------------------------------------------------------------------
# Janela principal
# ----------------------------------------------------------------------------
ICONES = {"pendente": "○", "baixando": "↓", "ok": "✓", "existe": "↷", "erro": "✕"}


class Janela(QWidget):
    def __init__(self):
        super().__init__()
        self.setObjectName("raiz")
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setWindowTitle("SomDeMala")
        self.resize(1140, 720)
        self.setMinimumSize(800, 560)

        self.historico = ler_json(ARQ_HIST, [])
        self.conf = ler_json(ARQ_CONF, {})
        self.pasta_base = self.conf.get("pasta_base") or str(pasta_musica_padrao())
        self.cor = self.conf.get("cor")
        self.tema = self.conf.get("tema", "escuro")
        self.worker = None
        self.cartoes = []
        self.titulos = []
        self.estados = []
        self.feitos = 0

        raiz = QVBoxLayout(self)
        raiz.setContentsMargins(20, 14, 20, 20)
        raiz.setSpacing(12)
        raiz.addLayout(self._montar_topo())

        self.painel_hist = self._montar_historico()
        self.painel_baixar = self._montar_baixar()
        self.divisoria = Divisoria()
        if self.conf.get("ordem") == "hist-dir":
            self.divisoria.addWidget(self.painel_baixar)
            self.divisoria.addWidget(self.painel_hist)
        else:
            self.divisoria.addWidget(self.painel_hist)
            self.divisoria.addWidget(self.painel_baixar)
        self._aplicar_proporcao(self.conf.get("proporcao", 0.5))
        self.divisoria.splitterMoved.connect(lambda *_: self._timer_salvar.start())
        self.divisoria.trocou.connect(self.salvar_conf)
        raiz.addWidget(self.divisoria, 1)

        self._timer_salvar = QTimer(self, singleShot=True, interval=400)
        self._timer_salvar.timeout.connect(self.salvar_conf)

        self.seletor = SeletorCor(self)
        self.seletor.cor_escolhida.connect(self._cor_ao_vivo)
        self.seletor.fechou.connect(self.salvar_conf)
        self._cor_pendente = None
        self._timer_cor = QTimer(self, singleShot=True, interval=30)
        self._timer_cor.timeout.connect(self._aplicar_cor_pendente)

        for i, reg in enumerate(self.historico):
            self._inserir_cartao(reg, ultima=(i == 0), no_topo=False)
        self._atualizar_contagem()
        self.aplicar_tema()

        if not FFMPEG_DIR and not shutil.which("ffmpeg"):
            QTimer.singleShot(400, lambda: QMessageBox.warning(
                self, "FFmpeg não encontrado",
                "O FFmpeg é necessário para converter as músicas em MP3.\n\n"
                "No Ubuntu, instale com: sudo apt install ffmpeg"))

    # ---- topo: cor e tema --------------------------------------------------
    def _montar_topo(self):
        topo = QHBoxLayout()
        topo.setSpacing(10)
        marca = QLabel("SomDeMala")
        marca.setObjectName("marca")
        topo.addWidget(marca)
        topo.addStretch(1)

        self.btn_cor = QPushButton()
        self.btn_cor.setObjectName("amostra")
        self.btn_cor.setCursor(Qt.PointingHandCursor)
        self.btn_cor.setToolTip("Escolher a cor principal")
        self.btn_cor.clicked.connect(lambda: self.seletor.abrir(self.cor, self.btn_cor))
        topo.addWidget(self.btn_cor)

        self.btn_tema = QPushButton()
        self.btn_tema.setObjectName("iconeTema")
        self.btn_tema.setCursor(Qt.PointingHandCursor)
        self.btn_tema.clicked.connect(self.alternar_tema)
        topo.addWidget(self.btn_tema)
        return topo

    def _novo_painel(self):
        painel = QFrame()
        painel.setObjectName("painel")
        painel.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred)
        painel.setMinimumWidth(340)
        return painel

    # ---- painel do histórico ----------------------------------------------
    def _montar_historico(self):
        painel = self._novo_painel()
        lay = QVBoxLayout(painel)
        lay.setContentsMargins(24, 24, 24, 24)
        lay.setSpacing(4)

        cabecalho = QHBoxLayout()
        titulo = QLabel("Histórico")
        titulo.setObjectName("titulo")
        cabecalho.addWidget(titulo)
        cabecalho.addStretch(1)
        self.btn_limpar = QPushButton("Limpar histórico")
        self.btn_limpar.setObjectName("secundario")
        self.btn_limpar.setCursor(Qt.PointingHandCursor)
        self.btn_limpar.setToolTip("Limpa só a lista. As músicas baixadas continuam nas pastas.")
        self.btn_limpar.clicked.connect(self.limpar_historico)
        cabecalho.addWidget(self.btn_limpar, 0, Qt.AlignVCenter)
        lay.addLayout(cabecalho)
        self.lbl_contagem = QLabel()
        self.lbl_contagem.setObjectName("sub")
        lay.addWidget(self.lbl_contagem)
        lay.addSpacing(14)

        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.scroll.setFrameShape(QFrame.NoFrame)
        self.scroll.viewport().setAutoFillBackground(False)

        interno = QWidget()
        interno.setObjectName("listaInterna")
        interno.setAutoFillBackground(False)
        self.lista_hist = QVBoxLayout(interno)
        self.lista_hist.setContentsMargins(0, 0, 6, 0)
        self.lista_hist.setSpacing(10)

        self.vazio = QLabel("Nenhuma playlist baixada ainda.\n"
                            "As playlists que você baixar vão aparecer aqui.")
        self.vazio.setObjectName("vazio")
        self.vazio.setAlignment(Qt.AlignCenter)
        self.lista_hist.addWidget(self.vazio)
        self.lista_hist.addStretch(1)

        self.scroll.setWidget(interno)
        lay.addWidget(self.scroll, 1)
        return painel

    # ---- painel de baixar --------------------------------------------------
    def _montar_baixar(self):
        painel = self._novo_painel()
        lay = QVBoxLayout(painel)
        lay.setContentsMargins(24, 24, 24, 24)
        lay.setSpacing(4)

        titulo = QLabel("Baixar playlist")
        titulo.setObjectName("titulo")
        lay.addWidget(titulo)
        sub = QLabel("")
        sub.setObjectName("sub")
        sub.setWordWrap(True)
        lay.addWidget(sub)
        lay.addSpacing(18)

        self.campo = QLineEdit()
        self.campo.setPlaceholderText("Cole aqui o link da playlist do YouTube")
        self.campo.returnPressed.connect(self.iniciar)
        lay.addWidget(self.campo)
        lay.addSpacing(10)

        linha = QHBoxLayout()
        linha.setSpacing(8)
        rotulo = QLabel("Salvar em")
        rotulo.setObjectName("sub")
        linha.addWidget(rotulo)
        self.tag_pasta = Tag(encurtar(self.pasta_base))
        self.tag_pasta.clicked.connect(lambda: abrir_pasta(self.pasta_base))
        linha.addWidget(self.tag_pasta, 1, Qt.AlignLeft)
        self.btn_pasta = QPushButton("Alterar")
        self.btn_pasta.setObjectName("secundario")
        self.btn_pasta.setCursor(Qt.PointingHandCursor)
        self.btn_pasta.clicked.connect(self.escolher_pasta)
        linha.addWidget(self.btn_pasta)
        lay.addLayout(linha)
        lay.addSpacing(14)

        self.btn_baixar = QPushButton("Baixar")
        self.btn_baixar.setObjectName("primario")
        self.btn_baixar.setCursor(Qt.PointingHandCursor)
        self.btn_baixar.clicked.connect(self.iniciar)
        lay.addWidget(self.btn_baixar)
        lay.addSpacing(22)

        self.ocioso = QLabel("Cole um link acima e clique em Baixar.\n"
                             "O progresso de cada música aparece aqui.")
        self.ocioso.setObjectName("vazio")
        self.ocioso.setAlignment(Qt.AlignCenter)
        self.ocioso.setWordWrap(True)
        lay.addWidget(self.ocioso, 1)

        self.caixa_prog = QWidget()
        self.caixa_prog.setObjectName("caixaProg")
        cp = QVBoxLayout(self.caixa_prog)
        cp.setContentsMargins(0, 0, 0, 0)
        cp.setSpacing(8)

        self.lbl_playlist = QLabel()
        self.lbl_playlist.setObjectName("nomePlaylist")
        self.lbl_playlist.setWordWrap(True)
        cp.addWidget(self.lbl_playlist)
        self.lbl_geral = QLabel()
        self.lbl_geral.setObjectName("sub")
        cp.addWidget(self.lbl_geral)
        self.barra_geral = QProgressBar()
        self.barra_geral.setTextVisible(False)
        cp.addWidget(self.barra_geral)
        cp.addSpacing(6)

        self.lbl_atual = QLabel()
        self.lbl_atual.setObjectName("atual")
        cp.addWidget(self.lbl_atual)
        self.barra_atual = QProgressBar()
        self.barra_atual.setObjectName("barraAtual")
        self.barra_atual.setTextVisible(False)
        self.barra_atual.setRange(0, 100)
        cp.addWidget(self.barra_atual)
        cp.addSpacing(6)

        self.lista_musicas = QListWidget()
        self.lista_musicas.setFocusPolicy(Qt.NoFocus)
        self.lista_musicas.setSelectionMode(QListWidget.NoSelection)
        cp.addWidget(self.lista_musicas, 1)

        self.btn_cancelar = QPushButton("Cancelar download")
        self.btn_cancelar.setObjectName("secundario")
        self.btn_cancelar.setCursor(Qt.PointingHandCursor)
        self.btn_cancelar.clicked.connect(self.cancelar)
        cp.addWidget(self.btn_cancelar, 0, Qt.AlignRight)

        self.caixa_prog.hide()
        lay.addWidget(self.caixa_prog, 1)
        return painel

    # ---- layout: proporção e ordem ----------------------------------------
    def _aplicar_proporcao(self, prop):
        prop = min(max(float(prop), 0.2), 0.8)
        a, b = int(prop * 1000), int((1 - prop) * 1000)
        hist_primeiro = self.divisoria.widget(0) is self.painel_hist
        self.divisoria.setSizes([a, b] if hist_primeiro else [b, a])

    def salvar_conf(self):
        tamanhos = self.divisoria.sizes()
        total = sum(tamanhos) or 1
        i_hist = self.divisoria.indexOf(self.painel_hist)
        self.conf.update({
            "pasta_base": self.pasta_base,
            "cor": self.cor,
            "tema": self.tema,
            "ordem": "hist-esq" if i_hist == 0 else "hist-dir",
            "proporcao": round(tamanhos[i_hist] / total, 3),
        })
        gravar_json(ARQ_CONF, self.conf)

    # ---- cor e tema --------------------------------------------------------
    def aplicar_tema(self):
        self.paleta = montar_paleta(self.cor, self.tema)
        QApplication.instance().setStyleSheet(montar_estilo(self.paleta))
        self.divisoria.cor_grip = self.paleta["suave"]
        for i in range(self.divisoria.count()):
            self.divisoria.handle(i).update()
        escuro = self.tema == "escuro"
        self.btn_tema.setText("☀" if escuro else "☾")
        self.btn_tema.setToolTip("Mudar para o modo claro" if escuro else "Mudar para o modo escuro")
        for i, estado in enumerate(self.estados):
            self._marcar(i, estado)

    def alternar_tema(self):
        self.tema = "claro" if self.tema == "escuro" else "escuro"
        self.aplicar_tema()
        self.salvar_conf()

    def _cor_ao_vivo(self, cor):
        self._cor_pendente = cor
        self._timer_cor.start()   # evita redesenhar a cada pixel arrastado

    def _aplicar_cor_pendente(self):
        self.cor = self._cor_pendente
        self.aplicar_tema()

    # ---- histórico ---------------------------------------------------------
    def _inserir_cartao(self, reg, ultima, no_topo=True):
        self.vazio.hide()
        cartao = CartaoHistorico(reg, ultima=ultima)
        if no_topo:
            for c in self.cartoes:
                c.marcar_ultima(False)
            self.lista_hist.insertWidget(0, cartao)
            self.cartoes.insert(0, cartao)
        else:
            self.lista_hist.insertWidget(self.lista_hist.count() - 1, cartao)
            self.cartoes.append(cartao)
        return cartao

    def limpar_historico(self):
        if not self.cartoes:
            return
        resp = QMessageBox.question(
            self, "Limpar histórico",
            "Limpar a lista de playlists baixadas?\n\n"
            "As músicas continuam salvas nas pastas do seu computador.",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if resp != QMessageBox.Yes:
            return

        self.historico = []
        gravar_json(ARQ_HIST, self.historico)
        cartoes, self.cartoes = self.cartoes, []
        self.btn_limpar.setEnabled(False)

        def remover():
            for c in cartoes:
                self.lista_hist.removeWidget(c)
                c.deleteLater()
            self.vazio.show()
            self._atualizar_contagem()

        # os cartões somem em sequência, de cima para baixo
        for i, c in enumerate(cartoes):
            efeito = QGraphicsOpacityEffect(c)
            c.setGraphicsEffect(efeito)
            anim = QPropertyAnimation(efeito, b"opacity", self)
            anim.setDuration(260)
            anim.setStartValue(1.0)
            anim.setEndValue(0.0)
            QTimer.singleShot(min(i, 8) * 45,
                              lambda a=anim: a.start(QAbstractAnimation.DeleteWhenStopped))
        QTimer.singleShot(min(len(cartoes) - 1, 8) * 45 + 300, remover)

    def _atualizar_contagem(self):
        n = len(self.historico)
        self.btn_limpar.setEnabled(n > 0)
        self.lbl_contagem.setText("Nenhuma playlist ainda" if n == 0 else
                                  f"{n} playlist baixada" if n == 1 else
                                  f"{n} playlists baixadas")

    # ---- ações -------------------------------------------------------------
    def escolher_pasta(self):
        pasta = QFileDialog.getExistingDirectory(self, "Escolha onde salvar", self.pasta_base)
        if pasta:
            self.pasta_base = pasta
            self.tag_pasta.definir(encurtar(pasta))
            self.salvar_conf()

    def iniciar(self):
        url = self.campo.text().strip()
        if not url:
            self.campo.setFocus()
            return
        if "youtube.com" not in url and "youtu.be" not in url:
            QMessageBox.warning(self, "Link inválido",
                                "Esse link não parece ser do YouTube. Cole o link da playlist.")
            return

        self.campo.setEnabled(False)
        self.btn_baixar.setEnabled(False)
        self.btn_pasta.setEnabled(False)
        self.btn_cancelar.setEnabled(True)
        self.ocioso.hide()
        self.caixa_prog.show()
        self.lbl_playlist.setText("Lendo a playlist…")
        self.lbl_geral.setText("")
        self.lbl_atual.setText("")
        self.barra_geral.setRange(0, 0)
        self.barra_atual.setValue(0)
        self.lista_musicas.clear()
        self.estados = []
        self.feitos = 0

        self.worker = Baixador(url, self.pasta_base)
        self.worker.info.connect(self.ao_receber_info)
        self.worker.musica_inicio.connect(self.ao_iniciar_musica)
        self.worker.musica_progresso.connect(lambda i, p: self.barra_atual.setValue(int(p)))
        self.worker.musica_fim.connect(self.ao_terminar_musica)
        self.worker.concluido.connect(self.ao_concluir)
        self.worker.falhou.connect(self.ao_falhar)
        self.worker.cancelado.connect(lambda: self.resetar_baixar(animado=True))
        self.worker.start()

    def cancelar(self):
        if self.worker and self.worker.isRunning():
            self.worker.cancelar()
            self.btn_cancelar.setEnabled(False)
            self.lbl_atual.setText("Cancelando…")

    def ao_receber_info(self, nome, titulos):
        self.titulos = titulos
        self.estados = ["pendente"] * len(titulos)
        self.lbl_playlist.setText(nome)
        self.barra_geral.setRange(0, len(titulos))
        self.barra_geral.setValue(0)
        self.lbl_geral.setText(f"0 de {len(titulos)} músicas")
        for i in range(len(titulos)):
            self.lista_musicas.addItem(QListWidgetItem())
            self._marcar(i, "pendente")

    def _marcar(self, i, estado):
        item = self.lista_musicas.item(i)
        if not item:
            return
        self.estados[i] = estado
        extra = "   já estava na pasta" if estado == "existe" else \
                "   falhou" if estado == "erro" else ""
        item.setText(f"{ICONES[estado]}   {i + 1:02d}   {self.titulos[i]}{extra}")
        cores = {"pendente": "fraco", "baixando": "destaque", "ok": "sucesso",
                 "existe": "fraco", "erro": "erro"}
        item.setForeground(self.paleta[cores[estado]])

    def ao_iniciar_musica(self, i):
        self._marcar(i, "baixando")
        self.lista_musicas.scrollToItem(self.lista_musicas.item(i))
        self.lbl_atual.setText(f"Baixando: {self.titulos[i]}")
        self.barra_atual.setValue(0)

    def ao_terminar_musica(self, i, estado):
        self._marcar(i, estado)
        self.feitos += 1
        self.barra_geral.setValue(self.feitos)
        self.lbl_geral.setText(f"{self.feitos} de {len(self.titulos)} músicas")
        self.barra_atual.setValue(100)

    def ao_falhar(self, msg):
        QMessageBox.warning(self, "Não foi possível baixar", msg)
        self.resetar_baixar()

    def ao_concluir(self, reg):
        self.lbl_atual.setText("Playlist concluída")
        self.btn_cancelar.setEnabled(False)
        self.historico.insert(0, reg)
        gravar_json(ARQ_HIST, self.historico)
        QTimer.singleShot(500, lambda: self.animar_para_historico(reg))

    # ---- animação: nome da playlist voa para o histórico ------------------
    def animar_para_historico(self, reg):
        self.scroll.verticalScrollBar().setValue(0)

        voador = QLabel(self)
        voador.setObjectName("voador")
        largura_max = max(self.painel_hist.width() - 80, 120)
        voador.setText(voador.fontMetrics().elidedText(reg["nome"], Qt.ElideRight, largura_max))
        voador.adjustSize()

        origem = self.lbl_playlist.mapTo(self, QPoint(0, 0))
        destino = self.scroll.viewport().mapTo(self, QPoint(0, 0))
        voador.move(origem)
        voador.show()
        voador.raise_()

        efeito = QGraphicsOpacityEffect(voador)
        efeito.setOpacity(1.0)
        voador.setGraphicsEffect(efeito)

        voo = QPropertyAnimation(voador, b"pos", self)
        voo.setDuration(850)
        voo.setStartValue(origem)
        voo.setEndValue(destino)
        voo.setEasingCurve(QEasingCurve.InOutCubic)

        sumir = QPropertyAnimation(efeito, b"opacity", self)
        sumir.setDuration(300)
        sumir.setStartValue(1.0)
        sumir.setEndValue(0.0)

        def pousou():
            cartao = self._inserir_cartao(reg, ultima=True)
            self._atualizar_contagem()
            self._destacar(cartao)
            self.resetar_baixar(animado=True)

        voo.finished.connect(pousou)
        seq = QSequentialAnimationGroup(self)
        seq.addAnimation(voo)
        seq.addAnimation(sumir)
        seq.finished.connect(voador.deleteLater)
        seq.start(QAbstractAnimation.DeleteWhenStopped)

    def _destacar(self, cartao):
        cartao.setProperty("novo", True)
        repolir(cartao)
        efeito = QGraphicsOpacityEffect(cartao)
        cartao.setGraphicsEffect(efeito)
        entrar = QPropertyAnimation(efeito, b"opacity", self)
        entrar.setDuration(450)
        entrar.setStartValue(0.0)
        entrar.setEndValue(1.0)
        entrar.finished.connect(lambda: cartao.setGraphicsEffect(None))
        entrar.start(QAbstractAnimation.DeleteWhenStopped)

        def apagar_destaque():
            cartao.setProperty("novo", False)
            repolir(cartao)
        QTimer.singleShot(2200, apagar_destaque)

    # ---- limpa o painel de baixar para o próximo link ---------------------
    def resetar_baixar(self, animado=False):
        def limpar():
            self.caixa_prog.setGraphicsEffect(None)
            self.caixa_prog.hide()
            self.lista_musicas.clear()
            self.estados = []
            self.barra_geral.setRange(0, 1)
            self.barra_geral.setValue(0)
            self.barra_atual.setValue(0)
            self.campo.clear()
            self.campo.setEnabled(True)
            self.btn_baixar.setEnabled(True)
            self.btn_pasta.setEnabled(True)
            self.ocioso.show()
            self.campo.setFocus()

        if not animado:
            limpar()
            return
        efeito = QGraphicsOpacityEffect(self.caixa_prog)
        self.caixa_prog.setGraphicsEffect(efeito)
        sumir = QPropertyAnimation(efeito, b"opacity", self)
        sumir.setDuration(450)
        sumir.setStartValue(1.0)
        sumir.setEndValue(0.0)
        sumir.finished.connect(limpar)
        sumir.start(QAbstractAnimation.DeleteWhenStopped)

    def closeEvent(self, evento):
        self.salvar_conf()
        if self.worker and self.worker.isRunning():
            self.worker.cancelar()
            self.worker.wait(5000)
        super().closeEvent(evento)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setApplicationName("SomDeMala")
    janela = Janela()
    janela.show()
    sys.exit(app.exec())
