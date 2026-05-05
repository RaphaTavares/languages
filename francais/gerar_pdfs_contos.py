"""
Gera 5 PDFs de contos Frieren com tema escuro + imagens unicas por conto.

Contos:
1. conte-frieren-la-chanson.pdf      (La chanson que personne n'entend)
2. conte-frieren-le-village.pdf      (Le village qui a oublie la guerre)
3. conte-frieren-la-carte.pdf        (La carte qui ne mene nulle part)
4. conte-frieren-le-jardin.pdf       (Le jardin de la mage oubliee)
5. conte-frieren-les-etoiles.pdf     (Les etoiles qu'on ne voit qu'une fois)
"""

from fpdf import FPDF
from PIL import Image
import os
import tempfile

BASE = os.path.dirname(os.path.abspath(__file__))
IMG  = os.path.join(BASE, "img")
TEMP_DIR = os.path.join(BASE, "_temp_img")
os.makedirs(TEMP_DIR, exist_ok=True)

# -- Cores do tema escuro --
BG       = (30, 30, 36)
TEXT     = (220, 220, 220)
TITLE    = (180, 160, 220)
ACCENT   = (140, 180, 255)
SUBTLE   = (160, 160, 170)
DIVIDER  = (80, 80, 100)


# -- Helpers --

def sanitize(txt):
    """Replace problematic unicode chars with ASCII equivalents for Helvetica."""
    replacements = {
        "\u2019": "'", "\u2018": "'",
        "\u201c": '"', "\u201d": '"',
        "\u00ab": '"', "\u00bb": '"',
        "\u2014": "--", "\u2013": "-",
        "\u2026": "...",
    }
    for k, v in replacements.items():
        txt = txt.replace(k, v)
    return txt


def dark_page(pdf):
    pdf.set_fill_color(*BG)
    pdf.rect(0, 0, 210, 297, "F")


def add_separator(pdf):
    pdf.ln(3)
    pdf.set_draw_color(*DIVIDER)
    x = 60
    pdf.line(x, pdf.get_y(), 210 - x, pdf.get_y())
    pdf.ln(6)


def safe_write(pdf, txt, align="L"):
    txt = sanitize(txt)
    pdf.set_left_margin(20)
    pdf.set_right_margin(20)
    pdf.set_x(20)
    pdf.multi_cell(w=170, h=7, text=txt, align=align)


def optimize_image(path):
    """Convert PNG to JPEG for smaller PDF size. Returns path to use."""
    if not path.lower().endswith(".png"):
        return path
    basename = os.path.splitext(os.path.basename(path))[0] + ".jpg"
    out_path = os.path.join(TEMP_DIR, basename)
    if os.path.exists(out_path):
        return out_path
    im = Image.open(path)
    if im.mode in ("RGBA", "P"):
        im = im.convert("RGB")
    im.save(out_path, "JPEG", quality=85, optimize=True)
    print(f"  [OPT] {os.path.basename(path)} -> {basename}")
    return out_path


def add_image_banner(pdf, path, max_h=70):
    if not os.path.exists(path):
        print(f"  [WARN] Imagem nao encontrada: {path}")
        return
    path = optimize_image(path)
    im = Image.open(path)
    w_img, h_img = im.size
    usable_w = 170
    ratio = usable_w / w_img
    h_scaled = h_img * ratio
    if h_scaled > max_h:
        ratio = max_h / h_img
        h_scaled = max_h
        usable_w = w_img * ratio
    x = (210 - usable_w) / 2
    if pdf.get_y() + h_scaled > 275:
        pdf.add_page()
        dark_page(pdf)
    pdf.image(path, x=x, y=pdf.get_y(), w=usable_w, h=h_scaled)
    pdf.ln(h_scaled + 5)


class DarkPDF(FPDF):
    def __init__(self, footer_text="Frieren"):
        super().__init__()
        self._footer_text = footer_text

    def header(self):
        dark_page(self)

    def footer(self):
        self.set_y(-15)
        self.set_font("Helvetica", "I", 8)
        self.set_text_color(*SUBTLE)
        self.cell(0, 10, sanitize(f"{self._footer_text}   |   {self.page_no()}"),
                  align="C")


# -- Definicao dos 5 contos --

CONTOS = [
    {
        "md": "conte-frieren-la-chanson.md",
        "out": "conte-frieren-la-chanson.pdf",
        "title": "Frieren",
        "subtitle": "La chanson que personne n'entend",
        "meta": "Un conte en fran\u00e7ais  |  Niveau A2",
        "meta2": "Univers de Frieren: Beyond Journey's End",
        "footer": "Frieren -- La chanson que personne n'entend",
        "images": ["s1a.jpg", "s1b.jpg", "s1c.png"],
        "img_sections": {1, 3, 5},
        "final_quote": '"Deux personnes, c\'est assez pour qu\'une chanson existe."',
    },
    {
        "md": "conte-frieren-le-village.md",
        "out": "conte-frieren-le-village.pdf",
        "title": "Frieren",
        "subtitle": "Le village qui a oubli\u00e9 la guerre",
        "meta": "Un conte en fran\u00e7ais  |  Niveau A2",
        "meta2": "Univers de Frieren: Beyond Journey's End",
        "footer": "Frieren -- Le village qui a oublie la guerre",
        "images": ["s2a.png", "s2b.jpg", "s2c.png"],
        "img_sections": {1, 4, 7},
        "final_quote": '"La paix parfaite, c\'est une paix qu\'on ne remarque pas."',
    },
    {
        "md": "conte-frieren-la-carte.md",
        "out": "conte-frieren-la-carte.pdf",
        "title": "Frieren",
        "subtitle": "La carte qui ne m\u00e8ne nulle part",
        "meta": "Un conte en fran\u00e7ais  |  Niveau A2",
        "meta2": "Univers de Frieren: Beyond Journey's End",
        "footer": "Frieren -- La carte qui ne mene nulle part",
        "images": ["s3a.jpg", "s3b.jpg", "s3c.png"],
        "img_sections": {1, 4, 7},
        "final_quote": '"Le plus bel endroit du monde n\'etait pas un endroit. C\'etait un moment."',
    },
    {
        "md": "conte-frieren-le-jardin.md",
        "out": "conte-frieren-le-jardin.pdf",
        "title": "Frieren",
        "subtitle": "Le jardin de la mage oubli\u00e9e",
        "meta": "Un conte en fran\u00e7ais  |  Niveau A2",
        "meta2": "Univers de Frieren: Beyond Journey's End",
        "footer": "Frieren -- Le jardin de la mage oubliee",
        "images": ["s4a.jpg", "s4b.jpg", "s4c.png"],
        "img_sections": {1, 4, 7},
        "final_quote": '"Des traces silencieuses. Des preuves invisibles d\'un amour qui n\'a pas besoin d\'etre compris pour exister."',
    },
    {
        "md": "conte-frieren-les-etoiles.md",
        "out": "conte-frieren-les-etoiles.pdf",
        "title": "Frieren",
        "subtitle": "Les \u00e9toiles qu'on ne voit qu'une fois",
        "meta": "Un conte en fran\u00e7ais  |  Niveau A2",
        "meta2": "Univers de Frieren: Beyond Journey's End",
        "footer": "Frieren -- Les etoiles qu'on ne voit qu'une fois",
        "images": ["s5a.png", "s5b.png", "s5c.jpg"],
        "img_sections": {1, 4, 7},
        "final_quote": '"Seule, mais pas vraiment seule. En silence, mais pas dans le vide."',
    },
]


def build_conte_pdf(conte):
    """Gera um PDF escuro para um conto Frieren."""
    pdf = DarkPDF(footer_text=conte["footer"])
    pdf.set_auto_page_break(auto=True, margin=20)
    pdf.add_page()

    # -- Capa --
    pdf.ln(10)
    # Usa a primeira imagem do conto como capa
    add_image_banner(pdf, os.path.join(IMG, conte["images"][0]), max_h=85)
    pdf.ln(3)

    pdf.set_font("Helvetica", "B", 28)
    pdf.set_text_color(*TITLE)
    safe_write(pdf, conte["title"], align="C")
    pdf.ln(2)
    pdf.set_font("Helvetica", "I", 18)
    pdf.set_text_color(*ACCENT)
    safe_write(pdf, conte["subtitle"], align="C")
    pdf.ln(6)
    pdf.set_font("Helvetica", "", 10)
    pdf.set_text_color(*SUBTLE)
    safe_write(pdf, conte["meta"], align="C")
    safe_write(pdf, conte["meta2"], align="C")

    # -- Ler o markdown --
    story_file = os.path.join(BASE, conte["md"])
    with open(story_file, "r", encoding="utf-8") as f:
        raw = f.read()

    # Remover titulo markdown
    lines = raw.split("\n")
    content = []
    past_title = False
    for line in lines:
        if not past_title:
            if line.startswith("# "):
                past_title = True
                continue
            continue
        content.append(line)

    text = "\n".join(content)
    sections = text.split("---")

    # Imagens de conteudo (excluindo a primeira que ja foi usada na capa)
    story_images = conte["images"][1:]  # s*b e s*c
    img_sections = conte["img_sections"]
    img_idx = 0

    for i, section in enumerate(sections):
        section = section.strip()
        if not section:
            continue

        pdf.add_page()

        # Inserir imagem em secoes especificas
        if i in img_sections and img_idx < len(story_images):
            add_image_banner(pdf, os.path.join(IMG, story_images[img_idx]), max_h=60)
            img_idx += 1

        paragraphs = section.split("\n\n")
        for para in paragraphs:
            para = para.strip()
            if not para:
                continue

            para = para.replace("\n", " ")

            # Detectar *Fin.*
            if para == "*Fin.*":
                pdf.ln(10)
                pdf.set_font("Helvetica", "I", 16)
                pdf.set_text_color(*ACCENT)
                safe_write(pdf, "Fin.", align="C")
                continue

            # Detectar italico puro (*texto*)
            if para.startswith("*") and para.endswith("*") and not para.startswith("**"):
                inner = para.strip("*").strip()
                pdf.set_font("Helvetica", "I", 11)
                pdf.set_text_color(*ACCENT)
                safe_write(pdf, inner)
                pdf.ln(3)
                continue

            # Detectar dialogo
            s = sanitize(para)
            is_dialogue = s.startswith('"') or s.startswith("'")

            if is_dialogue:
                pdf.set_font("Helvetica", "I", 11)
                pdf.set_text_color(*ACCENT)
            else:
                pdf.set_font("Helvetica", "", 11)
                pdf.set_text_color(*TEXT)

            safe_write(pdf, para)
            pdf.ln(3)

    # -- Pagina final --
    pdf.add_page()
    pdf.ln(30)
    # Usar ultima imagem
    add_image_banner(pdf, os.path.join(IMG, conte["images"][-1]), max_h=80)
    pdf.ln(8)
    pdf.set_font("Helvetica", "I", 16)
    pdf.set_text_color(*ACCENT)
    safe_write(pdf, "Fin.", align="C")
    pdf.ln(5)
    pdf.set_font("Helvetica", "I", 10)
    pdf.set_text_color(*SUBTLE)
    safe_write(pdf, conte["final_quote"], align="C")

    out = os.path.join(BASE, conte["out"])
    pdf.output(out)
    print(f"[OK] {out}")


def cleanup_temp():
    """Remove imagens temporarias."""
    import shutil
    if os.path.exists(TEMP_DIR):
        shutil.rmtree(TEMP_DIR)
        print("[CLEAN] Imagens temporarias removidas.")


if __name__ == "__main__":
    for conto in CONTOS:
        print(f"Gerando: {conto['out']}...")
        build_conte_pdf(conto)
    cleanup_temp()
    print("\nTodos os PDFs gerados com sucesso!")
