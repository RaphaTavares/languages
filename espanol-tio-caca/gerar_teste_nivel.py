"""
Gera o PDF do Teste de Nível de Espanhol para o Tio Caça.
Versão limpa (sem gabarito) para o aluno responder.
"""

from fpdf import FPDF

FONT_DIR = "C:/Windows/Fonts/"

# Cores
BG = (255, 255, 255)
TEXT = (40, 40, 40)
TITLE_COLOR = (180, 50, 50)
SECTION_COLOR = (50, 90, 160)
ACCENT = (100, 100, 100)
LINE_COLOR = (200, 200, 200)
TABLE_HEADER_BG = (50, 90, 160)
TABLE_HEADER_TEXT = (255, 255, 255)
TABLE_ROW_BG = (245, 245, 250)
TABLE_BORDER = (180, 180, 190)


class TestePDF(FPDF):
    def __init__(self):
        super().__init__()
        self.add_font("Cal", "", f"{FONT_DIR}calibri.ttf")
        self.add_font("Cal", "B", f"{FONT_DIR}calibrib.ttf")
        self.add_font("Cal", "I", f"{FONT_DIR}calibrii.ttf")
        self.add_font("Cal", "BI", f"{FONT_DIR}calibriz.ttf")
        self.set_auto_page_break(auto=True, margin=20)

    def header(self):
        if self.page_no() > 1:
            self.set_font("Cal", "I", 8)
            self.set_text_color(*ACCENT)
            self.cell(0, 8, "Teste de Nível — Espanhol", align="R")
            self.ln(4)

    def footer(self):
        self.set_y(-15)
        self.set_font("Cal", "I", 8)
        self.set_text_color(*ACCENT)
        self.cell(0, 10, f"Página {self.page_no()}", align="C")

    def title_page(self):
        self.add_page()
        self.ln(60)
        self.set_font("Cal", "B", 36)
        self.set_text_color(*TITLE_COLOR)
        self.cell(0, 15, "Teste de Nível", align="C", new_x="LMARGIN", new_y="NEXT")
        self.set_font("Cal", "B", 28)
        self.set_text_color(*SECTION_COLOR)
        self.cell(0, 15, "Espanhol", align="C", new_x="LMARGIN", new_y="NEXT")
        self.ln(15)
        self.set_draw_color(*TITLE_COLOR)
        self.set_line_width(0.8)
        x_center = self.w / 2
        self.line(x_center - 40, self.get_y(), x_center + 40, self.get_y())
        self.ln(15)
        self.set_font("Cal", "", 14)
        self.set_text_color(*TEXT)
        self.cell(0, 10, "Aluno: Caça", align="C", new_x="LMARGIN", new_y="NEXT")
        self.ln(30)
        self.set_font("Cal", "I", 11)
        self.set_text_color(*ACCENT)
        self.multi_cell(0, 7,
            "Instruções: Responda o que souber. Não consulte nada.\n"
            "Se não souber, deixe em branco — o objetivo é descobrir\n"
            "o que você já sabe e o que precisa estudar.",
            align="C"
        )

    def section_title(self, text):
        self.ln(6)
        self.set_font("Cal", "B", 14)
        self.set_text_color(*SECTION_COLOR)
        self.set_draw_color(*SECTION_COLOR)
        self.cell(0, 10, text, new_x="LMARGIN", new_y="NEXT")
        self.set_line_width(0.4)
        self.line(self.l_margin, self.get_y(), self.w - self.r_margin, self.get_y())
        self.ln(4)

    def question(self, num, text):
        self.ln(3)
        self.set_font("Cal", "B", 11)
        self.set_text_color(*TITLE_COLOR)
        self.cell(10, 7, f"{num}.")
        self.set_font("Cal", "", 11)
        self.set_text_color(*TEXT)
        self.multi_cell(0, 7, text)

    def sub_item(self, letter, text, answer_line=False):
        self.set_font("Cal", "", 11)
        self.set_text_color(*TEXT)
        x_start = self.l_margin + 10
        self.set_x(x_start)
        self.cell(8, 7, f"{letter})")
        if answer_line:
            self.cell(0, 7, text)
            self.ln()
            self.set_x(x_start + 8)
            self.set_draw_color(*LINE_COLOR)
            self.set_line_width(0.3)
            line_w = self.w - self.r_margin - (x_start + 8)
            self.line(self.get_x(), self.get_y(), self.get_x() + line_w, self.get_y())
            self.ln(4)
        else:
            self.multi_cell(0, 7, text)

    def answer_lines(self, count=2):
        self.set_draw_color(*LINE_COLOR)
        self.set_line_width(0.3)
        x_start = self.l_margin + 10
        line_w = self.w - self.r_margin - x_start
        for _ in range(count):
            self.ln(6)
            self.set_x(x_start)
            self.line(x_start, self.get_y(), x_start + line_w, self.get_y())
        self.ln(3)

    def blank_table(self, headers, num_rows=1):
        self.ln(2)
        col_w = (self.w - self.l_margin - self.r_margin) / len(headers)
        row_h = 10

        # Header
        self.set_font("Cal", "B", 10)
        self.set_fill_color(*TABLE_HEADER_BG)
        self.set_text_color(*TABLE_HEADER_TEXT)
        self.set_draw_color(*TABLE_BORDER)
        for h in headers:
            self.cell(col_w, row_h, h, border=1, fill=True, align="C")
        self.ln()

        # Empty rows
        self.set_font("Cal", "", 10)
        self.set_text_color(*TEXT)
        self.set_fill_color(*TABLE_ROW_BG)
        for _ in range(num_rows):
            for _ in headers:
                self.cell(col_w, row_h, "", border=1, fill=True, align="C")
            self.ln()
        self.ln(2)

    def vocab_table(self, rows):
        """Table with PT column filled and ES column blank."""
        self.ln(2)
        col_w = (self.w - self.l_margin - self.r_margin) / 2
        row_h = 9

        # Header
        self.set_font("Cal", "B", 10)
        self.set_fill_color(*TABLE_HEADER_BG)
        self.set_text_color(*TABLE_HEADER_TEXT)
        self.set_draw_color(*TABLE_BORDER)
        self.cell(col_w, row_h, "Português", border=1, fill=True, align="C")
        self.cell(col_w, row_h, "Espanhol", border=1, fill=True, align="C")
        self.ln()

        # Rows
        self.set_font("Cal", "", 10)
        self.set_fill_color(*TABLE_ROW_BG)
        self.set_text_color(*TEXT)
        for pt_word in rows:
            self.cell(col_w, row_h, pt_word, border=1, fill=True, align="C")
            self.cell(col_w, row_h, "", border=1, fill=True, align="C")
            self.ln()
        self.ln(2)

    def ser_estar_table(self):
        self.ln(2)
        col1_w = (self.w - self.l_margin - self.r_margin) * 0.6
        col2_w = (self.w - self.l_margin - self.r_margin) * 0.4
        row_h = 9

        self.set_font("Cal", "B", 10)
        self.set_fill_color(*TABLE_HEADER_BG)
        self.set_text_color(*TABLE_HEADER_TEXT)
        self.set_draw_color(*TABLE_BORDER)
        self.cell(col1_w, row_h, "Frase", border=1, fill=True, align="C")
        self.cell(col2_w, row_h, "Ser ou Estar?", border=1, fill=True, align="C")
        self.ln()

        frases = [
            "a) Yo ________ brasileño.",
            "b) Juiz de Fora ________ en Minas Gerais.",
            "c) Hoy yo ________ cansado.",
            "d) Mi sobrino Raphael ________ programador.",
            "e) La playa ________ muy bonita hoy.",
        ]
        self.set_font("Cal", "", 10)
        self.set_fill_color(*TABLE_ROW_BG)
        self.set_text_color(*TEXT)
        for frase in frases:
            self.cell(col1_w, row_h, frase, border=1, fill=True)
            self.cell(col2_w, row_h, "", border=1, fill=True, align="C")
            self.ln()
        self.ln(2)

    def write_body(self, text):
        self.set_x(self.l_margin + 10)
        self.set_font("Cal", "", 11)
        self.set_text_color(*TEXT)
        w = self.w - self.l_margin - self.r_margin - 10
        self.multi_cell(w, 7, text)

    def write_italic(self, text):
        self.set_x(self.l_margin + 10)
        self.set_font("Cal", "I", 10)
        self.set_text_color(*ACCENT)
        w = self.w - self.l_margin - self.r_margin - 10
        self.multi_cell(w, 6, text)

    def text_block(self, text):
        """Bordered text block for reading comprehension."""
        self.ln(2)
        self.set_fill_color(248, 248, 252)
        self.set_draw_color(*SECTION_COLOR)
        self.set_line_width(0.4)
        x = self.l_margin + 5
        w = self.w - self.l_margin - self.r_margin - 10
        self.set_x(x)
        self.set_font("Cal", "I", 11)
        self.set_text_color(60, 60, 70)
        y_start = self.get_y()
        self.multi_cell(w, 7, text, border=0)
        y_end = self.get_y()
        # Draw border
        self.rect(x - 3, y_start - 2, w + 6, y_end - y_start + 4)
        self.ln(3)


def build_pdf():
    pdf = TestePDF()

    # --- TITLE PAGE ---
    pdf.title_page()

    # --- PARTE 1 ---
    pdf.add_page()
    pdf.section_title("Parte 1 — Vocabulário e Frases Básicas")

    pdf.question(1, 'Como você diria "Bom dia" e "Boa noite" em espanhol?')
    pdf.answer_lines(2)

    pdf.question(2, "Traduza para o espanhol:")
    pdf.sub_item("a", "Eu me chamo Caça e moro em Juiz de Fora.", answer_line=True)
    pdf.sub_item("b", "Eu trabalho no IBGE.", answer_line=True)
    pdf.sub_item("c", "Eu tenho uma cachorra chamada Bolinha.", answer_line=True)

    pdf.question(3, "Qual a tradução dessas palavras para o espanhol?")
    pdf.write_italic("Se não souber, chute — quero ver se você cai nos falsos amigos.")
    pdf.vocab_table(["sobremesa", "escritório", "copo", "grávida", "largo"])

    # --- PARTE 2 ---
    pdf.section_title("Parte 2 — Verbos no Presente")

    pdf.question(4, "Conjugue o verbo hablar (falar) no presente para todas as pessoas:")
    pdf.blank_table(["yo", "tú", "él/ella", "nosotros", "ellos/ellas"])

    pdf.question(5, "Complete com ser ou estar:")
    pdf.ser_estar_table()

    pdf.question(6, "Traduza para o espanhol:")
    pdf.sub_item("a", "Eu vou à praia todo fim de semana.", answer_line=True)
    pdf.sub_item("b", "Nós queremos viajar para o Rio de Janeiro.", answer_line=True)

    # --- PARTE 3 ---
    pdf.section_title("Parte 3 — Passado")

    pdf.question(7, "Coloque as frases no passado:")
    pdf.sub_item("a", "Yo viajo a la playa. (ontem)", answer_line=True)
    pdf.sub_item("b", "Nosotros bailamos en la discoteca. (sábado passado)", answer_line=True)
    pdf.sub_item("c", "Raphael me llama por teléfono. (esta manhã)", answer_line=True)

    pdf.question(8, "Qual a diferença entre estas duas frases?")
    pdf.write_body('a) Cuando era joven, iba a la playa todos los veranos.')
    pdf.write_body('b) El año pasado, fui a la playa con mis amigos.')
    pdf.answer_lines(3)

    pdf.question(9, "Traduza para o espanhol:")
    pdf.sub_item("a", "Quando eu era criança, eu assistia muita TV.", answer_line=True)
    pdf.sub_item("b", "Ontem eu saí com meus amigos e fomos a uma balada em BH.", answer_line=True)

    # --- PARTE 4 ---
    pdf.add_page()
    pdf.section_title("Parte 4 — Estruturas Intermediárias")

    pdf.question(10, "Complete com a forma correta do verbo:")
    pdf.sub_item("a", "Mañana yo ________ (ir) a la montaña.", answer_line=True)
    pdf.sub_item("b", "Si tuviera vacaciones, ________ (viajar) a España.", answer_line=True)
    pdf.sub_item("c", "Me gustaría ________ (conocer) Buenos Aires.", answer_line=True)

    pdf.question(11, "Substitua a parte sublinhada por um pronome:")
    pdf.sub_item("a", "Yo compré el regalo para mi sobrino. →", answer_line=True)
    pdf.sub_item("b", "Ella dio las flores a su madre. →", answer_line=True)

    pdf.question(12, "Passe para a forma negativa:")
    pdf.sub_item("a", "Yo siempre viajo en avión.", answer_line=True)
    pdf.sub_item("b", "Alguien llamó a la puerta.", answer_line=True)
    pdf.sub_item("c", "Tengo algo para ti.", answer_line=True)

    # --- PARTE 5 ---
    pdf.section_title("Parte 5 — Subjuntivo e Estruturas Avançadas")

    pdf.question(13, "Complete com indicativo ou subjuntivo:")
    pdf.sub_item("a", "Creo que él ________ (estar) en casa.", answer_line=True)
    pdf.sub_item("b", "No creo que él ________ (estar) en casa.", answer_line=True)
    pdf.sub_item("c", "Espero que tú ________ (venir) a mi fiesta.", answer_line=True)
    pdf.sub_item("d", "Es importante que nosotros ________ (hablar) español.", answer_line=True)

    pdf.question(14, "Transforme em discurso indireto:")
    pdf.write_body('María dijo: "Voy a la playa mañana."')
    pdf.write_body("→ María dijo que ...")
    pdf.answer_lines(2)

    pdf.question(15, "O que significa esta frase?")
    pdf.write_body('"Aunque llueva, iremos a la playa."')
    pdf.answer_lines(2)

    # --- PARTE 6 ---
    pdf.section_title("Parte 6 — Compreensão")

    pdf.question(16, "Leia o texto e responda as perguntas:")
    pdf.text_block(
        "Carlos trabaja en una oficina del gobierno. Todos los días se levanta a las siete, "
        "desayuna con su perra Luna y sale de casa a las ocho. Los fines de semana le gusta "
        "ir a la playa o salir con sus amigos. El sábado pasado fue a una discoteca en Río de "
        "Janeiro y bailó hasta las cuatro de la mañana. El domingo durmió hasta las dos de la tarde."
    )
    pdf.sub_item("a", "Onde Carlos trabalha?", answer_line=True)
    pdf.sub_item("b", "O que ele faz nos fins de semana?", answer_line=True)
    pdf.sub_item("c", "O que aconteceu no sábado passado?", answer_line=True)
    pdf.sub_item("d", "Até que horas ele dormiu no domingo?", answer_line=True)

    pdf.question(17, "Qual dessas frases está errada? Corrija.")
    pdf.sub_item("a", "Yo soy cansado.")
    pdf.sub_item("b", "Me gusta las series.")
    pdf.sub_item("c", "Él tiene mucho hambre.")
    pdf.sub_item("d", "Vamos a ir al cine mañana.")
    pdf.answer_lines(3)

    # --- PARTE 7 ---
    pdf.add_page()
    pdf.section_title("Parte 7 — Produção Livre")

    pdf.question(18, "Escreva 3-5 frases em espanhol se apresentando (nome, cidade, trabalho, o que gosta de fazer).")
    pdf.answer_lines(5)

    pdf.question(19, "Escreva 3-5 frases em espanhol contando o que você fez no último fim de semana.")
    pdf.answer_lines(5)

    pdf.question(20, "Escreva 2-3 frases em espanhol sobre o que você gostaria de fazer nas próximas férias.")
    pdf.answer_lines(4)

    # --- Final ---
    pdf.ln(15)
    pdf.set_draw_color(*TITLE_COLOR)
    pdf.set_line_width(0.5)
    x_center = pdf.w / 2
    pdf.line(x_center - 30, pdf.get_y(), x_center + 30, pdf.get_y())
    pdf.ln(8)
    pdf.set_font("Cal", "I", 11)
    pdf.set_text_color(*ACCENT)
    pdf.cell(0, 8, "¡Buena suerte, Caça!", align="C")

    output_path = "C:/reps/languages/espanol-tio-caca/teste-de-nivel.pdf"
    pdf.output(output_path)
    print(f"PDF gerado: {output_path}")
    print(f"Páginas: {pdf.pages_count}")


if __name__ == "__main__":
    build_pdf()
