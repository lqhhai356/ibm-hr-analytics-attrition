# -*- coding: utf-8 -*-
"""Dựng báo cáo PDF từ kết quả của notebook HR_Attrition_Analysis.ipynb.

Quy trình: chạy notebook (Run all) -> sinh figures/ và outputs/ -> chạy  python generate_report.py
Bảng số liệu được đọc trực tiếp từ outputs/ (results.json và các file CSV) nên luôn khớp với notebook.
Cần: reportlab, pandas, Pillow (pip install reportlab pandas pillow).
"""
import json
import os

import pandas as pd
from PIL import Image as PILImage
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import cm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (BaseDocTemplate, Frame, Image, KeepTogether, NextPageTemplate, PageBreak,
                                PageTemplate, Paragraph, Spacer, Table, TableStyle)
from reportlab.platypus.tableofcontents import TableOfContents

import report_config as CFG

HERE = os.path.dirname(os.path.abspath(__file__))
FIG = os.path.join(HERE, "figures")
OUT = os.path.join(HERE, "outputs")

# ----------------------------------------------------------------------------- fonts
FONT_DIR = os.path.join(HERE, "fonts")
pdfmetrics.registerFont(TTFont("DV", os.path.join(FONT_DIR, "DejaVuSans.ttf")))
pdfmetrics.registerFont(TTFont("DV-B", os.path.join(FONT_DIR, "DejaVuSans-Bold.ttf")))
pdfmetrics.registerFont(TTFont("DV-I", os.path.join(FONT_DIR, "DejaVuSans-Oblique.ttf")))
pdfmetrics.registerFont(TTFont("DV-BI", os.path.join(FONT_DIR, "DejaVuSans-BoldOblique.ttf")))
pdfmetrics.registerFontFamily("DV", normal="DV", bold="DV-B", italic="DV-I", boldItalic="DV-BI")

NAVY = colors.HexColor("#1F3A5F")
RED = colors.HexColor("#C0392B")
GREY = colors.HexColor("#5F6B7A")
LIGHT = colors.HexColor("#F2F5F9")
HEAD_BG = colors.HexColor("#DCE5F0")
GRID = colors.HexColor("#B8C4D3")

ST = {
    "body": ParagraphStyle("body", fontName="DV", fontSize=9.6, leading=14, alignment=TA_JUSTIFY, spaceAfter=5),
    "bullet": ParagraphStyle("bullet", fontName="DV", fontSize=9.6, leading=14, alignment=TA_JUSTIFY,
                             leftIndent=14, bulletIndent=4, spaceAfter=3),
    "H1": ParagraphStyle("H1", fontName="DV-B", fontSize=14.5, leading=19, textColor=NAVY, spaceBefore=4, spaceAfter=9),
    "H2": ParagraphStyle("H2", fontName="DV-B", fontSize=11.5, leading=15, textColor=NAVY, spaceBefore=10, spaceAfter=5),
    "H3": ParagraphStyle("H3", fontName="DV-B", fontSize=10, leading=13.5, textColor=NAVY, spaceBefore=6, spaceAfter=4),
    "cap": ParagraphStyle("cap", fontName="DV-I", fontSize=8.6, leading=11.5, alignment=TA_CENTER, textColor=GREY,
                          spaceBefore=3, spaceAfter=8),
    "tcap": ParagraphStyle("tcap", fontName="DV-I", fontSize=8.6, leading=11.5, alignment=TA_LEFT, textColor=GREY,
                           spaceBefore=4, spaceAfter=3),
    "cell": ParagraphStyle("cell", fontName="DV", fontSize=8.2, leading=10.6),
    "cellb": ParagraphStyle("cellb", fontName="DV-B", fontSize=8.2, leading=10.6),
    "box_t": ParagraphStyle("box_t", fontName="DV-B", fontSize=9.4, leading=13, textColor=NAVY, spaceAfter=3),
    "box": ParagraphStyle("box", fontName="DV", fontSize=9.1, leading=13, alignment=TA_JUSTIFY, spaceAfter=3),
    "toc1": ParagraphStyle("toc1", fontName="DV-B", fontSize=10, leading=15, spaceBefore=5),
    "toc2": ParagraphStyle("toc2", fontName="DV", fontSize=9.2, leading=13, leftIndent=16),
}

# ----------------------------------------------------------------------------- data
R = json.load(open(os.path.join(OUT, "results.json"), encoding="utf-8"))
SCREEN = pd.read_csv(os.path.join(OUT, "screening_tests.csv"))
OUTL = pd.read_csv(os.path.join(OUT, "outlier_table.csv"))
SEG = pd.read_csv(os.path.join(OUT, "risk_segments.csv"))
TOPK = pd.read_csv(os.path.join(OUT, "topk_risk.csv"))
HYP = pd.read_csv(os.path.join(OUT, "hypothesis_summary.csv"))
COEF = pd.read_csv(os.path.join(OUT, "logreg_coefficients.csv"), index_col=0)
M = R["model"]


# ----------------------------------------------------------------------------- formatting helpers (kiểu số Việt Nam)
def vn(x, d=1):
    s = f"{x:,.{d}f}"
    return s.replace(",", "§").replace(".", ",").replace("§", ".")


def pct(x, d=1):
    return vn(x, d) + "%"


def sci(p, d=1):
    """p-value: số thập phân nếu >= 0,001, ngược lại dạng a×10^b; p = 0 do tràn số -> < 10^-16."""
    if p <= 0:
        return "&lt; 10<super>−16</super>"
    if p >= 0.001:
        return vn(p, 3)
    m, e = f"{p:.{d}e}".split("e")
    return f"{m.replace('.', ',')}×10<super>−{int(e[1:])}</super>"


def P(text, style="body"):
    return Paragraph(text, ST[style])


def bullets(items):
    return [Paragraph(t, ST["bullet"], bulletText="•") for t in items]


def table(rows, widths, header=True, font=None, zebra=True, align_right_cols=()):
    data = []
    for r_i, row in enumerate(rows):
        st = ST["cellb"] if (header and r_i == 0) else ST["cell"]
        data.append([c if not isinstance(c, str) else Paragraph(c, st) for c in row])
    t = Table(data, colWidths=widths, repeatRows=1 if header else 0, hAlign="CENTER", spaceAfter=8)
    style = [("GRID", (0, 0), (-1, -1), 0.4, GRID),
             ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
             ("TOPPADDING", (0, 0), (-1, -1), 3), ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
             ("LEFTPADDING", (0, 0), (-1, -1), 4), ("RIGHTPADDING", (0, 0), (-1, -1), 4)]
    if header:
        style.append(("BACKGROUND", (0, 0), (-1, 0), HEAD_BG))
    if zebra:
        for i in range(1 if header else 0, len(rows)):
            if i % 2 == 0:
                style.append(("BACKGROUND", (0, i), (-1, i), colors.HexColor("#F8FAFC")))
    t.setStyle(TableStyle(style))
    return t


_tab_no = [0]
_fig_no = [0]


def tcap(text):
    _tab_no[0] += 1
    return P(f"Bảng {_tab_no[0]}. {text}", "tcap")


def fig(name, caption, width=16.2, max_h=11.5):
    _fig_no[0] += 1
    path = os.path.join(FIG, name)
    w, h = PILImage.open(path).size
    W = width * cm
    H = W * h / w
    if H > max_h * cm:
        H = max_h * cm
        W = H * w / h
    return KeepTogether([Image(path, width=W, height=H), P(f"Hình {_fig_no[0]}. {caption}", "cap")])


def insight(so_lieu, nhan_dinh, y_nghia, title="Phân tích chuyên sâu (Deep Insight)"):
    inner = [P(title, "box_t"),
             P(f"<b>Số liệu.</b> {so_lieu}", "box"),
             P(f"<b>Nhận định.</b> {nhan_dinh}", "box"),
             P(f"<b>Ý nghĩa.</b> {y_nghia}", "box")]
    t = Table([[inner]], colWidths=[16.4 * cm])
    t.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), LIGHT),
                           ("LINEBEFORE", (0, 0), (0, -1), 3.2, NAVY),
                           ("LEFTPADDING", (0, 0), (-1, -1), 10), ("RIGHTPADDING", (0, 0), (-1, -1), 9),
                           ("TOPPADDING", (0, 0), (-1, -1), 7), ("BOTTOMPADDING", (0, 0), (-1, -1), 5)]))
    return [Spacer(1, 2), t, Spacer(1, 8)]


def note_box(title, paras):
    inner = [P(title, "box_t")] + [P(x, "box") for x in paras]
    t = Table([[inner]], colWidths=[16.4 * cm])
    t.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#FBF4EC")),
                           ("LINEBEFORE", (0, 0), (0, -1), 3.2, colors.HexColor("#D9822B")),
                           ("LEFTPADDING", (0, 0), (-1, -1), 10), ("RIGHTPADDING", (0, 0), (-1, -1), 9),
                           ("TOPPADDING", (0, 0), (-1, -1), 7), ("BOTTOMPADDING", (0, 0), (-1, -1), 5)]))
    return [Spacer(1, 2), t, Spacer(1, 8)]


STD_RULE = "Bác bỏ H₀ nếu p sau hiệu chỉnh Bonferroni &lt; 0,05; đọc kèm effect size và chênh lệch tỷ lệ để đánh giá ý nghĩa thực tế."


def five_steps(h0, h1, data, test, rule=STD_RULE):
    rows = [["Bước", "Nội dung"],
            ["1. Cặp giả thuyết", f"<b>H₀:</b> {h0}<br/><b>H₁:</b> {h1}"],
            ["2. Dữ liệu và giả định", data],
            ["3. Kiểm định", test],
            ["4. Tính toán", "Thống kê kiểm định, p-value, effect size trong notebook; p hiệu chỉnh Bonferroni (×30) và FDR lấy từ bước sàng lọc (mục 4.2)."],
            ["5. Quy tắc kết luận", rule]]
    t = table(rows, [3.6 * cm, 12.8 * cm])
    return [P("Khung kiểm định 5 bước", "H3"), t, Spacer(1, 6)]


def H1(text):
    p = P(text, "H1")
    p._toc = (0, text)
    return p


def H2(text):
    p = P(text, "H2")
    p._toc = (1, text)
    return p


def sv(var, col):
    return SCREEN.set_index("variable").loc[var, col]


# ----------------------------------------------------------------------------- document
class ReportDoc(BaseDocTemplate):
    def __init__(self, fn):
        super().__init__(fn, pagesize=A4, leftMargin=2.2 * cm, rightMargin=2.2 * cm, topMargin=2 * cm,
                         bottomMargin=2 * cm, title="Báo cáo phân tích nghỉ việc nhân viên – IBM HR Analytics",
                         author=CFG.GROUP_NAME, subject="Mid-Term 2 – Khoa học dữ liệu")
        frame = Frame(self.leftMargin, self.bottomMargin, self.width, self.height, id="f")
        self.addPageTemplates([PageTemplate(id="cover", frames=[frame], onPage=self._cover_bg),
                               PageTemplate(id="body", frames=[frame], onPage=self._footer)])

    def afterFlowable(self, flowable):
        if hasattr(flowable, "_toc"):
            level, text = flowable._toc
            key = f"h{id(flowable)}"
            self.canv.bookmarkPage(key)
            self.canv.addOutlineEntry(text, key, level=level, closed=level > 0)
            self.notify("TOCEntry", (level, text, self.page, key))

    @staticmethod
    def _cover_bg(canv, doc):
        canv.saveState()
        canv.setStrokeColor(NAVY)
        canv.setLineWidth(2)
        canv.rect(1.3 * cm, 1.3 * cm, A4[0] - 2.6 * cm, A4[1] - 2.6 * cm)
        canv.setLineWidth(0.6)
        canv.rect(1.45 * cm, 1.45 * cm, A4[0] - 2.9 * cm, A4[1] - 2.9 * cm)
        canv.restoreState()

    @staticmethod
    def _footer(canv, doc):
        canv.saveState()
        canv.setStrokeColor(GRID)
        canv.setLineWidth(0.5)
        canv.line(2.2 * cm, 1.5 * cm, A4[0] - 2.2 * cm, 1.5 * cm)
        canv.setFont("DV", 7.8)
        canv.setFillColor(GREY)
        canv.drawString(2.2 * cm, 1.05 * cm, "Báo cáo Mid-Term 2 – Phân tích nghỉ việc nhân viên (IBM HR Analytics)")
        canv.drawRightString(A4[0] - 2.2 * cm, 1.05 * cm, f"Trang {doc.page}")
        canv.restoreState()


# ----------------------------------------------------------------------------- cover
def logo_cell(path, label):
    full = os.path.join(HERE, path)
    if os.path.exists(full):
        w, h = PILImage.open(full).size
        H = 2.6 * cm
        W = min(H * w / h, 5.5 * cm)
        return Image(full, width=W, height=W * h / w)
    t = Table([[Paragraph(label, ParagraphStyle("lg", fontName="DV", fontSize=8, textColor=GREY, alignment=TA_CENTER))]],
              colWidths=[3.6 * cm], rowHeights=[2.6 * cm])
    t.setStyle(TableStyle([("BOX", (0, 0), (-1, -1), 0.6, GRID), ("VALIGN", (0, 0), (-1, -1), "MIDDLE")]))
    return t


def cover():
    c = ParagraphStyle
    s = []
    logos = Table([[logo_cell(CFG.LOGO_TRUONG, "Logo Trường"), logo_cell(CFG.LOGO_AEP, "Logo Viện AEP")]],
                  colWidths=[8 * cm, 8 * cm])
    logos.setStyle(TableStyle([("ALIGN", (0, 0), (-1, -1), "CENTER"), ("VALIGN", (0, 0), (-1, -1), "MIDDLE")]))
    s += [Spacer(1, 0.6 * cm), logos, Spacer(1, 0.7 * cm)]
    s.append(Paragraph(CFG.SCHOOL_NAME, c("c1", fontName="DV-B", fontSize=13, leading=17, alignment=TA_CENTER, textColor=NAVY)))
    s.append(Paragraph(CFG.INSTITUTE_NAME, c("c2", fontName="DV-B", fontSize=11.5, leading=16, alignment=TA_CENTER, textColor=NAVY)))
    s.append(Spacer(1, 1.1 * cm))
    s.append(Paragraph(CFG.COURSE, c("c3", fontName="DV", fontSize=11, leading=16, alignment=TA_CENTER, textColor=GREY)))
    s.append(Paragraph(CFG.ASSIGNMENT, c("c4", fontName="DV", fontSize=11, leading=16, alignment=TA_CENTER, textColor=GREY)))
    s.append(Spacer(1, 1.0 * cm))
    s.append(Paragraph("BÁO CÁO PHÂN TÍCH DỮ LIỆU", c("c5", fontName="DV-B", fontSize=21, leading=27, alignment=TA_CENTER, textColor=NAVY)))
    s.append(Paragraph("Các yếu tố liên quan đến việc nhân viên nghỉ việc",
                       c("c6", fontName="DV-B", fontSize=13.5, leading=19, alignment=TA_CENTER, textColor=RED)))
    s.append(Spacer(1, 0.2 * cm))
    s.append(Paragraph("Tập dữ liệu: IBM HR Analytics Employee Attrition &amp; Performance",
                       c("c7", fontName="DV", fontSize=10, leading=14, alignment=TA_CENTER, textColor=GREY)))
    s.append(Spacer(1, 1.3 * cm))
    rows = [[Paragraph("<b>Nhóm thực hiện</b>", ST["cell"]), Paragraph(CFG.GROUP_NAME, ST["cell"]), "", ""],
            [Paragraph("<b>Thành viên</b>", ST["cell"]), Paragraph("<b>Họ và tên</b>", ST["cell"]),
             Paragraph("<b>MSSV</b>", ST["cell"]), Paragraph("<b>Nhiệm vụ</b>", ST["cell"])]]
    for name, sid, task in CFG.MEMBERS:
        rows.append(["", Paragraph(name, ST["cell"]), Paragraph(sid, ST["cell"]), Paragraph(task, ST["cell"])])
    rows.append([Paragraph("<b>Giảng viên</b>", ST["cell"]), Paragraph(CFG.LECTURER, ST["cell"]), "", ""])
    rows.append([Paragraph("<b>GitHub</b>", ST["cell"]), Paragraph(CFG.GITHUB_URL, ST["cell"]), "", ""])
    n = len(rows)
    t = Table(rows, colWidths=[3 * cm, 6.2 * cm, 2.8 * cm, 4.2 * cm])
    t.setStyle(TableStyle([("GRID", (0, 0), (-1, -1), 0.5, GRID), ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                           ("SPAN", (1, 0), (3, 0)), ("SPAN", (0, 1), (0, n - 3)),
                           ("SPAN", (1, n - 2), (3, n - 2)), ("SPAN", (1, n - 1), (3, n - 1)),
                           ("BACKGROUND", (0, 0), (0, -1), LIGHT), ("BACKGROUND", (1, 1), (-1, 1), HEAD_BG),
                           ("TOPPADDING", (0, 0), (-1, -1), 4), ("BOTTOMPADDING", (0, 0), (-1, -1), 4)]))
    s.append(t)
    s.append(Spacer(1, 1.2 * cm))
    s.append(Paragraph(CFG.DATE_TEXT, c("c8", fontName="DV", fontSize=10, alignment=TA_CENTER, textColor=GREY)))
    s.append(NextPageTemplate("body"))
    s.append(PageBreak())
    return s


# ----------------------------------------------------------------------------- content
def build_story():
    s = cover()

    # --------------------------------------------------------------- TOC
    toc = TableOfContents()
    toc.levelStyles = [ST["toc1"], ST["toc2"]]
    toc.dotsMinLevel = 1
    s += [P("MỤC LỤC", "H1"), toc, PageBreak()]

    rates = R["rates"]
    H1r = R["H1"]
    cmh_ms, cmh_jl = R["CMH"]["OverTime|MaritalStatus"], R["CMH"]["OverTime|JobLevel"]
    cmh_so = R["CMH"]["StockOption0|MaritalStatus(non-single)"]
    tk = TOPK.set_index("top_k_%")

    # --------------------------------------------------------------- Executive summary
    s.append(H1("TÓM TẮT ĐIỀU HÀNH"))
    s.append(P(f"Báo cáo phân tích tập dữ liệu IBM HR Analytics Employee Attrition &amp; Performance ({vn(R['n_rows'], 0)} nhân viên, "
               f"{R['n_cols']} thuộc tính) nhằm trả lời câu hỏi: <b>những yếu tố nào liên quan đến việc nhân viên nghỉ việc và doanh nghiệp nên làm gì "
               "để giữ chân họ</b>. Quy trình đi từ đánh giá dữ liệu, làm sạch, kiểm định giả thuyết và trực quan hóa đến khuyến nghị, đúng theo 4 giai đoạn của đề bài."))
    s.append(P("Kết quả chính", "H3"))
    s += bullets([
        "<b>Chất lượng dữ liệu tốt:</b> không có giá trị khuyết, không trùng lặp, không vi phạm logic. Chỉ loại 4 cột vô nghĩa (3 cột hằng số, 1 cột mã nhân viên). "
        "Outlier thu nhập và thâm niên là giá trị thật nên được giữ lại và xử lý độ lệch bằng log1p.",
        f"Tỷ lệ nghỉ việc chung <b>{pct(R['attr_rate'])}</b> ({R['attr_yes']} người), mất cân bằng lớp khoảng {vn(R['imbalance_ratio'])} : 1.",
        f"<b>Làm thêm giờ là yếu tố mạnh nhất có thể can thiệp:</b> {pct(rates['OverTime']['Yes']['rate'])} so với {pct(rates['OverTime']['No']['rate'])} "
        f"(odds ratio {vn(H1r['OR'], 2)}, p = {sci(H1r['p'])}). Kiểm định Cochran–Mantel–Haenszel xác nhận hiệu ứng <b>không bị nhiễu</b> bởi hôn nhân hay cấp bậc "
        f"(OR gộp ≈ {vn(cmh_ms['OR_pooled'], 1)}).",
        f"<b>Người trẻ và nhân viên mới có nguy cơ cao nhất:</b> nhóm 18–24 tuổi nghỉ {pct(rates['AgeGroup']['18–24']['rate'])}; thâm niên ≤ 1 năm nghỉ "
        f"{pct(R['H3']['first_year'])} so với {pct(R['H3']['after_first_year'])} ở nhóm còn lại.",
        "<b>Thu nhập thấp chủ yếu phản ánh cấp bậc thấp</b> (tương quan JobLevel–MonthlyIncome = 0,92): trong cùng cấp bậc, chênh lệch thu nhập không còn ý nghĩa ở 3/5 cấp.",
        f"<b>Vị trí công việc phân hóa mạnh:</b> Sales Representative {pct(rates['JobRole']['Sales Representative']['rate'])}, Laboratory Technician "
        f"{pct(rates['JobRole']['Laboratory Technician']['rate'])}, Research Director {pct(rates['JobRole']['Research Director']['rate'])}.",
        "<b>Không được ủng hộ:</b> thời gian kể từ lần thăng chức gần nhất, giới tính (biến đối chứng). Khoảng cách đi làm và phòng ban chỉ có ý nghĩa khi dùng "
        "hiệu chỉnh FDR, nên chỉ là bằng chứng yếu.",
        f"<b>Mô hình hồi quy logistic tham chiếu:</b> ROC-AUC {vn(M['test_auc'], 2)} trên tập test và {vn(M['rep_cv_auc_mean'], 2)} trung bình qua 10 lần lặp 5-fold CV. "
        f"Dùng làm danh sách ưu tiên, top 20% điểm rủi ro bao phủ {pct(tk.loc[20, 'recall'] * 100, 0)} số người nghỉ.",
    ])
    s.append(P("Khuyến nghị ưu tiên", "H3"))
    s += bullets([
        "Đặt trần giờ làm thêm và rà soát tải công việc ở các vị trí rủi ro cao (Laboratory Technician, Sales Representative).",
        "Chương trình giữ chân trong 12 tháng đầu và cho nhân viên dưới 25 tuổi (mentor, mốc đánh giá, lộ trình lên cấp).",
        "Rà soát thang lương và lộ trình từ JobLevel 1 lên 2 thay vì tăng lương đại trà.",
        "Dùng điểm rủi ro để chọn top 10–20% nhân viên cho phỏng vấn giữ chân; thí điểm có đối chứng (A/B) trước khi triển khai rộng.",
    ])
    s.append(P(f"<b>Mã nguồn và dữ liệu:</b> {CFG.GITHUB_URL}"))
    s.append(PageBreak())

    # --------------------------------------------------------------- 1. Intro
    s.append(H1("1. GIỚI THIỆU BÀI TOÁN VÀ QUY TRÌNH THỰC HIỆN"))
    s.append(H2("1.1 Bối cảnh và mục tiêu"))
    s.append(P("Nghỉ việc ngoài ý muốn làm doanh nghiệp tốn chi phí tuyển dụng, đào tạo và mất tri thức. Bộ phận nhân sự cần biết nhóm nhân viên nào dễ nghỉ việc "
               "và vì sao để can thiệp sớm. Bài toán của báo cáo: dùng dữ liệu nhân sự của IBM (biến mục tiêu <i>Attrition</i>: Yes/No) để (i) mô tả hiện trạng, "
               "(ii) kiểm định các giả thuyết quản trị nhân sự và (iii) đề xuất giải pháp giữ chân có căn cứ số liệu."))
    s.append(H2("1.2 Quy trình 4 giai đoạn"))
    s.append(tcap("Khung quy trình của báo cáo"))
    s.append(table([["Giai đoạn", "Nội dung chính", "Sản phẩm"],
                    ["1. Thu thập và đánh giá", "Nguồn, cấu trúc, kiểu dữ liệu, missing (kể cả missing ẩn), tính nhất quán, phân phối biến mục tiêu", "Mục 2, Hình 1"],
                    ["2. Tiền xử lý và làm sạch", "Trùng lặp, cột vô nghĩa, định dạng, logic, outlier (IQR, Z-score), log1p, encoding, scaling – có giải trình", "Mục 3, Hình 2–3"],
                    ["3. Phân tích và trực quan hóa", "8 giả thuyết + 1 đối chứng theo khung 5 bước; hiệu chỉnh Bonferroni và FDR; CMH cho yếu tố nhiễu; heatmap; VIF; hồi quy logistic; mỗi hình kèm Deep Insight", "Mục 4, Hình 4–16"],
                    ["4. Tác động và khuyến nghị", "Phát hiện nổi bật, phân khúc rủi ro, giải pháp, giới hạn, hướng mở rộng", "Mục 5, Hình 17"]],
                   [3.6 * cm, 9.6 * cm, 3.2 * cm]))
    s.append(H2("1.3 Công cụ"))
    s.append(P("Python (pandas, NumPy); SciPy và statsmodels cho kiểm định thống kê (Chi-square, Mann–Whitney U, Cochran–Mantel–Haenszel, FDR, VIF); "
               "scikit-learn cho chuẩn hóa và mô hình tham chiếu; Matplotlib/Seaborn cho trực quan hóa; ReportLab để dựng báo cáo. Toàn bộ mã nằm trong notebook "
               "<i>HR_Attrition_Analysis.ipynb</i> (chạy được bằng Run all trên Google Colab). Mọi số liệu, bảng và hình trong báo cáo được sinh trực tiếp từ notebook; "
               "các bảng được script <i>generate_report.py</i> đọc thẳng từ thư mục <i>outputs/</i>."))
    s.append(PageBreak())

    # --------------------------------------------------------------- 2. Stage 1
    s.append(H1("2. GIAI ĐOẠN 1 – THU THẬP VÀ ĐÁNH GIÁ DỮ LIỆU BAN ĐẦU"))
    s.append(H2("2.1 Nguồn dữ liệu và mục tiêu bài toán"))
    s.append(tcap("Thông tin tổng quan về tập dữ liệu"))
    s.append(table([["Hạng mục", "Mô tả"],
                    ["Tên tập dữ liệu", "IBM HR Analytics Employee Attrition &amp; Performance"],
                    ["Nguồn", "Kaggle – pavansubhasht/ibm-hr-analytics-attrition-dataset"],
                    ["Cấu trúc file", "Một file CSV duy nhất: WA_Fn-UseC_-HR-Employee-Attrition.csv; mỗi dòng là một nhân viên"],
                    ["Số quan sát / thuộc tính", f"{vn(R['n_rows'], 0)} dòng × {R['n_cols']} cột (26 cột số nguyên, 9 cột văn bản)"],
                    ["Biến mục tiêu", f"Attrition (Yes = nghỉ việc, No = ở lại): {R['attr_yes']} Yes, {vn(R['attr_no'], 0)} No"],
                    ["Bản chất dữ liệu", "Dữ liệu mô phỏng do các nhà khoa học dữ liệu của IBM tạo ra (không phải dữ liệu thực của một doanh nghiệp)"],
                    ["Mục tiêu bài toán", "Tìm các yếu tố liên quan đến nghỉ việc và đề xuất giải pháp giữ chân nhân sự"]],
                   [4.2 * cm, 12.2 * cm]))
    s.append(H2("2.2 Cấu trúc thuộc tính"))
    s.append(P("35 thuộc tính được chia thành các nhóm nghiệp vụ để thuận tiện cho việc đặt giả thuyết:"))
    s.append(tcap("Nhóm thuộc tính theo ý nghĩa nghiệp vụ"))
    s.append(table([["Nhóm", "Số cột", "Thuộc tính"],
                    ["Nhân khẩu học", "6", "Age, Gender, MaritalStatus, Education, EducationField, DistanceFromHome"],
                    ["Công việc", "7", "Department, JobRole, JobLevel, BusinessTravel, OverTime, JobInvolvement, PerformanceRating"],
                    ["Lương – phúc lợi", "6", "MonthlyIncome, DailyRate, HourlyRate, MonthlyRate, PercentSalaryHike, StockOptionLevel"],
                    ["Mức độ hài lòng", "4", "EnvironmentSatisfaction, JobSatisfaction, RelationshipSatisfaction, WorkLifeBalance"],
                    ["Thâm niên – phát triển", "7", "TotalWorkingYears, NumCompaniesWorked, YearsAtCompany, YearsInCurrentRole, YearsSinceLastPromotion, YearsWithCurrManager, TrainingTimesLastYear"],
                    ["Định danh / hằng số", "4", "EmployeeNumber, EmployeeCount, StandardHours, Over18"],
                    ["Biến mục tiêu", "1", "Attrition"]],
                   [3.8 * cm, 1.5 * cm, 11.1 * cm]))
    s.append(P("Về bản chất, các biến thang điểm (Education, các biến *Satisfaction, JobInvolvement, JobLevel, PerformanceRating, StockOptionLevel, WorkLifeBalance) "
               "được lưu dạng số nguyên nhưng là <b>biến thứ bậc</b>; BusinessTravel là biến phân loại có thứ tự; Department, EducationField, JobRole, MaritalStatus là "
               "biến phân loại danh nghĩa; Attrition, OverTime, Gender là biến nhị phân."))
    s.append(H2("2.3 Kiểm tra hiện trạng dữ liệu"))
    s.append(tcap("Kết quả rà soát hiện trạng dữ liệu"))
    s.append(table([["Nội dung kiểm tra", "Phương pháp", "Kết quả", "Kết luận"],
                    ["Kích thước và kiểu dữ liệu", "df.shape, df.dtypes", "1.470 × 35; 26 int64, 9 chuỗi", "Kiểu dữ liệu phù hợp, không có cột bị đọc sai kiểu"],
                    ["Giá trị khuyết (NaN)", "df.isna().sum()", f"{R['n_missing_total']} ô khuyết (0% ở mọi cột)", "Không cần điền giá trị thiếu"],
                    ["Khuyết thiếu ẩn", "Tìm '', '?', 'NA', 'null',... và giá trị âm", f"{R['hidden_missing_total']} giá trị; không có số âm", "Không có khuyết thiếu ẩn"],
                    ["Tính nhất quán giữa các file", "Chỉ có 1 file; kiểm tra khóa chính EmployeeNumber", "Duy nhất, không rỗng (1–2068)", "Không có phép gộp bảng nên không có rủi ro lệch khóa ngoại"],
                    ["Dòng trùng lặp", "df.duplicated()", f"{R['dup_full']} (kể cả khi bỏ EmployeeNumber: {R['dup_wo_id']})", "Không có trùng lặp"],
                    ["Cột hằng số", "df.nunique() == 1", "EmployeeCount = 1; StandardHours = 80; Over18 = 'Y'", "Loại bỏ ở Giai đoạn 2"],
                    ["Biến mục tiêu", "value_counts()", f"Yes {pct(R['attr_rate'])}, No {pct(100 - R['attr_rate'])}", "Mất cân bằng lớp, cần chọn thước đo phù hợp"]],
                   [3.4 * cm, 4.2 * cm, 4.2 * cm, 4.6 * cm]))
    s.append(P("Dù không phát hiện lỗi, các kết quả \"không có\" ở trên vẫn được ghi nhận kèm bằng chứng tính toán để báo cáo đầy đủ chứ không bỏ qua bước kiểm tra."))
    s.append(H2("2.4 Phân phối biến mục tiêu"))
    s.append(fig("fig01_attrition_distribution.png", "Phân phối biến mục tiêu Attrition (số lượng và tỷ lệ).", width=14))
    s += insight(f"{vn(R['attr_no'], 0)} nhân viên ở lại ({pct(100 - R['attr_rate'])}) so với {R['attr_yes']} nhân viên nghỉ việc ({pct(R['attr_rate'])}); tỷ lệ {vn(R['imbalance_ratio'])} : 1.",
                 "Dữ liệu mất cân bằng ở mức vừa phải. Một mô hình \"đoán tất cả ở lại\" đạt accuracy khoảng 83,9% nhưng không phát hiện được ai nghỉ việc, nên accuracy là thước đo gây hiểu lầm.",
                 "Các nhóm sẽ được so sánh với mức nền 16,1%; khi xây mô hình cần chia train/test có phân tầng và đánh giá bằng ROC-AUC, PR-AUC, recall, precision. "
                 "Chỉ có 237 ca nghỉ việc nên nhiều nhóm con sẽ có cỡ mẫu nhỏ, cần đọc kèm n.")
    s.append(PageBreak())

    # --------------------------------------------------------------- 3. Stage 2
    s.append(H1("3. GIAI ĐOẠN 2 – TIỀN XỬ LÝ VÀ LÀM SẠCH DỮ LIỆU"))
    s.append(P("Nguyên tắc xuyên suốt: mỗi vấn đề đều có <b>minh chứng</b> (bảng, biểu đồ, phép tính) và mỗi quyết định xử lý đều có <b>lý do</b>."))
    s.append(H2("3.1 Dữ liệu trùng lặp"))
    s.append(P("df.duplicated() cho 0 dòng trùng hoàn toàn. Kiểm tra lại sau khi bỏ cột EmployeeNumber (vì hai bản ghi có thể trùng mọi thông tin khác nhưng khác mã): "
               "kết quả cũng là 0. Vì vậy không xóa dòng nào."))
    s.append(H2("3.2 Cột hằng số và cột định danh"))
    s.append(tcap("Các cột bị loại bỏ (phát hiện bằng nunique)"))
    s.append(table([["Cột", "Số giá trị khác nhau", "Giá trị", "Quyết định", "Lý do"],
                    ["EmployeeCount", "1", "1", "Loại bỏ", "Hằng số, không phân biệt được nhân viên"],
                    ["StandardHours", "1", "80", "Loại bỏ", "Hằng số"],
                    ["Over18", "1", "'Y'", "Loại bỏ", "Hằng số (mọi nhân viên đều trên 18 tuổi)"],
                    ["EmployeeNumber", "1.470", "1–2068, duy nhất", "Loại khỏi phân tích", "Mã định danh, không có ý nghĩa dự báo; đưa vào mô hình chỉ gây nhiễu"]],
                   [3.2 * cm, 2.4 * cm, 2.6 * cm, 2.8 * cm, 5.4 * cm]))
    s.append(P(f"Sau bước này, dữ liệu còn {R['n_cols_clean']} cột (30 biến đầu vào và biến mục tiêu Attrition)."))
    s.append(H2("3.3 Định dạng, miền giá trị và tính hợp lý logic"))
    lv = R["logic_violations"]
    s.append(tcap("Kiểm tra định dạng, miền giá trị và logic"))
    s.append(table([["Kiểm tra", "Kết quả"],
                    ["Chuỗi có khoảng trắng thừa hoặc trùng do khác hoa/thường", "0 trường hợp ở cả 8 cột văn bản còn lại"],
                    ["Biến thứ bậc nằm ngoài thang cho phép", "0 trường hợp (Education, JobLevel: 1–5; StockOptionLevel: 0–3; các biến còn lại: 1–4)"],
                    ["Khoảng giá trị hợp lý của biến số", "Age 18–60; MonthlyIncome 1.009–19.999; DistanceFromHome 1–29; PercentSalaryHike 11–25; không có giá trị bất hợp lý"],
                    ["YearsAtCompany &gt; TotalWorkingYears", f"{lv['YearsAtCompany > TotalWorkingYears']} dòng vi phạm"],
                    ["YearsInCurrentRole, YearsSinceLastPromotion, YearsWithCurrManager &gt; YearsAtCompany", "0 dòng vi phạm (cả ba)"],
                    ["Tuổi bắt đầu đi làm (Age − TotalWorkingYears) &lt; 15", f"{lv['Tuổi bắt đầu đi làm < 15 (Age - TotalWorkingYears)']} dòng vi phạm"]],
                   [7.6 * cm, 8.8 * cm]))
    s.append(P("Lưu ý: PerformanceRating chỉ nhận hai giá trị (3 và 4) dù thang là 1–4, nên gần như không phân biệt được nhân viên; kiểm định về sau xác nhận nó không liên quan "
               "đến nghỉ việc (V ≈ 0,003). Các cột chuỗi được chuyển sang kiểu category và biến mục tiêu được mã hóa thành cờ nhị phân AttritionFlag (1 = nghỉ việc)."))

    s.append(H2("3.4 Giá trị ngoại lệ (outliers)"))
    s.append(P("Hai phương pháp được dùng để đối chiếu: <b>IQR</b> (ngoại lệ nếu nằm ngoài [Q1 − 1,5·IQR ; Q3 + 1,5·IQR]) và <b>Z-score</b> (|z| &gt; 3). "
               "IQR không giả định phân phối chuẩn nên phù hợp với dữ liệu lệch phải của bài toán; Z-score dùng để đối chiếu."))
    o = OUTL[OUTL["n_IQR"] > 0]
    rows = [["Biến", "Min", "Max", "Skew", "Ngưỡng trên IQR", "Số outlier IQR (%)", "Số |z| &gt; 3"]]
    for _, r in o.iterrows():
        rows.append([r["bien"], vn(r["min"], 0), vn(r["max"], 0), vn(r["skew"], 2), vn(r["bien_tren"], 1),
                     f"{int(r['n_IQR'])} ({pct(r['%_IQR'])})", str(int(r["n_Z>3"]))])
    s.append(tcap(f"Outlier theo IQR và Z-score ({len(o)} biến có outlier)"))
    s.append(table(rows, [4.4 * cm, 1.6 * cm, 1.7 * cm, 1.5 * cm, 2.5 * cm, 2.9 * cm, 1.8 * cm]))
    s.append(P("Sáu biến còn lại (Age, DailyRate, HourlyRate, MonthlyRate, DistanceFromHome, PercentSalaryHike) không có outlier theo IQR."))
    s.append(fig("fig02_boxplot_outliers.png", "Boxplot của 8 biến có giá trị ngoại lệ theo IQR (chấm đỏ = outlier)."))
    io = R["income_outlier"]
    s += insight(f"MonthlyIncome có {io['n']} outlier (7,8%, ngưỡng trên {vn(io['upper_fence'], 0)}) nhưng Z-score &gt; 3 cho 0 trường hợp; YearsSinceLastPromotion có 107 outlier IQR "
                 "và 42 theo Z-score. TrainingTimesLastYear bị gắn cờ 238 dòng dù giá trị chỉ từ 0 đến 6.",
                 "Các biến thu nhập và thâm niên có đuôi phải dài (skew 1,0–2,0). Đuôi dài làm độ lệch chuẩn phình to nên Z-score kém nhạy hơn IQR trên dữ liệu lệch. "
                 "Với TrainingTimesLastYear, IQR rất hẹp (2–3 lần) nên các giá trị 0, 5, 6 bị gắn cờ dù hoàn toàn hợp lệ: đây là hạn chế của IQR với biến đếm rời rạc.",
                 "Phát hiện bằng công cụ thống kê mới chỉ là bước đầu; cần kiểm chứng bằng ý nghĩa nghiệp vụ trước khi quyết định xóa hay giữ (xem bên dưới).")
    s.append(P("Kiểm chứng: outlier là lỗi hay giá trị thật?", "H3"))
    s += bullets([
        f"<b>MonthlyIncome:</b> {io['n']} outlier đều thuộc JobLevel 4–5 ({pct(io['pct_joblevel45'], 0)}): 39,5% JobLevel 4 và 60,5% JobLevel 5; theo chức danh là Manager (64,9%) "
        "và Research Director (35,1%). Đây là lương của cấp quản lý, hoàn toàn hợp lý.",
        f"<b>Hệ quả nếu xóa:</b> tỷ lệ nghỉ việc của nhóm outlier lương chỉ {pct(io['attr_rate_outlier'])} so với {pct(io['attr_rate_rest'])} ở phần còn lại. Xóa họ sẽ loại đúng "
        "nhóm có xu hướng ở lại và làm tăng giả tạo mức nghỉ việc của toàn bộ dữ liệu.",
        "<b>YearsAtCompany:</b> các outlier (&gt; 18 năm) có TotalWorkingYears trung vị 24 năm so với 10 năm của toàn bộ, tức thâm niên cao đi kèm tổng số năm đi làm cao, "
        "nhất quán và đã qua các kiểm tra logic ở mục 3.3.",
        "<b>Các biến đếm</b> (YearsSinceLastPromotion, NumCompaniesWorked, TrainingTimesLastYear): giá trị lớn là hợp lệ và có thể chính là tín hiệu nghỉ việc.",
    ])
    s.append(P("Xử lý độ lệch bằng log1p", "H3"))
    s.append(fig("fig03_skew_transform.png", "Phân phối MonthlyIncome trước và sau log1p, và phân phối YearsSinceLastPromotion.", max_h=6.5))
    sk = "; ".join(f"{d['bien']} {vn(d['skew_truoc'], 2)} → {vn(d['skew_sau_log1p'], 2)}" for d in R["skew_cmp"])
    s += insight(f"Skewness trước → sau log1p: {sk}.",
                 "log1p đưa 4/5 biến về gần đối xứng (|skew| &lt; 0,7). Với TotalWorkingYears phép biến đổi hơi \"quá tay\" (skew chuyển sang −0,62) nhưng vẫn giảm độ lệch tuyệt đối. "
                 "YearsSinceLastPromotion chỉ giảm còn 0,72 vì dữ liệu dồn nhiều ở giá trị 0, log không kéo giãn được phần này.",
                 "Biến đổi log giữ nguyên toàn bộ quan sát (không mất dữ liệu như khi xóa outlier) và phù hợp với mô hình tuyến tính. Phần kiểm định phi tham số và mô tả "
                 "ở Giai đoạn 3 dùng thang đo gốc để dễ diễn giải.")
    s.append(tcap("Quyết định xử lý outlier và lý do"))
    s.append(table([["Biến", "Quyết định", "Lý do"],
                    ["MonthlyIncome", "Giữ lại; log1p cho mô hình", "Outlier thuộc cấp quản lý (JobLevel 4–5), là lương thật; xóa làm mất nhóm chỉ nghỉ 4,4% và gây thiên lệch"],
                    ["YearsAtCompany, TotalWorkingYears", "Giữ lại; log1p", "Thâm niên cao hợp lệ về logic; là nhóm nhân viên lâu năm có thật"],
                    ["YearsSinceLastPromotion, NumCompaniesWorked", "Giữ lại; log1p", "Biến đếm lệch phải; giá trị lớn có thể là tín hiệu nghỉ việc"],
                    ["YearsInCurrentRole, YearsWithCurrManager", "Giữ nguyên (skew &lt; 1)", "Ít outlier (21 và 14 dòng), độ lệch chấp nhận được"],
                    ["TrainingTimesLastYear", "Giữ nguyên", "Biến đếm nhỏ (0–6); \"outlier\" chỉ là hệ quả của IQR hẹp"]],
                   [4.6 * cm, 3.8 * cm, 8 * cm]))
    s.append(P("<b>Vì sao không xóa hay cắt (winsorize)?</b> Dữ liệu chỉ có 1.470 dòng và mọi outlier đều có giải thích nghiệp vụ. Xóa làm giảm cỡ mẫu và gây thiên lệch; "
               "cắt giá trị làm méo thông tin của nhóm lương cao. IQR và Z-score chỉ là công cụ phát hiện, còn quyết định phải dựa trên ý nghĩa thực tế. "
               "<b>Vì sao log1p mà không phải log?</b> Vì nhiều biến có giá trị 0 (log(0) không xác định)."))

    s.append(H2("3.5 Mã hóa (encoding)"))
    s.append(tcap("Phương án mã hóa theo từng nhóm biến"))
    s.append(table([["Nhóm biến", "Biến", "Phương pháp", "Lý do chọn"],
                    ["Nhị phân", "Attrition, OverTime, Gender", "Ánh xạ 0/1 (Yes = 1; Male = 1)", "Chỉ có hai trạng thái, không cần mã hóa phức tạp hơn"],
                    ["Phân loại có thứ tự", "BusinessTravel", "Ordinal: Non-Travel = 0 &lt; Travel_Rarely = 1 &lt; Travel_Frequently = 2", "Có thứ tự tự nhiên; one-hot làm mất thông tin thứ tự và tăng số chiều"],
                    ["Thang điểm (thứ bậc)", "Education, *Satisfaction, JobInvolvement, JobLevel, StockOptionLevel, WorkLifeBalance, PerformanceRating", "Giữ nguyên số nguyên", "Đã có thứ tự và khoảng cách xấp xỉ đều; one-hot thêm hàng chục cột mà không thêm thông tin"],
                    ["Danh nghĩa", "Department, EducationField, JobRole, MaritalStatus", "One-hot, drop_first = True", "Không có thứ tự nên mã số 0,1,2 tạo quan hệ thứ bậc giả; drop_first tránh đa cộng tuyến hoàn hảo"]],
                   [2.8 * cm, 4.4 * cm, 4.2 * cm, 5 * cm]))
    s.append(P(f"Kết quả: ma trận {vn(R['model_shape'][0], 0)} dòng × {R['model_shape'][1]} cột (43 đặc trưng và 1 cột mục tiêu), không còn giá trị khuyết, toàn bộ là số. "
               "Department vẫn được mã hóa để lưu đầy đủ dữ liệu, nhưng <b>bị loại khỏi mô hình</b> ở mục 4.13 vì JobRole lồng trong Department (bằng chứng VIF)."))
    s.append(H2("3.6 Chuẩn hóa (scaling)"))
    rows = [["Biến", "Trung bình (đổi %)", "Độ lệch chuẩn (đổi %)", "Trung vị (đổi %)", "IQR (đổi %)"]]
    for d in R["scaler_stability"]:
        rows.append([d["bien"], vn(d["mean_doi_%"]), vn(d["std_doi_%"]), vn(d["median_doi_%"]), vn(d["IQR_doi_%"])])
    s.append(tcap("Mức thay đổi của tham số thang đo khi có so với không có outlier"))
    s.append(table(rows, [4.6 * cm, 3 * cm, 3.2 * cm, 2.8 * cm, 2.8 * cm]))
    s.append(P("Bảng trên là minh chứng cho lựa chọn <b>RobustScaler</b> (trung vị và IQR) thay vì StandardScaler (trung bình và độ lệch chuẩn): khi loại outlier, trung bình thay đổi "
               "18–47% còn trung vị chỉ 0–6%; độ rộng IQR cũng thay đổi ít hơn độ lệch chuẩn ở cả ba biến, dù mức chênh không đồng đều. Vì ta giữ các outlier hợp lệ, thang đo "
               "nên là loại ít bị đuôi dữ liệu chi phối. <b>Lưu ý trung thực:</b> tỷ lệ giá trị nằm trong [−1; 1] sau chuẩn hóa của hai phương pháp khá gần nhau (82–85%), "
               "nên chênh lệch kết quả mô hình dự kiến nhỏ; RobustScaler được chọn vì tính ổn định chứ không vì cho kết quả vượt trội."))
    s.append(P("<b>Phạm vi áp dụng:</b> chỉ chuẩn hóa 14 biến liên tục/đếm (sau log1p với 5 biến lệch); biến nhị phân, one-hot và thang điểm giữ nguyên. Bộ chuẩn hóa chỉ được "
               "fit trên tập huấn luyện (đặt trong Pipeline) để tránh rò rỉ dữ liệu. Phần kiểm định và mô tả ở Giai đoạn 3 dùng thang đo gốc."))
    s.append(PageBreak())

    # --------------------------------------------------------------- 4. Stage 3
    s.append(H1("4. GIAI ĐOẠN 3 – PHÂN TÍCH VÀ TRỰC QUAN HÓA"))
    s.append(H2("4.1 Hệ giả thuyết và phương pháp kiểm định"))
    s.append(P("Các giả thuyết được nêu <b>trước</b> khi xem số liệu chi tiết, dựa trên kiến thức quản trị nhân sự. Mỗi giả thuyết được trình bày theo <b>khung kiểm định 5 bước</b> "
               "(cặp H₀/H₁ → dữ liệu và giả định → chọn kiểm định → tính toán → quy tắc kết luận) rồi đối chiếu với số liệu để xác nhận hoặc bác bỏ."))
    s.append(tcap("Hệ giả thuyết nghiên cứu"))
    s.append(table([["Mã", "Giả thuyết (H₁)", "Biến liên quan"],
                    ["H1", "Nhân viên làm thêm giờ có tỷ lệ nghỉ việc cao hơn", "OverTime"],
                    ["H2", "Thu nhập thấp làm tăng nghỉ việc (kiểm tra yếu tố nhiễu là cấp bậc)", "MonthlyIncome, JobLevel"],
                    ["H3", "Nhân viên trẻ và ít thâm niên nghỉ việc nhiều hơn", "Age, YearsAtCompany, TotalWorkingYears"],
                    ["H4", "Lâu chưa được thăng chức thì dễ nghỉ việc hơn", "YearsSinceLastPromotion"],
                    ["H5", "Mức hài lòng/gắn kết thấp làm tăng nghỉ việc", "JobSatisfaction, EnvironmentSatisfaction, WorkLifeBalance, JobInvolvement"],
                    ["H6", "Có quyền chọn cổ phiếu giúp giữ chân nhân viên", "StockOptionLevel"],
                    ["H7", "Đi công tác thường xuyên, độc thân và ở xa công ty làm tăng nghỉ việc", "BusinessTravel, MaritalStatus, DistanceFromHome"],
                    ["H8", "Tỷ lệ nghỉ việc khác nhau giữa các vị trí và phòng ban", "JobRole, Department"],
                    ["H0*", "(Đối chứng) Giới tính không liên quan đến nghỉ việc", "Gender"]],
                   [1.3 * cm, 8.6 * cm, 6.5 * cm]))
    s += bullets([
        "Biến phân loại và thang điểm: kiểm định <b>Chi-square</b> độc lập, độ mạnh bằng <b>Cramér's V</b>.",
        "Biến số: kiểm định <b>Mann–Whitney U</b> hai phía (phi tham số, vì các biến lệch và không chuẩn), độ mạnh bằng hệ số <b>rank-biserial |r|</b>.",
        "Đa kiểm định: 30 biến được kiểm định đồng thời nên dùng <b>hiệu chỉnh Bonferroni</b> (p × 30, α = 0,05) làm kết luận chính và <b>FDR Benjamini–Hochberg</b> làm phân tích độ nhạy.",
        "Yếu tố nhiễu: kiểm định <b>Cochran–Mantel–Haenszel (CMH)</b> tính odds ratio trong từng tầng (hôn nhân, cấp bậc) rồi gộp lại; kèm kiểm định <b>Breslow–Day</b> xem OR có đồng nhất giữa các tầng.",
        "Ý nghĩa thống kê không đồng nghĩa ý nghĩa thực tế: luôn đọc p kèm effect size và tỷ lệ phần trăm; effect size nhỏ ≈ 0,1, vừa ≈ 0,3, lớn ≈ 0,5.",
    ])

    s.append(H2("4.2 Sàng lọc toàn bộ 30 biến"))
    top = SCREEN.sort_values("effect", ascending=False).head(12).reset_index(drop=True)
    rows = [["Hạng", "Biến", "Kiểm định", "Effect size", "p (Bonferroni)", "p (FDR)", "Kết luận"]]
    for i, r in top.iterrows():
        rows.append([str(i + 1), r["variable"], r["test"], vn(r["effect"], 3), sci(r["p_bonferroni"]), sci(r["p_fdr"]),
                     "Có ý nghĩa" if r["significant"] else "Không"])
    s.append(tcap("12 biến có độ mạnh liên hệ lớn nhất với Attrition"))
    s.append(table(rows, [1.2 * cm, 4.2 * cm, 3 * cm, 2 * cm, 2.4 * cm, 2.1 * cm, 1.9 * cm]))
    s.append(fig("fig04_effect_ranking.png", "Xếp hạng độ mạnh liên hệ của 30 biến với Attrition (đỏ = có ý nghĩa sau Bonferroni).", width=13, max_h=12.5))
    nonsig = ", ".join(SCREEN.loc[~SCREEN["significant"], "variable"])
    s += insight(f"{R['n_significant']}/30 biến có ý nghĩa sau Bonferroni và {R['n_significant_fdr']}/30 theo FDR. Dẫn đầu: TotalWorkingYears (0,312), MonthlyIncome (0,311), "
                 f"YearsAtCompany (0,298), YearsInCurrentRole, YearsWithCurrManager, Age, rồi OverTime (0,246) và JobRole (0,242). Không có ý nghĩa sau Bonferroni "
                 f"({30 - R['n_significant']} biến): {nonsig}. Bốn biến chỉ có ý nghĩa với FDR: {', '.join(R['only_fdr'])}.",
                 "Sáu biến đứng đầu thực chất cùng đo một chiều là <b>thâm niên/cấp bậc</b> (các biến Years* và thu nhập tương quan 0,7–0,9) nên không phải 6 yếu tố độc lập. "
                 "Trong các yếu tố có thể can thiệp, OverTime mạnh nhất. Mọi effect size đều ở mức nhỏ đến vừa (tối đa 0,31): không biến đơn lẻ nào giải thích được nghỉ việc. "
                 "Các biến Rate (DailyRate, HourlyRate, MonthlyRate) và PerformanceRating gần như không mang thông tin.",
                 "Ưu tiên nguồn lực vào các yếu tố vừa mạnh vừa tác động được (làm thêm giờ, vị trí, lộ trình lên cấp). Kết luận cho bốn biến chỉ qua FDR là bằng chứng yếu. "
                 "Lưu ý: Cramér's V và |r| không hoàn toàn so sánh trực tiếp được; riêng EducationField có tần số kỳ vọng nhỏ nhất 4,4 (&lt; 5) nên Chi-square của biến này kém tin cậy.")

    # ---- H1
    s.append(H2("4.3 H1 – Làm thêm giờ (OverTime)"))
    s += five_steps("tỷ lệ nghỉ việc độc lập với việc làm thêm giờ.",
                    "tỷ lệ nghỉ việc khác nhau giữa nhóm làm thêm giờ và không làm thêm giờ (kỳ vọng: nhóm làm thêm giờ cao hơn).",
                    "OverTime và Attrition đều nhị phân → bảng chéo 2×2; mọi tần số kỳ vọng ≥ 5 nên dùng được Chi-square.",
                    "Chi-square độc lập (hai phía) + Cramér's V; odds ratio và risk ratio kèm KTC 95%; CMH để loại trừ nhiễu do hôn nhân, cấp bậc.")
    s.append(fig("fig05_overtime.png", "Tỷ lệ nghỉ việc theo OverTime (trái) và theo OverTime trong từng nhóm hôn nhân (phải).", max_h=7))
    ox = rates["OverTime_x_Marital"]

    def oxr(m, o):
        return pct(ox[f"('{m}', '{o}')"]["rate"])
    s += insight(f"OverTime = Yes: {pct(rates['OverTime']['Yes']['rate'])} nghỉ việc ({rates['OverTime']['Yes']['left']}/{rates['OverTime']['Yes']['n']}); "
                 f"No: {pct(rates['OverTime']['No']['rate'])} ({rates['OverTime']['No']['left']}/{vn(rates['OverTime']['No']['n'], 0)}). χ² = {vn(H1r['chi2'])}, p = {sci(H1r['p'])}, "
                 f"Cramér's V = {vn(H1r['V'], 3)}; odds ratio = {vn(H1r['OR'], 2)} (KTC 95%: {vn(H1r['OR_lo'], 2)}–{vn(H1r['OR_hi'], 2)}); risk ratio = {vn(H1r['RR'], 2)}. "
                 f"Theo hôn nhân: Single {oxr('Single', 'No')} → {oxr('Single', 'Yes')}; Married {oxr('Married', 'No')} → {oxr('Married', 'Yes')}; "
                 f"Divorced {oxr('Divorced', 'No')} → {oxr('Divorced', 'Yes')}.",
                 f"<b>H1 được ủng hộ mạnh.</b> Làm thêm giờ đi kèm tỷ lệ nghỉ việc cao gấp khoảng {vn(H1r['RR'], 1)} lần (risk ratio; odds ratio {vn(H1r['OR'], 2)} là tỷ số odds, "
                 "không phải tỷ số xác suất). Nhóm độc thân làm thêm giờ (131 người) có nguy cơ cao nhất: cứ hai người thì có một người nghỉ.",
                 "Làm thêm giờ vừa là yếu tố mạnh nhất vừa là đòn bẩy quản lý trực tiếp. Dữ liệu chỉ cho thấy tương quan: làm thêm giờ có thể gây kiệt sức, hoặc chỉ là dấu hiệu "
                 "của vị trí quá tải; cần thử nghiệm giảm giờ làm thêm để xác nhận.")
    s.append(P("H1b – Kiểm tra yếu tố nhiễu bằng Cochran–Mantel–Haenszel", "H3"))
    s.append(tcap("Kiểm định CMH cho OverTime, phân tầng theo hôn nhân và cấp bậc"))
    s.append(table([["Phân tầng theo", "Số tầng", "OR gộp (Mantel–Haenszel)", "KTC 95%", "p CMH", "p Breslow–Day"],
                    ["(Không phân tầng – OR thô)", "–", vn(H1r["OR"], 2), f"{vn(H1r['OR_lo'], 2)} – {vn(H1r['OR_hi'], 2)}", sci(H1r["p"]), "–"],
                    ["MaritalStatus", str(cmh_ms["n_strata"]), vn(cmh_ms["OR_pooled"], 2), f"{vn(cmh_ms['OR_lo'], 2)} – {vn(cmh_ms['OR_hi'], 2)}", sci(cmh_ms["p_cmh"]), vn(cmh_ms["p_breslow_day"], 3)],
                    ["JobLevel", str(cmh_jl["n_strata"]), vn(cmh_jl["OR_pooled"], 2), f"{vn(cmh_jl['OR_lo'], 2)} – {vn(cmh_jl['OR_hi'], 2)}", sci(cmh_jl["p_cmh"]), vn(cmh_jl["p_breslow_day"], 3)]],
                   [4.4 * cm, 1.6 * cm, 3.2 * cm, 2.6 * cm, 2.2 * cm, 2.4 * cm]))
    s.append(P(f"OR không giảm mà còn tăng nhẹ khi phân tầng ({vn(H1r['OR'], 2)} → {vn(cmh_ms['OR_pooled'], 2)} và {vn(cmh_jl['OR_pooled'], 2)}), nên liên hệ giữa làm thêm giờ và nghỉ việc "
               f"<b>không phải do</b> hôn nhân hay cấp bậc gây ra. Breslow–Day p = {vn(cmh_ms['p_breslow_day'], 2)} và {vn(cmh_jl['p_breslow_day'], 2)}: chưa có bằng chứng OR khác nhau giữa các tầng, "
               "tức là làm thêm giờ làm tăng odds nghỉ việc khoảng 4 lần <b>ở mọi nhóm</b>. Tỷ lệ 49,6% ở nhóm độc thân làm thêm giờ là do hai yếu tố cộng lại."))

    # ---- H2
    s.append(H2("4.4 H2 – Thu nhập (MonthlyIncome) và yếu tố nhiễu cấp bậc"))
    s += five_steps("phân phối thu nhập của nhóm nghỉ việc và nhóm ở lại như nhau, cả trên toàn bộ dữ liệu lẫn trong từng JobLevel.",
                    "nhóm nghỉ việc có thu nhập khác (kỳ vọng: thấp hơn) nhóm ở lại.",
                    "MonthlyIncome lệch phải (skew 1,37), không chuẩn → kiểm định phi tham số. JobLevel là yếu tố nhiễu tiềm năng (tương quan 0,92 với thu nhập) → cần phân tầng.",
                    "Mann–Whitney U hai phía + |r| trên toàn bộ dữ liệu; Mann–Whitney U lặp lại trong từng JobLevel (kiểm soát cấp bậc).",
                    STD_RULE + " Với phân tầng theo JobLevel dùng mức 0,05 chưa hiệu chỉnh và ghi rõ cỡ mẫu từng tầng.")
    s.append(fig("fig06_income.png", "Thu nhập theo Attrition (trái), tỷ lệ nghỉ việc theo tứ phân vị thu nhập (giữa) và theo JobLevel (phải).", max_h=6.5))
    H2r = R["H2"]
    iq, jl = rates["IncomeQuartile"], rates["JobLevel"]
    s += insight(f"Thu nhập trung vị: nhóm nghỉ {vn(H2r['median_yes'], 0)} so với {vn(H2r['median_no'], 0)} (thấp hơn 38%); Mann–Whitney p = {sci(H2r['p'])}, |r| = {vn(H2r['r'], 3)}. "
                 f"Theo tứ phân vị: Q1 {pct(iq['Q1 (thấp)']['rate'])} (n = {iq['Q1 (thấp)']['n']}), Q2 {pct(iq['Q2']['rate'])}, Q3 {pct(iq['Q3']['rate'])}, Q4 {pct(iq['Q4 (cao)']['rate'])}. "
                 f"Theo cấp bậc: JobLevel 1 {pct(jl['1']['rate'])} (n = {jl['1']['n']}), 2 {pct(jl['2']['rate'])}, 3 {pct(jl['3']['rate'])}, 4 {pct(jl['4']['rate'])}, 5 {pct(jl['5']['rate'])}.",
                 "Nhìn tổng thể, H2 được ủng hộ: người nghỉ việc có thu nhập thấp hơn rõ rệt. Nhưng rủi ro tập trung ở tứ phân vị thấp nhất (gấp khoảng 1,8 lần mức chung) còn Q2–Q4 "
                 "chênh nhau ít, tức không có quan hệ \"càng cao càng ít nghỉ\" đều đặn. JobLevel 1 chiếm phần lớn nhóm thu nhập thấp và có tỷ lệ nghỉ cao gấp khoảng 2,7 lần JobLevel 2.",
                 "Thu nhập thấp phần lớn là biểu hiện của vị trí đầu vào. Cần kiểm tra yếu tố nhiễu bằng cách so sánh thu nhập trong cùng cấp bậc (bảng và hình dưới).")
    rows = [["JobLevel", "n", "Số người nghỉ", "Thu nhập trung vị (nghỉ)", "Thu nhập trung vị (ở lại)", "p (Mann–Whitney)", "Kết luận"]]
    for d in H2r["strat"]:
        rows.append([str(d["JobLevel"]), str(d["n"]), str(d["n_nghi"]), vn(d["TV_thu_nhap_nghi"], 0), vn(d["TV_thu_nhap_o_lai"], 0), sci(d["p_MWU"]),
                     "Có ý nghĩa" if d["p_MWU"] < 0.05 else "Không"])
    s.append(tcap("So sánh thu nhập giữa người nghỉ và người ở lại trong từng JobLevel (mức 0,05, chưa hiệu chỉnh)"))
    s.append(table(rows, [1.9 * cm, 1.2 * cm, 2.0 * cm, 3.0 * cm, 3.0 * cm, 2.8 * cm, 2.5 * cm]))
    s.append(fig("fig06b_income_by_joblevel.png", "Thu nhập tháng theo từng cấp bậc, tách người nghỉ và người ở lại (số trên hộp = trung vị; p = Mann–Whitney trong từng cấp).", max_h=7.5))
    s += insight("Trung vị trong cùng cấp: JobLevel 2 – 5.346 so với 5.334; JobLevel 3 – 9.887 so với 9.982; JobLevel 5 – 19.545 so với 19.200 (không có ý nghĩa). "
                 "Chỉ JobLevel 1 (2.437 so với 2.719, thấp hơn khoảng 10%, p &lt; 0,001) và JobLevel 4 (13.194 so với 16.307, p = 0,004 nhưng chỉ có 5 người nghỉ) có khác biệt.",
                 "Khi đặt cạnh nhau trong từng cấp, hộp của người nghỉ (đỏ) và người ở lại (xanh) gần như trùng nhau ở 3/5 cấp; khoảng cách thu nhập <b>giữa các cấp</b> lớn hơn nhiều "
                 "lần khoảng cách <b>trong cùng cấp</b>. Chênh lệch tổng thể (3.202 so với 5.204) chủ yếu là do người nghỉ việc tập trung ở JobLevel 1.",
                 "Giải pháp nên nhắm vào mặt bằng lương JobLevel 1 và lộ trình lên JobLevel 2, không tăng lương đại trà. Kết quả ở JobLevel 4 cần thận trọng vì cỡ mẫu quá nhỏ.")
    s.append(fig("fig07_scatter_income.png", "Quan hệ giữa thu nhập với tuổi (trái) và tổng số năm đi làm (phải), tô màu theo Attrition.", max_h=6.8))
    s += insight(f"Tương quan hạng Spearman với MonthlyIncome: Age = {vn(H2r['rho_age'], 2)}; TotalWorkingYears = {vn(H2r['rho_twy'], 2)}; JobLevel = {vn(H2r['rho_jl'], 2)}.",
                 "Các điểm đỏ (nghỉ việc) tụ ở góc dưới bên trái: tuổi trẻ, ít năm đi làm, thu nhập thấp; rất ít điểm đỏ ở vùng thu nhập trên 15.000. Thu nhập gần như là hàm "
                 "của cấp bậc và thâm niên.",
                 "Trẻ tuổi – ít thâm niên – lương thấp là một cụm nhân viên \"đầu sự nghiệp\" chứ không phải ba nguyên nhân độc lập; vì vậy cần mô hình đa biến (mục 4.13).")

    # ---- H3
    s.append(H2("4.5 H3 – Tuổi và thâm niên"))
    s += five_steps("tuổi, thâm niên tại công ty và tổng số năm đi làm có phân phối như nhau ở hai nhóm.",
                    "nhóm nghỉ việc khác (kỳ vọng: trẻ hơn, ít thâm niên hơn) nhóm ở lại.",
                    "Ba biến định lượng; YearsAtCompany, TotalWorkingYears lệch phải → kiểm định phi tham số. Chia nhóm tuổi/thâm niên để đọc tỷ lệ.",
                    "Mann–Whitney U hai phía + |r| cho từng biến; tỷ lệ nghỉ việc theo nhóm tuổi và nhóm thâm niên.")
    s.append(fig("fig08_age_tenure.png", "Phân phối và tỷ lệ nghỉ việc theo tuổi (hàng trên) và thâm niên tại công ty (hàng dưới).", max_h=10.5))
    ag, tn, H3r = rates["AgeGroup"], rates["TenureGroup"], R["H3"]
    s += insight(f"Tuổi trung vị: nghỉ 32, ở lại 36 (p = {sci(H3r['Age']['p'])}, |r| = {vn(H3r['Age']['r'], 3)}). Theo nhóm tuổi: 18–24 {pct(ag['18–24']['rate'])} (n = {ag['18–24']['n']}); "
                 f"25–34 {pct(ag['25–34']['rate'])} (n = {ag['25–34']['n']}); 35–44 {pct(ag['35–44']['rate'])}; 45–54 {pct(ag['45–54']['rate'])}; 55+ {pct(ag['55+']['rate'])} (n = {ag['55+']['n']}). "
                 f"Thâm niên: 0–1 năm {pct(tn['0–1']['rate'])} (n = {tn['0–1']['n']}); 2–3 năm {pct(tn['2–3']['rate'])}; 4–5 năm {pct(tn['4–5']['rate'])}; 6–10 năm {pct(tn['6–10']['rate'])}; "
                 f"trên 10 năm {pct(tn['>10']['rate'])}. YearsAtCompany trung vị: nghỉ 3, ở lại 6 (p = {sci(H3r['YearsAtCompany']['p'])}).",
                 f"<b>H3 được ủng hộ mạnh.</b> Rủi ro giảm dần theo tuổi và thâm niên, tập trung ở năm đầu: {pct(H3r['first_year'])} người có thâm niên ≤ 1 năm nghỉ việc, gấp khoảng "
                 f"2,7 lần nhóm còn lại ({pct(H3r['after_first_year'])}). Nhóm 55+ tăng nhẹ (có thể do nghỉ hưu, nhưng dữ liệu không phân biệt và n chỉ 69). Hai nhóm 18–34 tuổi chiếm "
                 "150/237 = 63,3% số người nghỉ trong khi chỉ chiếm 44,3% nhân viên.",
                 "Chính sách giữ chân nên tập trung vào 12 tháng đầu (onboarding, mentor, kiểm tra định kỳ) và nhóm dưới 35 tuổi. Nhóm 25–34 có tỷ lệ \"chỉ\" 20,2% nhưng đóng góp số "
                 "người nghỉ lớn nhất do quy mô lớn, nên khi chọn đối tượng cần xét cả tỷ lệ lẫn số tuyệt đối.")

    # ---- H4
    s.append(H2("4.6 H4 – Thời gian kể từ lần thăng chức gần nhất"))
    s += five_steps("số năm kể từ lần thăng chức gần nhất có phân phối như nhau ở hai nhóm.",
                    "nhóm nghỉ việc khác (kỳ vọng: lâu chưa thăng chức hơn) nhóm ở lại.",
                    "Biến đếm 0–15, rất lệch (skew 1,98), dồn ở giá trị 0; do ràng buộc YearsSinceLastPromotion ≤ YearsAtCompany, nhân viên mới luôn có giá trị 0.",
                    "Mann–Whitney U hai phía + |r|; tỷ lệ nghỉ việc theo nhóm số năm; đối chiếu YearsInCurrentRole, YearsWithCurrManager.",
                    STD_RULE + " Chú ý chiều của chênh lệch có khớp với kỳ vọng hay không.")
    s.append(fig("fig09_promotion.png", "Tỷ lệ nghỉ việc theo số năm kể từ lần thăng chức gần nhất (trái) và phân phối theo Attrition (phải).", max_h=6.8))
    pg = rates["PromoGroup"]
    coef_promo = COEF.loc["YearsSinceLastPromotion_log", "OR_per_1SD"]
    s += insight(f"Theo nhóm: 0 năm {pct(pg['0']['rate'])} (n = {pg['0']['n']}); 1–2 năm {pct(pg['1–2']['rate'])}; 3–5 năm {pct(pg['3–5']['rate'])}; 6–10 năm {pct(pg['6–10']['rate'])} "
                 f"(n = {pg['6–10']['n']}); trên 10 năm {pct(pg['>10']['rate'])} (n = {pg['>10']['n']}). Trung vị hai nhóm đều bằng 1 năm; p thô = {vn(R['H4']['p'], 3)}, "
                 f"p sau Bonferroni = 1,000, |r| = {vn(R['H4']['r'], 3)}.",
                 "<b>H4 không được ủng hộ.</b> Tỷ lệ nghỉ việc không tăng theo số năm chưa được thăng chức mà dao động không có quy luật (cao nhất ở nhóm 0 năm). Nguyên nhân: nhân viên "
                 "mới vào làm bắt buộc có giá trị 0, và nhóm này vốn nghỉ nhiều; nhóm \"0 năm\" vì vậy không có nghĩa là \"vừa được thăng chức\". Trong mô hình đa biến, "
                 f"log(YearsSinceLastPromotion) lại có hệ số dương (OR ≈ {vn(coef_promo, 2)} mỗi 1 độ lệch chuẩn) khi thâm niên được giữ cố định, gợi ý biến này bị thâm niên che khuất; "
                 "đây chỉ là gợi ý do đa cộng tuyến.",
                 "Không nên xây chính sách giữ chân chỉ dựa trên giả định \"lâu không thăng chức thì bỏ đi\" khi dữ liệu không chứng minh điều đó. Một giả thuyết hợp lý bị bác bỏ cũng là kết quả có giá trị.")

    # ---- H5
    s.append(H2("4.7 H5 – Mức độ hài lòng và gắn kết"))
    s += five_steps("tỷ lệ nghỉ việc độc lập với từng mức hài lòng/gắn kết (JobSatisfaction, EnvironmentSatisfaction, WorkLifeBalance, JobInvolvement).",
                    "tỷ lệ nghỉ việc khác nhau giữa các mức (kỳ vọng: mức thấp nghỉ nhiều hơn).",
                    "Bốn biến thứ bậc thang 1–4 → bảng chéo 4×2; tần số kỳ vọng đều ≥ 5.",
                    "Chi-square độc lập + Cramér's V cho từng biến; Spearman ρ để xem quan hệ có đơn điệu không.")
    s.append(fig("fig10_satisfaction.png", "Tỷ lệ nghỉ việc theo bốn biến thang điểm 1–4 (1 = thấp nhất, 4 = cao nhất).", max_h=10.5))
    H5r = R["H5"]

    def r4(v):
        return rates[v]
    s += insight(f"JobInvolvement: mức 1 {pct(r4('JobInvolvement')['1']['rate'])} (n = {r4('JobInvolvement')['1']['n']}), 2 {pct(r4('JobInvolvement')['2']['rate'])}, "
                 f"3 {pct(r4('JobInvolvement')['3']['rate'])}, 4 {pct(r4('JobInvolvement')['4']['rate'])} (V = {vn(H5r['JobInvolvement']['V'], 3)}). WorkLifeBalance: mức 1 "
                 f"{pct(r4('WorkLifeBalance')['1']['rate'])} (n = {r4('WorkLifeBalance')['1']['n']}), 2 {pct(r4('WorkLifeBalance')['2']['rate'])}, 3 {pct(r4('WorkLifeBalance')['3']['rate'])}, "
                 f"4 {pct(r4('WorkLifeBalance')['4']['rate'])}. EnvironmentSatisfaction: mức 1 {pct(r4('EnvironmentSatisfaction')['1']['rate'])} (n = {r4('EnvironmentSatisfaction')['1']['n']}), "
                 f"các mức còn lại 13,5–15,0%. JobSatisfaction: mức 1 {pct(r4('JobSatisfaction')['1']['rate'])}, mức 4 {pct(r4('JobSatisfaction')['4']['rate'])}. p sau Bonferroni: "
                 f"JobInvolvement {sci(sv('JobInvolvement', 'p_bonferroni'))}; EnvironmentSatisfaction {sci(sv('EnvironmentSatisfaction', 'p_bonferroni'))}; "
                 f"JobSatisfaction {sci(sv('JobSatisfaction', 'p_bonferroni'))}; WorkLifeBalance {sci(sv('WorkLifeBalance', 'p_bonferroni'))}.",
                 "<b>H5 được ủng hộ ở mức yếu đến vừa</b> (V = 0,11–0,14). JobInvolvement giảm dần đều (mức 1 cao gấp 3,7 lần mức 4); EnvironmentSatisfaction và WorkLifeBalance có dạng "
                 f"ngưỡng (chỉ mức 1 nổi bật). WorkLifeBalance không đơn điệu (mức 4 cao hơn mức 3) nên Spearman ρ gần 0 ({vn(H5r['WorkLifeBalance']['rho'], 2)}) dù Chi-square vẫn có ý nghĩa.",
                 "Nhóm tự đánh giá thấp nhất (mức 1) là đối tượng nên được HR chủ động trao đổi, nhưng các nhóm này nhỏ (80–289 người) nên khó làm tín hiệu cảnh báo duy nhất; "
                 "khảo sát hài lòng nên kết hợp với các tín hiệu khác như làm thêm giờ và thâm niên.")

    # ---- H6
    s.append(H2("4.8 H6 – Quyền chọn cổ phiếu (StockOptionLevel)"))
    s += five_steps("tỷ lệ nghỉ việc độc lập với mức quyền chọn cổ phiếu.",
                    "tỷ lệ nghỉ việc khác nhau giữa các mức (kỳ vọng: không có cổ phiếu nghỉ nhiều hơn).",
                    "StockOptionLevel thứ bậc 0–3 → bảng chéo 4×2. Nghi vấn nhiễu: toàn bộ nhân viên độc thân có mức 0.",
                    "Chi-square + Cramér's V; bảng chéo với MaritalStatus; CMH trong nhóm Married/Divorced.")
    s.append(fig("fig11_stock_option.png", "Tỷ lệ nghỉ việc theo StockOptionLevel (trái) và theo StockOptionLevel trong từng nhóm hôn nhân (phải).", max_h=6.8))
    so, H6r = rates["StockOptionLevel"], R["H6"]
    s += insight(f"StockOptionLevel 0: {pct(so['0']['rate'])} (n = {so['0']['n']}); mức 1: {pct(so['1']['rate'])} (n = {so['1']['n']}); mức 2: {pct(so['2']['rate'])} (n = {so['2']['n']}); "
                 f"mức 3: {pct(so['3']['rate'])} (n = {so['3']['n']}). χ² = {vn(H6r['chi2'])}, V = {vn(H6r['V'], 3)}. {pct(H6r['single_pct_lvl0'])} nhân viên mức 0 là độc thân và "
                 f"không nhân viên độc thân nào có mức ≥ 1. CMH trong nhóm Married + Divorced (1.000 người): không có cổ phiếu có OR = {vn(cmh_so['OR_pooled'], 2)} "
                 f"(KTC 95%: {vn(cmh_so['OR_lo'], 2)}–{vn(cmh_so['OR_hi'], 2)}; p = {sci(cmh_so['p_cmh'])}; Breslow–Day p = {vn(cmh_so['p_breslow_day'], 2)}).",
                 "<b>H6 được ủng hộ nhưng bị trộn với hôn nhân</b>: toàn bộ người độc thân (nhóm nghỉ cao nhất) rơi vào mức 0. Kiểm định CMH trên nhóm đã kết hôn/ly hôn cho thấy "
                 "liên hệ <b>vẫn tồn tại khi đã loại nhóm độc thân</b> (odds nghỉ việc cao gấp 2,4 lần), nên hiệu ứng không chỉ do hôn nhân. Mức 3 tăng lên 17,6% không đơn điệu, nhưng n nhỏ.",
                 "Với nhân viên độc thân thì dữ liệu không trả lời được (không ai có cổ phiếu), nên đề xuất thí điểm cổ phiếu/thưởng dài hạn cho nhóm này phải có nhóm đối chứng. "
                 "Việc không nhân viên độc thân nào có cổ phiếu cũng là dấu hiệu cấu trúc nhân tạo của dữ liệu mô phỏng.")

    # ---- H7
    s.append(H2("4.9 H7 – Công tác, hôn nhân và khoảng cách đi làm"))
    s += five_steps("tỷ lệ nghỉ việc độc lập với mức đi công tác và tình trạng hôn nhân; khoảng cách đi làm có phân phối như nhau ở hai nhóm.",
                    "có khác biệt (kỳ vọng: công tác thường xuyên, độc thân, ở xa thì nghỉ nhiều hơn).",
                    "BusinessTravel (3 mức), MaritalStatus (3 nhóm) là biến phân loại; DistanceFromHome là biến số 1–29 km, không chuẩn.",
                    "Chi-square + Cramér's V cho hai biến phân loại; Mann–Whitney U hai phía + |r| cho khoảng cách.",
                    STD_RULE + " So thêm với FDR vì khoảng cách nằm sát ngưỡng.")
    s.append(fig("fig12_travel_marital_distance.png", "Tỷ lệ nghỉ việc theo mức độ đi công tác, tình trạng hôn nhân và khoảng cách từ nhà đến công ty.", max_h=6.5))
    bt, ms, dg, H7r = rates["BusinessTravel"], rates["MaritalStatus"], rates["DistanceGroup"], R["H7"]
    seg = SEG.set_index("phan_khuc")
    stf = seg.loc["Single & Travel_Frequently"]
    s += insight(f"BusinessTravel: Non-Travel {pct(bt['Non-Travel']['rate'])} (n = {bt['Non-Travel']['n']}), Travel_Rarely {pct(bt['Travel_Rarely']['rate'])}, Travel_Frequently "
                 f"{pct(bt['Travel_Frequently']['rate'])} (n = {bt['Travel_Frequently']['n']}); V = {vn(H7r['BusinessTravel']['V'], 3)}. MaritalStatus: Single {pct(ms['Single']['rate'])} "
                 f"(n = {ms['Single']['n']}), Married {pct(ms['Married']['rate'])}, Divorced {pct(ms['Divorced']['rate'])}; V = {vn(H7r['MaritalStatus']['V'], 3)}. Khoảng cách: "
                 f"1–5 km {pct(dg['1–5 km']['rate'])}, 6–10 km {pct(dg['6–10 km']['rate'])}, 11–20 km {pct(dg['11–20 km']['rate'])}, 21–29 km {pct(dg['21–29 km']['rate'])}; "
                 f"p thô = {vn(H7r['DistanceFromHome']['p'], 4)}, p Bonferroni = {vn(sv('DistanceFromHome', 'p_bonferroni'), 3)}, p FDR = {vn(sv('DistanceFromHome', 'p_fdr'), 4)}. "
                 f"Độc thân + công tác thường xuyên: {pct(stf['ty_le_nghi_%'])} ({int(stf['so_nghi'])}/{int(stf['n'])} người).",
                 "Công tác và hôn nhân được ủng hộ rõ: tỷ lệ tăng đều theo mức công tác (Travel_Frequently gấp 3,1 lần Non-Travel) và người độc thân nghỉ gấp khoảng 2 lần người đã kết "
                 "hôn hoặc ly hôn; riêng nhóm độc thân chiếm 120/237 = 50,6% số người nghỉ. Hai yếu tố cộng hưởng: độc thân và công tác thường xuyên nghỉ 38,5%. Khoảng cách có xu "
                 "hướng tăng bậc thang sau 10 km nhưng chỉ có ý nghĩa với FDR, không qua Bonferroni.",
                 "Có thể giảm nguy cơ bằng cách hạn chế điều động công tác thường xuyên với nhân viên đã có tín hiệu rủi ro (độc thân, làm thêm giờ) hoặc bù đắp bằng chế độ phù hợp. "
                 "Kết luận về khoảng cách phụ thuộc cách hiệu chỉnh nên chỉ là bằng chứng yếu, cần thêm dữ liệu trước khi hành động.")

    # ---- H8
    s.append(H2("4.10 H8 – Vị trí công việc và phòng ban"))
    s += five_steps("tỷ lệ nghỉ việc như nhau giữa các vị trí công việc (và giữa các phòng ban).",
                    "tỷ lệ nghỉ việc khác nhau giữa các vị trí (và phòng ban).",
                    "JobRole 9 nhóm → bảng 9×2; Department 3 nhóm → bảng 3×2; JobRole lồng trong Department.",
                    "Chi-square + Cramér's V cho từng biến.")
    s.append(fig("fig13_jobrole_department.png", "Tỷ lệ nghỉ việc theo vị trí công việc (trái) và phòng ban (phải).", max_h=7.5))
    jr = rates["JobRole"]
    ov = R["attr_rate"]
    rows = [["Hạng", "Vị trí", "Tỷ lệ nghỉ", "Nghỉ / tổng", "So với mức chung"]]
    for i, (k, v) in enumerate(sorted(jr.items(), key=lambda kv: -kv[1]["rate"])):
        lift = v["rate"] / ov
        cmp_ = f"gấp {vn(lift, 1)} lần" if lift >= 1.2 else ("xấp xỉ mức chung" if lift >= 0.9 else "thấp hơn")
        rows.append([str(i + 1), k, pct(v["rate"]), f"{v['left']} / {v['n']}", cmp_])
    s.append(tcap("Xếp hạng đầy đủ 9 vị trí công việc theo tỷ lệ nghỉ việc"))
    s.append(table(rows, [1.3 * cm, 5.2 * cm, 2.6 * cm, 3 * cm, 4.3 * cm]))
    dp, H8r = rates["Department"], R["H8"]
    s += insight(f"V(JobRole) = {vn(H8r['JobRole']['V'], 3)}, p = {sci(H8r['JobRole']['p'])}. Phòng ban: Sales {pct(dp['Sales']['rate'])}, Human Resources {pct(dp['Human Resources']['rate'])}, "
                 f"R&amp;D {pct(dp['Research & Development']['rate'])}; V = {vn(H8r['Department']['V'], 3)}, p thô = {vn(H8r['Department']['p'], 4)}, p Bonferroni = "
                 f"{vn(sv('Department', 'p_bonferroni'), 3)}, p FDR = {vn(sv('Department', 'p_fdr'), 4)}.",
                 "<b>H8 được ủng hộ ở cấp vị trí, không vững ở cấp phòng ban.</b> Có hai nhóm rõ rệt: 5 vị trí tuyến đầu/chuyên viên (16–40%) và 4 vị trí quản lý/chuyên gia cấp cao "
                 "(2,5–7%); chênh lệch cao nhất – thấp nhất khoảng 16 lần. Ba vị trí đông người Laboratory Technician, Sales Executive, Research Scientist chiếm 166/237 = 70% số người nghỉ. "
                 "Phòng ban che giấu sự không đồng nhất: phòng Sales có cả Sales Representative (39,8%) và Manager.",
                 "Chính sách nên thiết kế <b>theo vị trí</b>: can thiệp sâu cho Sales Representative (áp lực chỉ tiêu, cơ chế thưởng), can thiệp diện rộng cho ba vị trí đông người. "
                 "Human Resources (52 người) và Sales Representative (83 người) có cỡ mẫu nhỏ, nên các thứ hạng sát nhau chỉ mang tính tham khảo.")

    # ---- H0*
    s.append(H2("4.11 H0* – Đối chứng: giới tính"))
    s += five_steps("tỷ lệ nghỉ việc độc lập với giới tính.",
                    "tỷ lệ nghỉ việc khác nhau giữa nam và nữ.",
                    "Gender nhị phân → bảng 2×2. Đây là <b>biến đối chứng</b>: không có lý do nghiệp vụ mạnh để giới tính ảnh hưởng, nên kỳ vọng <i>không bác bỏ</i> H₀.",
                    "Chi-square độc lập + Cramér's V; odds ratio kèm KTC 95%.",
                    "Kỳ vọng p ≥ 0,05; đối chiếu với p sau Bonferroni. Nếu bác bỏ, cần nghi ngờ quy trình (ví dụ \"câu\" p-value).")
    g, G0 = rates["Gender"], R["H0_gender"]
    s.append(tcap("Tỷ lệ nghỉ việc theo giới tính"))
    s.append(table([["Giới tính", "Số nhân viên", "Số người nghỉ", "Tỷ lệ nghỉ"],
                    ["Nữ", str(g["Female"]["n"]), str(g["Female"]["left"]), pct(g["Female"]["rate"])],
                    ["Nam", str(g["Male"]["n"]), str(g["Male"]["left"]), pct(g["Male"]["rate"])]],
                   [4 * cm, 4 * cm, 4 * cm, 4.4 * cm]))
    s += insight(f"Chênh lệch 2,2 điểm phần trăm; χ² = {vn(G0['chi2'], 2)}, p = {vn(G0['p'], 3)} (sau Bonferroni = 1,000), Cramér's V = {vn(G0['V'], 3)}; odds ratio nam so với nữ = "
                 f"{vn(G0['OR'], 2)} (KTC 95%: {vn(G0['OR_lo'], 2)}–{vn(G0['OR_hi'], 2)}).",
                 "Khoảng tin cậy của odds ratio chứa 1 nên <b>không bác bỏ H₀</b>, đúng như kỳ vọng của biến đối chứng.",
                 "Kết quả giúp tăng độ tin cậy cho quy trình: các kiểm định không \"tìm ra\" liên hệ ở nơi không có lý do để có. Không cần chương trình giữ chân riêng theo giới tính.")

    # ---- heatmap
    s.append(H2("4.12 Ma trận tương quan"))
    s.append(fig("fig14_correlation_heatmap.png", "Ma trận tương quan Spearman giữa các biến số, biến thang điểm, OverTime và AttritionFlag.", width=16, max_h=13.5))
    ct = R["corr_top"]
    pairs = "; ".join(f"{p['a']}–{p['b']} ({vn(p['r'], 2)})" for p in R["corr_pairs"])
    s += insight(f"Tương quan với Attrition: OverTime +{vn(ct['OverTime'], 2)}; TotalWorkingYears {vn(ct['TotalWorkingYears'], 2)}; MonthlyIncome {vn(ct['MonthlyIncome'], 2)}; "
                 f"YearsAtCompany {vn(ct['YearsAtCompany'], 2)}; JobLevel {vn(ct['JobLevel'], 2)}; StockOptionLevel {vn(ct['StockOptionLevel'], 2)}; Age {vn(ct['Age'], 2)}. "
                 f"Các cặp |ρ| ≥ 0,7: {pairs}.",
                 "Mọi tương quan đơn lẻ với nghỉ việc đều yếu (|ρ| ≤ 0,25), phù hợp với effect size nhỏ đến vừa ở mục 4.2. Các biến thâm niên và cấp bậc tạo thành một khối tương quan "
                 "cao, mang thông tin trùng lặp. Ba cột DailyRate, HourlyRate, MonthlyRate gần như độc lập với mọi biến; PerformanceRating chỉ tương quan 0,63 với PercentSalaryHike.",
                 "Khi đưa vào mô hình tuyến tính cần kiểm tra đa cộng tuyến (VIF, mục 4.13) và không đọc riêng hệ số của các biến trong cùng khối. Heatmap chỉ đo quan hệ đơn điệu "
                 "từng cặp nên không thay thế được phân tích đa biến.")

    # ---- model
    s.append(H2("4.13 Mô hình tham chiếu: hồi quy logistic"))
    s.append(P("Các kiểm định ở trên xét từng biến riêng lẻ nên có thể bị nhiễu bởi các biến khác. Hồi quy logistic dùng đồng thời nhiều biến cho biết biến nào còn liên hệ với nghỉ "
               "việc khi các biến khác được giữ cố định. Đây là mô hình để <b>diễn giải</b>, không phải mô hình triển khai."))
    s.append(P("Bước 1 – Kiểm tra đa cộng tuyến (VIF)", "H3"))
    va, vb = list(R["vif"]["top_all"].items()), list(R["vif"]["top_nodept"].items())
    rows = [["#", "Đủ 43 đặc trưng", "VIF", "Sau khi loại Department", "VIF"]]
    for i in range(5):
        rows.append([str(i + 1), va[i][0], vn(va[i][1], 1), vb[i][0], vn(vb[i][1], 1)])
    s.append(tcap("5 đặc trưng có VIF cao nhất trước và sau khi loại Department (VIF &gt; 10 là đa cộng tuyến nghiêm trọng)"))
    s.append(table(rows, [0.8 * cm, 5.4 * cm, 1.6 * cm, 6.2 * cm, 2.4 * cm]))
    s.append(P(f"Các cột Department_* có VIF ≈ 44 vì JobRole <b>lồng trong</b> Department (mỗi vị trí chỉ thuộc một phòng ban, riêng Manager có ở cả 3), nên Department gần như được suy ra "
               f"hoàn toàn từ JobRole. Mô hình <b>loại Department</b> và giữ JobRole (chi tiết hơn, liên hệ mạnh hơn: V = 0,24 so với 0,09). VIF lớn nhất giảm từ {vn(R['vif']['max_all'], 1)} "
               f"xuống {vn(R['vif']['max_nodept'], 1)}. VIF còn cao ở EducationField_* là hệ quả của nhóm tham chiếu quá nhỏ (drop_first bỏ nhóm \"Human Resources\" chỉ có 27 người), "
               "không phải hai thông tin trùng nhau; cặp JobLevel – MonthlyIncome_log (≈ 9) là cặp đã biết nên không đọc riêng hệ số của từng biến trong cặp này."))
    s.append(P("Bước 2 – Huấn luyện và đánh giá", "H3"))
    s.append(P(f"Thiết lập: {M['n_features']} đặc trưng; chia train/test 80/20 có phân tầng (random_state = 42); RobustScaler fit trên tập train trong Pipeline; class_weight = 'balanced'; "
               "đánh giá bằng ROC-AUC, PR-AUC, recall, precision; độ ổn định đo bằng 5-fold CV lặp lại 10 lần. Để so sánh được các hệ số có đơn vị khác nhau (biến liên tục theo IQR, "
               "thang điểm theo 1 mức, nhị phân 0/1), hình dùng <b>hệ số chuẩn hóa</b> = hệ số × độ lệch chuẩn của đặc trưng."))
    s.append(fig("fig15_logreg.png", "15 hệ số chuẩn hóa lớn nhất (trái), đường cong ROC (giữa) và Precision–Recall (phải) trên tập test.", width=16.4, max_h=6))
    cm_ = M["cm"]
    top_c = COEF.head(8)
    coef_txt = "; ".join(f"{k} {vn(v, 2)}" for k, v in top_c["OR_per_1SD"].items())
    s += insight(f"ROC-AUC: {vn(M['test_auc'], 3)} trên test; {vn(M['cv_auc_mean'], 3)} ± {vn(M['cv_auc_std'], 3)} (5-fold CV trên train); {vn(M['rep_cv_auc_mean'], 3)} trung bình qua 10 lần "
                 f"lặp 5-fold CV, 95% số lần trong [{vn(M['rep_cv_auc_lo95'], 3)}; {vn(M['rep_cv_auc_hi95'], 3)}]. PR-AUC test {vn(M['test_pr_auc'], 3)} (mức nền 0,160). Ở ngưỡng 0,5: "
                 f"recall lớp nghỉ việc {vn(M['recall_leave'], 2)}, precision {vn(M['precision_leave'], 2)}, F1 {vn(M['f1_leave'], 2)}; ma trận nhầm lẫn [[{cm_[0][0]}, {cm_[0][1]}], "
                 f"[{cm_[1][0]}, {cm_[1][1]}]]; accuracy {pct(M['accuracy'] * 100)} (thấp hơn mức {pct(M['baseline_acc'])} của mô hình đoán toàn bộ \"ở lại\"). OR theo 1 độ lệch chuẩn của "
                 f"8 đặc trưng mạnh nhất: {coef_txt}.",
                 "Mô hình xếp hạng khá tốt (AUC ≈ 0,8); mức 0,79 trên test chỉ là dao động bình thường vì tập test chỉ có 47 ca nghỉ việc. Theo hệ số chuẩn hóa, ba yếu tố lớn nhất gần "
                 "như ngang nhau: OverTime, TotalWorkingYears (càng nhiều năm đi làm càng ít nghỉ) và JobLevel; tiếp theo là số công ty đã làm, thu nhập, đi công tác, hài lòng môi trường, "
                 "Laboratory Technician và độc thân. Trước khi chuẩn hóa, OverTime trông vượt trội chỉ vì là biến 0/1.",
                 "Các kết luận đơn biến không bị đảo ngược khi xét đồng thời nhiều biến, làm tăng độ tin cậy cho khuyến nghị. JobLevel dương và MonthlyIncome_log âm là hệ quả của "
                 "tương quan 0,92, không có nghĩa \"lên cấp làm tăng nghỉ việc\". Kết luận đúng: làm thêm giờ là yếu tố mạnh nhất trong các yếu tố <b>có thể can thiệp trực tiếp</b>.")
    s.append(P("Bước 3 – Dùng điểm rủi ro theo kiểu top-k", "H3"))
    rows = [["Top k%", "Số nhân viên được chọn", "Số người nghỉ bắt được", "Precision", "Recall", "Lift"]]
    for _, r in TOPK.iterrows():
        rows.append([f"{int(r['top_k_%'])}%", str(int(r["so_nv_duoc_chon"])), str(int(r["so_nghi_bat_duoc"])), vn(r["precision"], 2), vn(r["recall"], 2), vn(r["lift"], 2)])
    s.append(tcap("Hiệu quả khi chọn k% nhân viên có điểm rủi ro cao nhất (dự báo out-of-fold trên toàn bộ 1.470 nhân viên)"))
    s.append(table(rows, [2 * cm, 3.6 * cm, 3.6 * cm, 2.4 * cm, 2.4 * cm, 2.4 * cm]))
    s += insight(f"PR-AUC out-of-fold {vn(M['oof_pr_auc'], 3)}. Top 10% (147 người): precision {vn(tk.loc[10, 'precision'], 2)}, bao phủ {pct(tk.loc[10, 'recall'] * 100, 0)} số người nghỉ "
                 f"(lift {vn(tk.loc[10, 'lift'], 1)}). Top 20% (294 người): precision {vn(tk.loc[20, 'precision'], 2)}, bao phủ {pct(tk.loc[20, 'recall'] * 100, 0)} (lift {vn(tk.loc[20, 'lift'], 1)}).",
                 "Mỗi nhân viên được chấm điểm bởi mô hình không học trên chính họ, nên số liệu không bị lạc quan do khớp quá mức. Precision giảm dần khi k tăng: đánh đổi giữa độ phủ và "
                 "độ chính xác của danh sách.",
                 "Cách đọc top-k gắn trực tiếp với <b>nguồn lực có hạn</b> của HR: chọn k theo số buổi phỏng vấn giữ chân làm được, thay vì dùng một ngưỡng xác suất khó giải thích.")

    # ---- summary
    s.append(H2("4.14 Tổng hợp kết quả kiểm định giả thuyết"))
    interp = {"OverTime": "Ủng hộ mạnh; không bị nhiễu (CMH)", "MonthlyIncome": "Ủng hộ, chủ yếu qua cấp bậc", "Age": "Ủng hộ", "YearsAtCompany": "Ủng hộ",
              "TotalWorkingYears": "Ủng hộ", "YearsSinceLastPromotion": "Bác bỏ", "JobSatisfaction": "Ủng hộ (yếu)", "WorkLifeBalance": "Ủng hộ (yếu, không đơn điệu)",
              "EnvironmentSatisfaction": "Ủng hộ (yếu–vừa)", "JobInvolvement": "Ủng hộ (vừa)", "StockOptionLevel": "Ủng hộ; vẫn còn khi loại độc thân (CMH)",
              "BusinessTravel": "Ủng hộ", "MaritalStatus": "Ủng hộ", "DistanceFromHome": "Bằng chứng yếu (chỉ qua FDR)", "JobRole": "Ủng hộ mạnh",
              "Department": "Bằng chứng yếu (chỉ qua FDR); bị JobRole bao trọn", "Gender": "Đúng kỳ vọng: không liên quan"}
    rows = [["Giả thuyết", "Biến", "Kiểm định", "p (Bonferroni)", "p (FDR)", "Effect size", "Kết luận"]]
    for _, r in HYP.iterrows():
        rows.append([r["Giả thuyết"], r["Biến"], r["Kiểm định"], sci(float(r["p (Bonferroni)"])), sci(float(r["p (FDR)"])), vn(r["Effect size"], 3), interp[r["Biến"]]])
    s.append(tcap("Tổng hợp kiểm định giả thuyết (α = 0,05; Bonferroni với 30 kiểm định; FDR làm phân tích độ nhạy)"))
    s.append(table(rows, [1.6 * cm, 4.3 * cm, 2.4 * cm, 2.0 * cm, 1.9 * cm, 1.3 * cm, 2.9 * cm]))
    s.append(P("<b>Độ nhạy theo cách hiệu chỉnh:</b> mọi kết luận \"có ý nghĩa\" theo Bonferroni vẫn giữ nguyên với FDR. Ngược lại, FDR (ít khắt khe hơn) thêm 4 biến: DistanceFromHome, "
               "Department, EducationField, DailyRate. Các kết luận này phụ thuộc vào cách hiệu chỉnh nên được xếp là bằng chứng yếu."))
    s.append(PageBreak())

    # --------------------------------------------------------------- 5. Stage 4
    s.append(H1("5. GIAI ĐOẠN 4 – ĐÁNH GIÁ TÁC ĐỘNG VÀ KHUYẾN NGHỊ"))
    s.append(H2("5.1 Các phát hiện nổi bật nhất"))
    s += bullets([
        f"<b>Làm thêm giờ là yếu tố mạnh và rõ nhất:</b> {pct(rates['OverTime']['Yes']['rate'])} so với {pct(rates['OverTime']['No']['rate'])} (odds ratio {vn(H1r['OR'], 2)}); "
        "hiệu ứng không bị nhiễu bởi hôn nhân hay cấp bậc (OR gộp CMH ≈ 4,0); nhân viên độc thân làm thêm giờ nghỉ 49,6%.",
        "<b>Nhân viên trẻ và mới vào làm có nguy cơ cao nhất:</b> nhóm 18–24 tuổi 39,2%, thâm niên ≤ 1 năm 34,9%.",
        "<b>Thu nhập thấp phần lớn phản ánh cấp bậc đầu vào:</b> trong cùng cấp bậc, chênh lệch thu nhập không còn ý nghĩa ở 3/5 cấp (Hình 7).",
        "<b>Vị trí công việc phân hóa mạnh:</b> Sales Representative 39,8%, Laboratory Technician 23,9%, so với Research Director 2,5%; ba vị trí đông người chiếm 70% số người nghỉ.",
        "<b>Yếu tố bổ trợ:</b> độc thân (25,5%), đi công tác thường xuyên (24,9%; cộng với độc thân 38,5%), không có quyền chọn cổ phiếu (24,4%; vẫn gấp 2,4 lần về odds trong nhóm "
        "đã kết hôn/ly hôn), mức gắn kết thấp (JobInvolvement mức 1: 33,7%).",
        "<b>Không được ủng hộ:</b> thời gian kể từ lần thăng chức gần nhất, giới tính; khoảng cách đi làm và phòng ban chỉ là bằng chứng yếu.",
        f"<b>Đa biến:</b> hồi quy logistic (AUC ≈ {vn(M['rep_cv_auc_mean'], 2)}) xác nhận các kết luận trên; top 20% điểm rủi ro bao phủ khoảng 60% số người nghỉ.",
    ])
    s.append(H2("5.2 Phân khúc có rủi ro cao"))
    s.append(P(f"Để chuyển phát hiện thành hành động, các phân khúc được định lượng bằng tỷ lệ nghỉ việc, lift (so với mức chung {pct(ov)}) và tỷ trọng số người nghỉ mà phân khúc bao phủ. "
               "Các phân khúc có thể chồng lấn."))
    rows = [["Phân khúc", "n", "% nhân viên", "Tỷ lệ nghỉ", "Lift", "% người nghỉ được bao phủ"]]
    for _, r in SEG.iterrows():
        rows.append([r["phan_khuc"], str(int(r["n"])), vn(r["%_nhan_vien"]), pct(r["ty_le_nghi_%"]), vn(r["lift"], 2), vn(r["%_bao_phu_nguoi_nghi"])])
    s.append(tcap("Các phân khúc rủi ro (nhóm đối chứng ở dòng cuối)"))
    s.append(table(rows, [6.4 * cm, 1.4 * cm, 2 * cm, 2 * cm, 1.4 * cm, 3.2 * cm]))
    s.append(fig("fig16_risk_segments.png", "Tỷ lệ nghỉ việc và lift của các phân khúc rủi ro.", width=14, max_h=8.5))
    s += insight("OverTime = Yes: 28,3% nhân viên nhưng chiếm 53,6% số người nghỉ (lift 1,89). JobLevel 1 và OverTime: 10,6% nhân viên, chiếm 34,6% số người nghỉ, tỷ lệ 52,6%. "
                 "Thâm niên ≤ 1 năm và OverTime: tỷ lệ 55,1% (lift 3,42, cao nhất). Độc thân và công tác thường xuyên: 38,5% (lift 2,39). Nhóm đối chứng (không làm thêm giờ, không "
                 "độc thân): 48,6% nhân viên nhưng chỉ nghỉ 7,7% (lift 0,48).",
                 "Kết hợp các yếu tố làm rủi ro cộng hưởng: nhân viên mới hoặc cấp thấp cộng với làm thêm giờ có khoảng một nửa nghỉ việc, trong khi nhóm đối chứng chỉ khoảng 8%. "
                 "Chỉ riêng việc nhắm vào nhóm làm thêm giờ đã chạm tới hơn một nửa số người nghỉ.",
                 "Có thể ưu tiên nguồn lực HR theo phân khúc thay vì áp dụng đại trà, kết hợp với danh sách top-k ở mục 4.13. Lưu ý: các phân khúc được chọn sau khi đã xem dữ liệu nên tỷ lệ "
                 "có thể lạc quan (data snooping); cần xác nhận trên dữ liệu mới.")
    s.append(H2("5.3 Đề xuất giải pháp ứng dụng"))
    s.append(tcap("Giải pháp gắn với từng phát hiện"))
    s.append(table([["Phát hiện", "Giải pháp đề xuất", "Chỉ số theo dõi"],
                    ["Làm thêm giờ làm odds nghỉ việc tăng khoảng 4 lần, ở mọi nhóm", "Đặt trần giờ làm thêm theo tháng; rà soát phân bổ khối lượng, ưu tiên Laboratory Technician và Sales Representative; quy đổi giờ làm thêm thành nghỉ bù hoặc phụ cấp rõ ràng", "Tỷ lệ nhân viên OverTime; tỷ lệ nghỉ của nhóm OverTime"],
                    ["Nghỉ việc tập trung ở người trẻ và năm đầu", "Chương trình onboarding 12 tháng: mentor, mốc đánh giá tháng 3/6/12, lộ trình phát triển rõ ràng cho nhân viên dưới 25 tuổi", "Tỷ lệ giữ chân sau 12 tháng"],
                    ["Sales Representative, Laboratory Technician, HR có rủi ro cao", "Phỏng vấn giữ chân và phỏng vấn nghỉ việc tại các vị trí này; xem lại cơ chế thưởng, áp lực chỉ tiêu và lộ trình lên cấp", "Tỷ lệ nghỉ việc theo vị trí"],
                    ["Thu nhập thấp gắn với cấp bậc thấp", "Rà soát thang lương JobLevel 1 và lộ trình lên JobLevel 2 (nhóm nghỉ 26,3%) thay vì tăng lương đại trà", "Tỷ lệ nghỉ ở JobLevel 1; thời gian lên JobLevel 2"],
                    ["Độc thân, đi công tác nhiều, không có cổ phiếu", "Thí điểm phúc lợi giữ chân (cổ phiếu hoặc thưởng dài hạn) có nhóm đối chứng; giảm tần suất công tác với nhân viên có tín hiệu rủi ro", "Mức tham gia; tỷ lệ nghỉ của nhóm thí điểm so với đối chứng"],
                    ["Mức hài lòng và gắn kết thấp", "Khảo sát nhanh định kỳ (pulse survey) về WorkLifeBalance và JobInvolvement; HR chủ động trao đổi với nhân viên điểm thấp", "Điểm hài lòng trung bình; số nhân viên điểm 1"],
                    ["Cần ưu tiên nguồn lực", "Dùng điểm rủi ro chọn top 10–20% nhân viên cho phỏng vấn giữ chân (top 20% bao phủ khoảng 60% số người nghỉ); kết hợp phân khúc ở mục 5.2", "Precision/recall của danh sách top-k, cập nhật hằng quý"]],
                   [4.4 * cm, 7.6 * cm, 4.4 * cm]))
    s.append(P("<b>Lưu ý khi áp dụng:</b> các mối liên hệ là tương quan, chưa chứng minh nhân quả. Nên thí điểm có nhóm đối chứng (A/B) trước khi triển khai toàn công ty."))
    s.append(H2("5.4 Giới hạn của tập dữ liệu"))
    s += bullets([
        "<b>Dữ liệu mô phỏng:</b> do IBM tạo ra với mục đích minh họa, không phải dữ liệu thực nên không khái quát hóa trực tiếp ra thực tế.",
        "<b>Lát cắt thời điểm:</b> không có chiều thời gian (ngày nghỉ, lịch sử lương, thay đổi mức hài lòng) nên không kết luận được nhân quả và không dùng được phân tích sống sót.",
        "<b>Không có lý do nghỉ việc:</b> không phân biệt nghỉ tự nguyện, bị cho thôi việc hay nghỉ hưu.",
        "<b>Mất cân bằng lớp và cỡ mẫu nhỏ:</b> chỉ 237 ca nghỉ việc; nhiều nhóm con n nhỏ (Divorced có StockOptionLevel 0 chỉ 8 người; Sales Representative 83 người; JobLevel 4–5 chỉ 5 người nghỉ mỗi cấp).",
        "<b>Cấu trúc bất thường:</b> PerformanceRating chỉ có 2 giá trị; không nhân viên độc thân nào có StockOptionLevel ≥ 1 nên không tách được hoàn toàn hiệu ứng cổ phiếu và hôn nhân.",
        "<b>Đa cộng tuyến:</b> JobLevel–MonthlyIncome (0,92), YearsInCurrentRole–YearsAtCompany (0,85) khiến hệ số từng biến trong cặp kém ổn định.",
        "<b>Nhiều kiểm định:</b> Bonferroni khá bảo thủ; với FDR có 4 biến đổi kết luận, nên các kết luận đó chỉ là bằng chứng yếu.",
        "<b>Mô hình tham chiếu:</b> AUC dao động 0,78–0,89 giữa các lần chia dữ liệu; precision ở ngưỡng 0,5 khoảng 0,40 và ở top 20% khoảng 0,48, nên điểm rủi ro chỉ dùng để ưu tiên "
        "trao đổi, không để ra quyết định nhân sự ở mức cá nhân; chưa kiểm định trên dữ liệu ngoài.",
    ])
    s.append(H2("5.5 Hướng mở rộng"))
    s += bullets([
        "Thu thập dữ liệu theo thời gian (ngày vào, ngày nghỉ, lịch sử lương, điểm hài lòng định kỳ) để dùng phân tích sống sót (Kaplan–Meier, Cox).",
        "Thử mô hình phi tuyến (Random Forest, Gradient Boosting) kết hợp SHAP để giải thích; xử lý mất cân bằng bằng trọng số lớp, SMOTE hoặc tinh chỉnh ngưỡng; đánh giá bằng PR-AUC và recall tại top-k.",
        "Bổ sung dữ liệu về lý do nghỉ việc, đánh giá của quản lý và thị trường lao động để tách các nhóm nguyên nhân.",
        "Phân tích chi phí – lợi ích (chi phí thay thế nhân viên so với chi phí chương trình giữ chân) để chọn k tối ưu cho danh sách ưu tiên.",
        "Thiết kế thử nghiệm A/B cho các giải pháp đề xuất (trần giờ làm thêm, chương trình mentor).",
    ])
    s.append(PageBreak())

    # --------------------------------------------------------------- 6. Conclusion
    s.append(H1("6. KẾT LUẬN"))
    s.append(P("Từ 1.470 hồ sơ nhân viên sạch và nhất quán, báo cáo cho thấy nghỉ việc (16,1%) tập trung ở nhóm làm thêm giờ, nhân viên trẻ hoặc mới vào, ở cấp bậc đầu vào và ở một số vị trí "
               "cụ thể (Sales Representative, Laboratory Technician). Hiệu ứng của làm thêm giờ đứng vững sau khi kiểm soát hôn nhân và cấp bậc, cũng như trong mô hình đa biến. Nhiều giả "
               "thuyết hợp lý không được ủng hộ (thăng chức, giới tính), một số chỉ là bằng chứng yếu (phòng ban, khoảng cách), và một số kết quả đơn biến (thu nhập, cổ phiếu) bị trộn với "
               "cấp bậc và hôn nhân, nên cần diễn giải thận trọng. Các giải pháp tập trung vào những đòn bẩy vừa có bằng chứng vừa quản lý được: giảm làm thêm giờ, hỗ trợ năm đầu, lộ trình "
               "lên cấp, chính sách theo vị trí và danh sách ưu tiên top-k, với điều kiện thí điểm có đối chứng trước khi nhân rộng."))
    s.append(Spacer(1, 10))

    # --------------------------------------------------------------- Appendix
    s.append(H1("PHỤ LỤC"))
    s.append(H2("A. Mã nguồn và cấu trúc kho GitHub"))
    s.append(P(f"Đường dẫn kho GitHub (public): <b>{CFG.GITHUB_URL}</b>"))
    s.append(tcap("Cấu trúc kho mã nguồn"))
    s.append(table([["Tệp / thư mục", "Nội dung"],
                    ["HR_Attrition_Analysis.ipynb", "Notebook phân tích đầy đủ 4 giai đoạn, có chú thích từng khối lệnh; chạy được bằng Run all trên Colab"],
                    ["WA_Fn-UseC_-HR-Employee-Attrition.csv", "Dữ liệu gốc từ Kaggle"],
                    ["Bao_cao_HR_Attrition.pdf", "Báo cáo PDF chính thức (file này)"],
                    ["figures/", "17 hình dùng trong báo cáo (do notebook sinh ra)"],
                    ["outputs/", "Bảng kết quả: screening_tests.csv, hypothesis_summary.csv, outlier_table.csv, logreg_coefficients.csv, topk_risk.csv, risk_segments.csv, hr_attrition_model_ready.csv, results.json"],
                    ["generate_report.py, report_config.py, fonts/", "Script dựng báo cáo PDF từ figures/ và outputs/; file cấu hình thông tin nhóm; font DejaVu Sans hỗ trợ tiếng Việt"],
                    ["requirements.txt, README.md", "Thư viện cần cài và hướng dẫn chạy"]],
                   [5.6 * cm, 10.8 * cm]))
    s.append(H2("B. Hướng dẫn chạy lại"))
    s += bullets([
        "Mở notebook trên Google Colab (Runtime → Run all). Nếu file CSV nằm cùng thư mục, notebook đọc trực tiếp; nếu không, điền GITHUB_RAW_URL (link raw của file CSV trong kho) "
        "hoặc tải file lên khi được hỏi. Cố định random_state = 42 nên kết quả tái lập được.",
        "Dựng lại báo cáo: sửa thông tin nhóm trong report_config.py, đặt logo_truong.png và logo_aep.png cạnh script, rồi chạy <i>python generate_report.py</i> (cần reportlab, pandas, Pillow).",
    ])
    s.append(H2("C. Phân công thành viên"))
    rows = [["Họ và tên", "MSSV", "Nhiệm vụ"]] + [list(m) for m in CFG.MEMBERS]
    s.append(tcap("Phân công công việc"))
    s.append(table(rows, [6.4 * cm, 3.4 * cm, 6.6 * cm]))
    s.append(H2("D. Tài liệu và công cụ tham khảo"))
    s += bullets([
        "Tập dữ liệu: Kaggle – IBM HR Analytics Employee Attrition &amp; Performance (pavansubhasht), https://www.kaggle.com/datasets/pavansubhasht/ibm-hr-analytics-attrition-dataset",
        "Thư viện: pandas, NumPy, SciPy (chi2_contingency, mannwhitneyu, spearmanr), statsmodels (StratifiedTable – Cochran–Mantel–Haenszel, multipletests – FDR, "
        "variance_inflation_factor), scikit-learn (RobustScaler, LogisticRegression, Pipeline, RepeatedStratifiedKFold), Matplotlib, Seaborn, ReportLab.",
    ])
    return s


def main():
    out = os.path.join(HERE, CFG.OUTPUT_PDF)
    doc = ReportDoc(out)
    doc.multiBuild(build_story())
    print("Đã tạo:", out)


if __name__ == "__main__":
    main()
