"""
Gera dois PDFs:
1. conte-frieren-la-neige-inutile.pdf  (conto com tema escuro + imagens)
2. ideias-contos-frieren.pdf           (5 ideias de contos)
"""

from fpdf import FPDF
from PIL import Image
import os

BASE = os.path.dirname(os.path.abspath(__file__))
IMG  = os.path.join(BASE, "img")

# ── Cores do tema escuro ──
BG       = (30, 30, 36)
TEXT     = (220, 220, 220)
TITLE    = (180, 160, 220)
ACCENT   = (140, 180, 255)
SUBTLE   = (160, 160, 170)
DIVIDER  = (80, 80, 100)

# ── Helpers ──

def sanitize(txt):
    """Replace problematic unicode chars with ASCII equivalents for Helvetica."""
    replacements = {
        "\u2019": "'", "\u2018": "'",   # smart quotes
        "\u201c": '"', "\u201d": '"',
        "\u00ab": '"', "\u00bb": '"',   # guillemets
        "\u2014": "--", "\u2013": "-",  # dashes
        "\u2026": "...",                # ellipsis
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
    # Ensure we have left/right margins set properly
    pdf.set_left_margin(20)
    pdf.set_right_margin(20)
    pdf.set_x(20)
    pdf.multi_cell(w=170, h=7, text=txt, align=align)

def add_image_banner(pdf, path, max_h=70):
    if not os.path.exists(path):
        return
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


# ══════════════════════════════════════════════════════════════
#  PDF 1 — Conto: La neige inutile
# ══════════════════════════════════════════════════════════════

class DarkPDF(FPDF):
    def header(self):
        dark_page(self)

    def footer(self):
        self.set_y(-15)
        self.set_font("Helvetica", "I", 8)
        self.set_text_color(*SUBTLE)
        self.cell(0, 10, sanitize(f"Frieren -- La neige inutile   |   {self.page_no()}"), align="C")


def build_story_pdf():
    pdf = DarkPDF()
    pdf.set_auto_page_break(auto=True, margin=20)

    # Use latin-1 encoding explicitly
    pdf.add_page()

    # ── Cover page ──
    pdf.ln(10)
    add_image_banner(pdf, os.path.join(IMG, "frieren1.jpg"), max_h=85)
    pdf.ln(3)

    pdf.set_font("Helvetica", "B", 28)
    pdf.set_text_color(*TITLE)
    safe_write(pdf, "Frieren", align="C")
    pdf.ln(2)
    pdf.set_font("Helvetica", "I", 18)
    pdf.set_text_color(*ACCENT)
    safe_write(pdf, "La neige inutile", align="C")
    pdf.ln(6)
    pdf.set_font("Helvetica", "", 10)
    pdf.set_text_color(*SUBTLE)
    safe_write(pdf, "Un conte en francais  |  Niveau A2", align="C")
    safe_write(pdf, "Univers de Frieren: Beyond Journey's End", align="C")

    # ── Read story ──
    story_file = os.path.join(BASE, "conte-frieren-la-neige-inutile.md")
    with open(story_file, "r", encoding="utf-8") as f:
        raw = f.read()

    # Split by --- separator
    lines = raw.split("\n")
    # Remove the markdown title line
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

    img_files = ["frieren2.jpg", "frieren3.jpg", "frieren4.jpg"]
    img_insert_at = {1, 3, 5}  # section indices where we insert images
    img_idx = 0

    for i, section in enumerate(sections):
        section = section.strip()
        if not section:
            continue

        pdf.add_page()

        # Add image banner at certain sections
        if i in img_insert_at and img_idx < len(img_files):
            add_image_banner(pdf, os.path.join(IMG, img_files[img_idx]), max_h=60)
            img_idx += 1

        paragraphs = section.split("\n\n")
        for para in paragraphs:
            para = para.strip()
            if not para:
                continue

            # Handle multiple single newlines within paragraph
            para = para.replace("\n", " ")

            if para == "*Fin.*":
                pdf.ln(10)
                pdf.set_font("Helvetica", "I", 16)
                pdf.set_text_color(*ACCENT)
                safe_write(pdf, "Fin.", align="C")
                continue

            # Dialogue detection (starts with quote mark or \u00ab)
            is_dialogue = False
            s = sanitize(para)
            if s.startswith('"') or s.startswith("'"):
                is_dialogue = True

            if is_dialogue:
                pdf.set_font("Helvetica", "I", 11)
                pdf.set_text_color(*ACCENT)
            else:
                pdf.set_font("Helvetica", "", 11)
                pdf.set_text_color(*TEXT)

            safe_write(pdf, para)
            pdf.ln(3)

    # ── Final page ──
    pdf.add_page()
    pdf.ln(30)
    add_image_banner(pdf, os.path.join(IMG, "frieren4.jpg"), max_h=80)
    pdf.ln(8)
    pdf.set_font("Helvetica", "I", 16)
    pdf.set_text_color(*ACCENT)
    safe_write(pdf, "Fin.", align="C")
    pdf.ln(5)
    pdf.set_font("Helvetica", "I", 10)
    pdf.set_text_color(*SUBTLE)
    safe_write(pdf, '"Les choses les plus importantes sont rarement utiles."', align="C")

    out = os.path.join(BASE, "conte-frieren-la-neige-inutile.pdf")
    pdf.output(out)
    print(f"[OK] {out}")


# ══════════════════════════════════════════════════════════════
#  PDF 2 — 5 ideias de contos
# ══════════════════════════════════════════════════════════════

def build_ideas_pdf():
    pdf = DarkPDF()
    pdf.set_auto_page_break(auto=True, margin=20)
    pdf.add_page()

    # ── Cover ──
    pdf.ln(10)
    add_image_banner(pdf, os.path.join(IMG, "frieren1.jpg"), max_h=80)
    pdf.ln(3)
    pdf.set_font("Helvetica", "B", 24)
    pdf.set_text_color(*TITLE)
    safe_write(pdf, "Contes de Frieren", align="C")
    pdf.ln(2)
    pdf.set_font("Helvetica", "I", 14)
    pdf.set_text_color(*ACCENT)
    safe_write(pdf, "5 ideias para escolher", align="C")
    pdf.ln(4)
    pdf.set_font("Helvetica", "", 10)
    pdf.set_text_color(*SUBTLE)
    safe_write(pdf, "Cada ideia vira um conto de ~1000 palavras em frances,", align="C")
    safe_write(pdf, "nivel A2, contemplativo e filosofico.", align="C")

    ideas = [
        {
            "num": "1",
            "title": "La chanson que personne n'entend",
            "subtitle": "A cancao que ninguem ouve",
            "hook": "Frieren encontra um instrumento magico em ruinas. Quando tocado, ele reproduz a ultima musica que alguem tocou naquele lugar -- uma cancao de 800 anos atras. Mas so quem tem mais de mil anos consegue ouvi-la.",
            "theme": "Percepcao do tempo. O que significa ouvir algo que nao foi feito para voce? Frieren e a unica pessoa viva que pode ouvir essa musica, e isso a faz se perguntar: quando voce e a unica testemunha de algo, aquilo realmente existiu?",
            "ending": "Frieren ensina Fern a melodia de ouvido. Agora duas pessoas conhecem a cancao. Isso e suficiente para que ela exista.",
            "vocab": "musique, instrument, son, ecouter, entendre, chanter, se souvenir, le temps, les ruines, seul/seule"
        },
        {
            "num": "2",
            "title": "Le village qui a oublie la guerre",
            "subtitle": "A vila que esqueceu a guerra",
            "hook": "Frieren passa por um vilarejo pacifico e descobre que seus habitantes nao sabem que houve uma guerra contra o Rei dos Demonios. Para eles, o mundo sempre foi assim. A paz e tao antiga que virou esquecimento.",
            "theme": "A ironia da vitoria. Himmel e os herois lutaram para que as pessoas pudessem viver sem medo -- e o resultado e que ninguem se lembra deles. Frieren reflete: a melhor vitoria e aquela que as pessoas nem sabem que aconteceu?",
            "ending": "Uma crianca pergunta a Frieren quem e Himmel. Frieren se senta e conta a historia. Nao porque e importante para o mundo. Porque e importante para ela.",
            "vocab": "le village, la guerre, la paix, les habitants, oublier, se souvenir, un heros, raconter, une histoire, les enfants"
        },
        {
            "num": "3",
            "title": "La carte qui ne mene nulle part",
            "subtitle": "O mapa que nao leva a lugar nenhum",
            "hook": "Frieren encontra um mapa antigo feito por Himmel durante a jornada. O mapa marca um lugar que Himmel chamou de 'Le plus bel endroit du monde'. Frieren nunca ouviu ele mencionar esse lugar. Ela decide ir ate la.",
            "theme": "A busca e mais importante que o destino. O lugar marcado no mapa e uma colina comum, sem nada especial. Mas quando Frieren chega, ela encontra uma mensagem gravada numa pedra: a data e o dia em que Himmel conheceu Frieren.",
            "ending": "O lugar mais bonito do mundo nao era um lugar. Era um momento. Frieren se senta na colina e, pela primeira vez, entende por que Himmel sorria tanto.",
            "vocab": "une carte, un chemin, chercher, trouver, une colline, une pierre, une date, le plus bel endroit, un sourire, comprendre"
        },
        {
            "num": "4",
            "title": "Le jardin de la mage oubliee",
            "subtitle": "O jardim da maga esquecida",
            "hook": "Frieren descobre um jardim magico no meio de uma floresta. As flores nunca murcham. As arvores nunca perdem as folhas. Uma maga elfa criou esse jardim ha 2000 anos como um presente para uma amiga humana. A amiga morreu. A maga partiu. O jardim ficou.",
            "theme": "O que sobrevive a nos. Frieren percebe que a maga esquecida fez exatamente o que ela faz: colecionar coisas aparentemente inuteis por razoes que so fazem sentido para quem as viveu. O jardim e um sort de amor congelado no tempo.",
            "ending": "Frieren planta uma flor nova no jardim. Uma Sternblume. Para Himmel. Daqui a 2000 anos, alguem vai encontrar esse jardim e nao vai saber por que existe uma Sternblume entre as outras flores. Mas ela estara la.",
            "vocab": "un jardin, une fleur, un arbre, planter, une foret, eternel, une amie, le temps, une elfe, un cadeau"
        },
        {
            "num": "5",
            "title": "Les etoiles qu'on ne voit qu'une fois",
            "subtitle": "As estrelas que so se ve uma vez",
            "hook": "A cada 1000 anos, uma constelacao rara aparece no ceu por uma unica noite. Frieren ja viu essa constelacao duas vezes. Da primeira vez, ela estava sozinha e nao prestou atencao. Da segunda, ela estava com Himmel e ele ficou acordado a noite toda para ver.",
            "theme": "A diferenca entre ver e olhar. Frieren viu a constelacao duas vezes, mas so 'olhou' de verdade uma vez -- quando Himmel a fez parar e prestar atencao. Agora a constelacao vai aparecer de novo e Frieren quer mostrar a Fern.",
            "ending": "Fern adormece antes da constelacao aparecer. Frieren a cobre com um cobertor e fica olhando sozinha. Mas desta vez, pela primeira vez, ela nao esta realmente sozinha. Ela sabe que Fern esta ali. E isso muda tudo.",
            "vocab": "les etoiles, le ciel, la nuit, une constellation, regarder, voir, dormir, un reve, la lumiere, ensemble"
        }
    ]

    img_files = ["frieren2.jpg", "frieren3.jpg", "frieren4.jpg", "frieren2.jpg", "frieren3.jpg"]

    for idx, idea in enumerate(ideas):
        pdf.add_page()

        # Small image at top
        add_image_banner(pdf, os.path.join(IMG, img_files[idx]), max_h=45)

        # Number + Title
        pdf.set_font("Helvetica", "B", 9)
        pdf.set_text_color(*SUBTLE)
        safe_write(pdf, f"IDEIA {idea['num']}")
        pdf.ln(1)

        pdf.set_font("Helvetica", "B", 18)
        pdf.set_text_color(*TITLE)
        safe_write(pdf, idea["title"])

        pdf.set_font("Helvetica", "I", 11)
        pdf.set_text_color(*SUBTLE)
        safe_write(pdf, idea["subtitle"])
        pdf.ln(4)

        add_separator(pdf)

        # Hook
        pdf.set_font("Helvetica", "B", 10)
        pdf.set_text_color(*ACCENT)
        safe_write(pdf, "PREMISSA")
        pdf.ln(1)
        pdf.set_font("Helvetica", "", 10)
        pdf.set_text_color(*TEXT)
        safe_write(pdf, idea["hook"])
        pdf.ln(3)

        # Theme
        pdf.set_font("Helvetica", "B", 10)
        pdf.set_text_color(*ACCENT)
        safe_write(pdf, "TEMA FILOSOFICO")
        pdf.ln(1)
        pdf.set_font("Helvetica", "", 10)
        pdf.set_text_color(*TEXT)
        safe_write(pdf, idea["theme"])
        pdf.ln(3)

        # Ending
        pdf.set_font("Helvetica", "B", 10)
        pdf.set_text_color(*ACCENT)
        safe_write(pdf, "FINAL")
        pdf.ln(1)
        pdf.set_font("Helvetica", "I", 10)
        pdf.set_text_color(*TEXT)
        safe_write(pdf, idea["ending"])
        pdf.ln(4)

        # Vocab
        add_separator(pdf)
        pdf.set_font("Helvetica", "B", 9)
        pdf.set_text_color(*SUBTLE)
        safe_write(pdf, "VOCABULARIO-CHAVE")
        pdf.ln(1)
        pdf.set_font("Helvetica", "I", 9)
        pdf.set_text_color(*SUBTLE)
        safe_write(pdf, idea["vocab"])

    out = os.path.join(BASE, "ideias-contos-frieren.pdf")
    pdf.output(out)
    print(f"[OK] {out}")


if __name__ == "__main__":
    build_story_pdf()
    build_ideas_pdf()
