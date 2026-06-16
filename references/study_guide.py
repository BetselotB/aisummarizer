from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.colors import HexColor, black, white
from reportlab.lib.units import mm
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    PageBreak, HRFlowable, KeepTogether
)
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_JUSTIFY

# Colors
DARK_BG   = HexColor("#1a1a2e")
ACCENT    = HexColor("#e94560")
BLUE      = HexColor("#0f3460")
LIGHT_BG  = HexColor("#f0f4ff")
CODE_BG   = HexColor("#1e1e2e")
CODE_TXT  = HexColor("#cdd6f4")
KEYWORD   = HexColor("#89b4fa")
HEADING_COLOR = HexColor("#0f3460")
SUB_COLOR = HexColor("#e94560")
GRAY      = HexColor("#555577")
YELLOW    = HexColor("#fffbe6")
YELLOW_BG = HexColor("#fff3b0")

W, H = A4

styles = getSampleStyleSheet()

def make_styles():
    s = {}

    s['cover_title'] = ParagraphStyle('cover_title',
        fontName='Helvetica-Bold', fontSize=32, textColor=white,
        spaceAfter=8, alignment=TA_CENTER, leading=40)

    s['cover_sub'] = ParagraphStyle('cover_sub',
        fontName='Helvetica', fontSize=14, textColor=HexColor("#ccddff"),
        spaceAfter=4, alignment=TA_CENTER)

    s['chapter'] = ParagraphStyle('chapter',
        fontName='Helvetica-Bold', fontSize=18, textColor=white,
        spaceBefore=4, spaceAfter=6, alignment=TA_LEFT,
        backColor=HEADING_COLOR, borderPad=8)

    s['section'] = ParagraphStyle('section',
        fontName='Helvetica-Bold', fontSize=13, textColor=ACCENT,
        spaceBefore=10, spaceAfter=4)

    s['subsection'] = ParagraphStyle('subsection',
        fontName='Helvetica-Bold', fontSize=11, textColor=HEADING_COLOR,
        spaceBefore=6, spaceAfter=3)

    s['body'] = ParagraphStyle('body',
        fontName='Helvetica', fontSize=9.5, textColor=HexColor("#222233"),
        spaceAfter=3, leading=14, alignment=TA_JUSTIFY)

    s['bullet'] = ParagraphStyle('bullet',
        fontName='Helvetica', fontSize=9.5, textColor=HexColor("#222233"),
        spaceAfter=2, leading=13, leftIndent=14,
        bulletIndent=4, bulletFontName='Helvetica', bulletFontSize=9)

    s['code'] = ParagraphStyle('code',
        fontName='Courier', fontSize=8.2, textColor=CODE_TXT,
        backColor=CODE_BG, spaceAfter=2, spaceBefore=2,
        leading=12, leftIndent=8, rightIndent=8,
        borderPad=6, borderWidth=0)

    s['code_label'] = ParagraphStyle('code_label',
        fontName='Helvetica-Bold', fontSize=8, textColor=HexColor("#888aaa"),
        spaceAfter=0, spaceBefore=6)

    s['note'] = ParagraphStyle('note',
        fontName='Helvetica-Oblique', fontSize=9, textColor=HexColor("#553300"),
        backColor=YELLOW, spaceAfter=4, leading=13,
        leftIndent=10, rightIndent=10, borderPad=5)

    s['key'] = ParagraphStyle('key',
        fontName='Helvetica-Bold', fontSize=9, textColor=HexColor("#000033"),
        backColor=HexColor("#dde8ff"), spaceAfter=4, leading=13,
        leftIndent=10, rightIndent=10, borderPad=5)

    s['toc_entry'] = ParagraphStyle('toc',
        fontName='Helvetica', fontSize=10, textColor=HEADING_COLOR,
        spaceAfter=3, leading=14)

    return s

S = make_styles()


def chapter_header(title):
    data = [[Paragraph(title, S['chapter'])]]
    t = Table(data, colWidths=[W - 40*mm])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), HEADING_COLOR),
        ('TOPPADDING', (0,0), (-1,-1), 8),
        ('BOTTOMPADDING', (0,0), (-1,-1), 8),
        ('LEFTPADDING', (0,0), (-1,-1), 12),
        ('RIGHTPADDING', (0,0), (-1,-1), 8),
        ('ROUNDEDCORNERS', [4,4,4,4]),
    ]))
    return t


def code_block(lines, label=None):
    items = []
    if label:
        items.append(Paragraph(label, S['code_label']))
    safe = lines.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
    # wrap each line
    parts = []
    for ln in safe.split('\n'):
        parts.append(ln if ln.strip() else ' ')
    full = '<br/>'.join(parts)
    items.append(Paragraph(full, S['code']))
    return items


def note_box(text):
    return Paragraph(f"💡 {text}", S['note'])


def key_box(text):
    return Paragraph(f"⚡ {text}", S['key'])


def bullet(text):
    return Paragraph(f"• {text}", S['bullet'])


def subbullet(text):
    return Paragraph(f"  ◦ {text}", S['bullet'])


def two_col_table(rows, header=None, col_widths=None):
    cw = col_widths or [60*mm, 110*mm]
    data = []
    if header:
        data.append([Paragraph(f"<b>{header[0]}</b>", S['body']),
                     Paragraph(f"<b>{header[1]}</b>", S['body'])])
    for r in rows:
        data.append([Paragraph(str(r[0]), S['body']),
                     Paragraph(str(r[1]), S['body'])])
    t = Table(data, colWidths=cw)
    style = [
        ('GRID', (0,0), (-1,-1), 0.4, HexColor("#aabbcc")),
        ('BACKGROUND', (0,0), (-1,0), HexColor("#dde8ff")),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('FONTSIZE', (0,0), (-1,-1), 8.5),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [white, LIGHT_BG]),
        ('TOPPADDING', (0,0), (-1,-1), 4),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
        ('LEFTPADDING', (0,0), (-1,-1), 6),
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
    ]
    if header:
        style.append(('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'))
    t.setStyle(TableStyle(style))
    return t


def build_pdf():
    doc = SimpleDocTemplate(
        "/mnt/user-data/outputs/Web_Programming_Final_Exam_Guide.pdf",
        pagesize=A4,
        leftMargin=18*mm, rightMargin=18*mm,
        topMargin=16*mm, bottomMargin=16*mm,
        title="Web Programming – Final Exam Study Guide"
    )

    story = []

    # ── COVER ──────────────────────────────────────────────────────────────────
    cover_data = [[
        Paragraph("WEB PROGRAMMING", S['cover_title']),
    ]]
    cover = Table(cover_data, colWidths=[W - 36*mm])
    cover.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), DARK_BG),
        ('TOPPADDING', (0,0), (-1,-1), 30),
        ('BOTTOMPADDING', (0,0), (-1,-1), 10),
        ('LEFTPADDING', (0,0), (-1,-1), 16),
    ]))
    story.append(cover)

    sub_data = [[
        Paragraph("Final Exam Study Guide", S['cover_sub']),
    ]]
    sub_tbl = Table(sub_data, colWidths=[W - 36*mm])
    sub_tbl.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), DARK_BG),
        ('TOPPADDING', (0,0), (-1,-1), 2),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
        ('LEFTPADDING', (0,0), (-1,-1), 16),
    ]))
    story.append(sub_tbl)

    sub_data2 = [[
        Paragraph("Chapters 1–4: Internet &amp; Web · HTML · CSS · JavaScript", S['cover_sub']),
    ]]
    sub_tbl2 = Table(sub_data2, colWidths=[W - 36*mm])
    sub_tbl2.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), BLUE),
        ('TOPPADDING', (0,0), (-1,-1), 8),
        ('BOTTOMPADDING', (0,0), (-1,-1), 14),
        ('LEFTPADDING', (0,0), (-1,-1), 16),
    ]))
    story.append(sub_tbl2)
    story.append(Spacer(1, 10*mm))

    focus_data = [[
        Paragraph("<b>🎯 Focus Areas</b>", ParagraphStyle('fh', fontName='Helvetica-Bold', fontSize=11, textColor=ACCENT)),
    ],[
        Paragraph("Heavy emphasis on JavaScript &amp; HTML examples  •  CSS selectors &amp; box model  •  Event handling  •  Form validation", S['body']),
    ]]
    ft = Table(focus_data, colWidths=[W - 36*mm])
    ft.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), HexColor("#f7f9ff")),
        ('BOX', (0,0), (-1,-1), 1.5, ACCENT),
        ('TOPPADDING', (0,0), (-1,-1), 6),
        ('BOTTOMPADDING', (0,0), (-1,-1), 6),
        ('LEFTPADDING', (0,0), (-1,-1), 10),
    ]))
    story.append(ft)
    story.append(PageBreak())

    # ══════════════════════════════════════════════════════════════════════════
    # CHAPTER 1 – Internet & WWW
    # ══════════════════════════════════════════════════════════════════════════
    story.append(chapter_header("Chapter 1 – The Internet & World Wide Web"))
    story.append(Spacer(1, 4))

    story.append(Paragraph("Key Concepts at a Glance", S['section']))
    rows = [
        ("Internet", "Global network of networks sharing data via common protocols. Started as ARPANET (1960s), commercialized 1995."),
        ("WWW", "Created by Tim Berners-Lee (1989, CERN). Collection of hyperlinked documents over the Internet."),
        ("HTTP", "Application-level protocol for transferring web content. Runs on TCP/IP."),
        ("DNS", "Converts domain names (www.google.com) → IP addresses (e.g. 74.125.45.100)."),
        ("Client/Server", "Browser (client) requests a page; web server sends HTML back."),
        ("Static page", "Fixed HTML content, same every load. Lower cost, harder to update."),
        ("Dynamic page", "Content generated server-side (PHP, ASP, JSP). Can connect to a database."),
        ("Web hosting", "Storing your site on a public web server so others can access it."),
        ("Domain registration", "Registering a unique name via ICANN-accredited registrars (e.g. GoDaddy)."),
    ]
    story.append(two_col_table(rows, header=["Term", "Definition"], col_widths=[45*mm, 125*mm]))
    story.append(Spacer(1, 4))

    story.append(Paragraph("DNS Resolution – How it Works", S['subsection']))
    steps = [
        "You type www.cisco.com in browser.",
        "Browser asks your ISP's DNS server.",
        "ISP DNS asks a Root DNS server → gets the authoritative DNS for .com.",
        "ISP DNS asks Cisco's DNS → gets IP 198.133.219.25.",
        "Browser sends HTTP request to that IP and downloads the page.",
    ]
    for i, s in enumerate(steps, 1):
        story.append(Paragraph(f"{i}. {s}", S['bullet']))

    story.append(Spacer(1, 3))
    story.append(Paragraph("URL Anatomy: &nbsp;<b>www.microsoft.com.</b>  →  root (.) → .com (TLD) → microsoft → www (host)", S['body']))
    story.append(Spacer(1, 4))

    story.append(Paragraph("Web Programming Triangle", S['subsection']))
    story.append(bullet("<b>Client-side (front-end):</b> HTML, CSS, JavaScript — run in the browser."))
    story.append(bullet("<b>Server-side (back-end):</b> PHP, ASP.NET, JSP — run on the server, converted to HTML before sending."))
    story.append(bullet("IIS (Microsoft) and Apache are popular web server software."))

    story.append(PageBreak())

    # ══════════════════════════════════════════════════════════════════════════
    # CHAPTER 2 – HTML
    # ══════════════════════════════════════════════════════════════════════════
    story.append(chapter_header("Chapter 2 – HTML Tags"))
    story.append(Spacer(1, 4))

    # Basic structure
    story.append(Paragraph("1 · Basic HTML Structure", S['section']))
    story.append(note_box("Every HTML document must follow this skeleton. The browser renders only what is inside &lt;body&gt;."))
    story.append(Spacer(1, 2))
    for p in code_block("""<!DOCTYPE html>
<html lang="en">
  <head>
    <meta charset="UTF-8">
    <title>Page Title</title>       <!-- shown in browser tab / bookmarks -->
  </head>
  <body>
    <h1>Hello World</h1>
    <p>First paragraph.</p>
  </body>
</html>""", "HTML Skeleton"):
        story.append(p)

    story.append(Spacer(1, 4))
    story.append(Paragraph("2 · Common Tags Quick Reference", S['section']))
    tag_rows = [
        ("<b>&lt;h1&gt; – &lt;h6&gt;</b>", "Headings, largest to smallest. Block elements."),
        ("<b>&lt;p&gt;</b>", "Paragraph. Block element. Cannot nest another &lt;p&gt; inside."),
        ("<b>&lt;br&gt;</b>", "Line break. Empty element (no closing tag needed)."),
        ("<b>&lt;hr&gt;</b>", "Horizontal rule — draws a dividing line."),
        ("<b>&lt;b&gt;</b>", "Bold text."),
        ("<b>&lt;i&gt;</b>", "Italic text."),
        ("<b>&lt;u&gt;</b>", "Underlined text."),
        ("<b>&lt;strike&gt;</b>", "Strikethrough text."),
        ("<b>&lt;sub&gt; / &lt;sup&gt;</b>", "Subscript / superscript. e.g. H&lt;sub&gt;2&lt;/sub&gt;O"),
        ("<b>&lt;big&gt; / &lt;small&gt;</b>", "One size larger / smaller than surrounding text."),
        ("<b>&lt;pre&gt;</b>", "Preformatted text — preserves spaces and line breaks (Courier font)."),
        ("<b>&lt;center&gt;</b>", "Centers content."),
        ("<b>&lt;bdo dir='rtl'&gt;</b>", "Bidirectional override — for right-to-left languages (Arabic, Hebrew)."),
        ("<b>&lt;em&gt; / &lt;strong&gt;</b>", "Emphasized / strong (bold-like) semantic text."),
        ("<b>&lt;abbr&gt; / &lt;acronym&gt;</b>", "Abbreviation / acronym with title tooltip."),
        ("<b>&lt;!-- comment --&gt;</b>", "HTML comment. Ignored by browser."),
    ]
    story.append(two_col_table(tag_rows, header=["Tag", "Purpose"], col_widths=[55*mm, 115*mm]))

    story.append(Spacer(1, 4))
    story.append(Paragraph("3 · Tag Attributes", S['section']))
    story.append(bullet("Attributes go inside the <b>opening</b> tag: &lt;tag attribute=\"value\"&gt;"))
    story.append(bullet("<b>bgcolor</b>, <b>text</b>, <b>alink</b>, <b>link</b>, <b>vlink</b> on &lt;body&gt; set page and link colors."))
    story.append(bullet("<b>lang</b> on &lt;html&gt; declares language: &lt;html lang=\"en\"&gt; or &lt;html lang=\"am\"&gt; for Amharic."))
    story.append(bullet('<b>align</b> on &lt;p&gt;, &lt;h1&gt;, etc.: left | center | right | justify'))

    for p in code_block("""<body bgcolor="yellow" text="#FF0000" alink="#00A000" link="#00FF00" vlink="#0000FF">
  <p align="center">Centered paragraph</p>
  <p align="justify">Justified paragraph with multiple lines of text.</p>
</body>""", "Body & Paragraph Attributes Example"):
        story.append(p)

    story.append(Spacer(1, 4))
    story.append(Paragraph("4 · Font Tag", S['section']))
    story.append(bullet("&lt;font size='1-7' color='red' face='Arial,Verdana'&gt; — size range 1 (smallest) to 7 (largest), default 3."))
    story.append(bullet("Relative sizes: &lt;font size='+2'&gt; or &lt;font size='-1'&gt;"))
    story.append(bullet("Always fallback fonts: face=\"Arial, Helvetica, sans-serif\""))

    for p in code_block("""<font size="5" color="#0000FF" face="Verdana, Arial">Blue Verdana text</font>
<font size="+2" color="red">Two sizes larger red text</font>
<basefont face="Arial" size="3" color="#000000">  <!-- sets page default font -->""", "Font Examples"):
        story.append(p)

    story.append(Spacer(1, 4))
    story.append(Paragraph("5 · Hyperlinks", S['section']))
    attr_rows = [
        ("<b>href</b>", "URL of destination page."),
        ("<b>target</b>", "_blank (new window), _self (same), _top, _parent"),
        ("<b>name</b>", "Creates a bookmark anchor: &lt;a name='top'&gt;"),
        ("<b>title</b>", "Tooltip shown on hover."),
        ("<b>accesskey</b>", "Keyboard shortcut (Alt+key) to activate link."),
    ]
    story.append(two_col_table(attr_rows, header=["Attribute", "Effect"], col_widths=[35*mm, 135*mm]))

    for p in code_block("""<!-- Link to external page, opens in new tab -->
<a href="http://www.google.com" target="_blank" title="Go to Google">Google</a>

<!-- Internal bookmark link -->
<a name="section2">Section 2 Title</a>   <!-- anchor -->
<a href="#section2">Jump to Section 2</a> <!-- link to it -->

<!-- Email link -->
<a href="mailto:info@example.com">Email Us</a>""", "Link Examples"):
        story.append(p)

    story.append(Spacer(1, 4))
    story.append(Paragraph("6 · Images", S['section']))
    for p in code_block("""<!-- Basic image -->
<img src="photo.jpg" alt="Description" width="200" height="150" />

<!-- With border and alignment -->
<img src="logo.png" alt="Logo" border="2" align="right" hspace="10" vspace="5" title="Our Logo" />""", "Image Tag Examples"):
        story.append(p)
    story.append(bullet("<b>src</b> = path/URL to image.   <b>alt</b> = fallback text (required).   <b>hspace/vspace</b> = horizontal/vertical spacing around image."))

    story.append(Spacer(1, 4))
    story.append(Paragraph("7 · Image Maps", S['section']))
    story.append(note_box("Image maps let different regions of one image link to different pages. Shape options: rect, circle, poly."))
    for p in code_block("""<img src="map.gif" usemap="#shapes" alt="Shapes" />
<map id="shapes" name="shapes">
  <area shape="rect"   coords="29,27,173,171" href="square.html"   alt="Square">
  <area shape="circle" coords="295,175,81"    href="circle.html"   alt="Circle">
  <area shape="poly"   coords="177,231,269,369,84,369" href="tri.html" alt="Triangle">
</map>""", "Image Map Example"):
        story.append(p)

    story.append(Spacer(1, 4))
    story.append(Paragraph("8 · Tables", S['section']))
    for p in code_block("""<table border="1" cellpadding="5" cellspacing="2" bgcolor="#f0f0f0">
  <tr>
    <th>Name</th>    <!-- th = header cell: bold + centered -->
    <th>CGPA</th>
  </tr>
  <tr>
    <td>Ayele</td>
    <td>3.75</td>
  </tr>
  <tr>
    <td>Beshatu</td>
    <td>3.50</td>
  </tr>
</table>""", "Table Example"):
        story.append(p)
    story.append(bullet("Key attributes: <b>border</b> (px), <b>cellpadding</b> (space inside cell), <b>cellspacing</b> (space between cells), <b>align</b>, <b>bgcolor</b>, <b>width</b>."))

    story.append(Spacer(1, 4))
    story.append(Paragraph("9 · Meta Tags", S['section']))
    for p in code_block("""<head>
  <meta charset="UTF-8">
  <meta name="description" content="Free HTML tutorials">
  <meta name="keywords"    content="HTML, CSS, JavaScript">
  <meta name="author"      content="Diriba G.">
  <meta name="robots"      content="index, follow">
  <meta http-equiv="refresh" content="30">           <!-- refresh every 30s -->
  <meta http-equiv="refresh" content="5; url=new.html"> <!-- redirect in 5s -->
</head>""", "Meta Tag Examples"):
        story.append(p)

    story.append(Spacer(1, 4))
    story.append(Paragraph("10 · Special HTML Characters", S['section']))
    char_rows = [
        ("&amp;nbsp;", "Non-breaking space"),
        ("&amp;lt; / &amp;gt;", "Less-than / greater-than (&lt; &gt;)"),
        ("&amp;amp;", "Ampersand (&amp;)"),
        ("&amp;copy;", "Copyright ©"),
        ("&amp;reg;", "Registered trademark ®"),
        ("&amp;quot;", 'Double quote "'),
        ("&amp;times; / &amp;divide;", "× / ÷"),
    ]
    story.append(two_col_table(char_rows, header=["Entity", "Character"], col_widths=[60*mm, 110*mm]))

    story.append(PageBreak())

    # ══════════════════════════════════════════════════════════════════════════
    # CHAPTER 3 – CSS
    # ══════════════════════════════════════════════════════════════════════════
    story.append(chapter_header("Chapter 3 – CSS (Cascading Style Sheets)"))
    story.append(Spacer(1, 4))

    story.append(Paragraph("1 · CSS Syntax", S['section']))
    story.append(note_box("A CSS rule = selector { property: value; }  — declarations separated by semicolons."))
    for p in code_block("""/* Multiple selectors share one rule */
h1, h2, h3 { color: green; font-weight: bold; }

/* Comment style */
p { font-size: 16px; /* inline comment */ }""", "CSS Syntax"):
        story.append(p)

    story.append(Spacer(1, 4))
    story.append(Paragraph("2 · Selectors", S['section']))
    sel_rows = [
        ("Tag / Type", "p { … }  h1 { … }", "Targets all elements of that type."),
        ("Class", ".myClass { … }", "Targets any element with class=\"myClass\". Use . prefix."),
        ("ID", "#myId { … }", "Targets ONE unique element with id=\"myId\". Use # prefix."),
        ("Combined", "h1.center { … }", "Only &lt;h1&gt; elements with class center."),
        ("Pseudo-class", "a:hover { … }", "Applies when mouse is over a link."),
    ]
    data = [[Paragraph("<b>Type</b>", S['body']), Paragraph("<b>Syntax</b>", S['body']), Paragraph("<b>Effect</b>", S['body'])]]
    for r in sel_rows:
        data.append([Paragraph(r[0], S['body']), Paragraph(r[1], S['code']), Paragraph(r[2], S['body'])])
    t = Table(data, colWidths=[30*mm, 55*mm, 85*mm])
    t.setStyle(TableStyle([
        ('GRID', (0,0), (-1,-1), 0.4, HexColor("#aabbcc")),
        ('BACKGROUND', (0,0), (-1,0), HexColor("#dde8ff")),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [white, LIGHT_BG]),
        ('FONTSIZE', (0,0), (-1,-1), 8.5),
        ('TOPPADDING', (0,0), (-1,-1), 4),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
        ('LEFTPADDING', (0,0), (-1,-1), 6),
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
    ]))
    story.append(t)

    story.append(Spacer(1, 4))
    story.append(Paragraph("Pseudo-Class Links", S['subsection']))
    for p in code_block("""a:link    { color: red; }      /* unvisited */
a:visited { color: green; }   /* visited */
a:hover   { color: yellow; }  /* mouse over */""", "Link Pseudo-classes"):
        story.append(p)

    story.append(Spacer(1, 4))
    story.append(Paragraph("3 · Three Ways to Add CSS", S['section']))

    story.append(Paragraph("Inline (highest priority, hardest to maintain):", S['subsection']))
    for p in code_block('<h1 style="color: red; font-size: 24px;">Inline Style</h1>',
                        "Inline CSS"):
        story.append(p)

    story.append(Paragraph("Embedded / Internal (document-specific):", S['subsection']))
    for p in code_block("""<head>
  <style type="text/css">
    body { background-color: powderblue; }
    h1   { color: blue; }
    p    { color: red; font-size: 18pt; }
    .blue { color: blue; }
  </style>
</head>""", "Embedded CSS"):
        story.append(p)

    story.append(Paragraph("External (best practice — one file controls the whole site):", S['subsection']))
    for p in code_block("""<!-- In HTML <head> -->
<link rel="stylesheet" type="text/css" href="styles.css">

/* OR using @import inside a <style> block */
<style> @import url("styles.css"); </style>""", "External CSS Linking"):
        story.append(p)

    story.append(Spacer(1, 3))
    story.append(key_box("Cascading Priority (lowest → highest): 1. Browser default  2. External CSS  3. Internal CSS  4. Inline style. ID rules beat class rules. Explicit styles beat inherited ones."))

    story.append(Spacer(1, 4))
    story.append(Paragraph("4 · Font & Text Properties", S['section']))
    font_rows = [
        ("color", "Text color. Name or #hex or rgb()."),
        ("font-size", "px, pt, em, %, keyword (small/large/etc.). Browser default = 16px."),
        ("font-weight", "normal | bold | bolder | lighter | 100–900"),
        ("font-family", "Comma-list of fonts. Always end with generic (serif/sans-serif/monospace)."),
        ("font-style", "normal | italic | oblique"),
        ("font-variant", "normal | small-caps"),
        ("text-decoration", "none | underline | overline | line-through | blink"),
        ("text-align", "left | right | center | justify"),
        ("text-transform", "uppercase | lowercase | capitalize | none"),
        ("text-indent", "Indent first line. px or em or %."),
    ]
    story.append(two_col_table(font_rows, header=["Property", "Values / Notes"], col_widths=[45*mm, 125*mm]))

    for p in code_block("""/* Shorthand font: style variant weight size/line-height family */
font: italic small-caps bold 12px/16px Verdana, sans-serif;

/* Same as: */
font-style: italic;   font-variant: small-caps;  font-weight: bold;
font-size: 12px;      line-height: 16px;         font-family: Verdana, sans-serif;""", "Font Shorthand"):
        story.append(p)

    story.append(Spacer(1, 4))
    story.append(Paragraph("5 · Background Properties", S['section']))
    for p in code_block("""/* Shorthand */
background: #FFF0C0 url("back.gif") no-repeat fixed top;

/* Longhand */
background-color: #FFF0C0;
background-image: url("back.gif");
background-repeat: no-repeat;      /* repeat | repeat-x | repeat-y | no-repeat */
background-attachment: fixed;      /* fixed | scroll */
background-position: top left;     /* top/center/bottom  left/center/right */""", "Background Properties"):
        story.append(p)

    story.append(Spacer(1, 4))
    story.append(Paragraph("6 · The Box Model", S['section']))
    story.append(note_box("Every HTML element is a box: Content → Padding → Border → Margin (inside out)."))
    for p in code_block("""div {
  width: 200px;
  height: 100px;
  padding: 10px 20px;          /* top-bottom=10, left-right=20 */
  border: 1px solid red;       /* width  style  color */
  margin: 5px 3px 8px;         /* top=5  right/left=3  bottom=8 */
}

/* margin/padding shorthand patterns */
margin: 5px;               /* all 4 sides = 5px */
margin: 10px 20px;         /* top-bottom=10  left-right=20 */
margin: 5px 3px 8px;       /* top  left-right  bottom */
margin: 1px 3px 5px 7px;  /* top  right  bottom  left (clockwise) */""", "Box Model Examples"):
        story.append(p)

    story.append(Spacer(1, 4))
    story.append(Paragraph("7 · Borders", S['section']))
    for p in code_block("""border: 1px solid red;          /* shorthand */
border-style: dotted solid double dashed;  /* top right bottom left */
border-top-color: blue;
border-left-width: 3px;

/* border-style one value = all sides */
border-style: dotted;           /* all four = dotted */""", "Border Examples"):
        story.append(p)

    story.append(Spacer(1, 4))
    story.append(Paragraph("8 · display Property", S['section']))
    story.append(bullet("<b>display: block</b> — element starts on a new line, takes full width (e.g. &lt;div&gt;, &lt;p&gt;, &lt;h1&gt;)."))
    story.append(bullet("<b>display: inline</b> — no line break; flows with text (e.g. &lt;span&gt;, &lt;a&gt;, &lt;img&gt;)."))

    story.append(Spacer(1, 4))
    story.append(Paragraph("9 · CSS Units Quick Reference", S['section']))
    unit_rows = [
        ("px", "Pixels. Absolute screen unit."),
        ("em", "Relative to current font-size. 2em = twice the current font."),
        ("%", "Percentage of the parent element."),
        ("pt", "Points (1pt = 1/72 inch). Common for print."),
        ("in / cm / mm", "Real-world inches/centimeters/millimeters."),
    ]
    story.append(two_col_table(unit_rows, header=["Unit", "Meaning"], col_widths=[25*mm, 145*mm]))

    story.append(PageBreak())

    # ══════════════════════════════════════════════════════════════════════════
    # CHAPTER 4 – JAVASCRIPT (biggest section)
    # ══════════════════════════════════════════════════════════════════════════
    story.append(chapter_header("Chapter 4 – JavaScript  ★ HIGH PRIORITY ★"))
    story.append(Spacer(1, 4))

    story.append(Paragraph("1 · What is JavaScript?", S['section']))
    story.append(bullet("Lightweight, interpreted (not compiled) scripting language embedded in HTML."))
    story.append(bullet("Adds interactivity: validates forms, reacts to events, manipulates the page."))
    story.append(bullet("Client-side — runs in the browser, not on the server."))
    story.append(bullet("Loosely typed: no need to declare variable types. Case-sensitive."))

    story.append(Spacer(1, 3))
    story.append(Paragraph("JS vs Java (common exam question):", S['subsection']))
    jj_rows = [
        ("Interpreted", "Compiled"),
        ("Loosely typed (no type declaration)", "Strongly typed"),
        ("Embedded in HTML", "Applet separate from HTML"),
        ("Dynamic binding (checked at run-time)", "Static binding (checked at compile-time)"),
        ("No graphics / threads / networking", "Full AWT, threads, sockets"),
    ]
    data = [[Paragraph("<b>JavaScript</b>", S['body']), Paragraph("<b>Java</b>", S['body'])]]
    for r in jj_rows:
        data.append([Paragraph(r[0], S['body']), Paragraph(r[1], S['body'])])
    t = Table(data, colWidths=[87*mm, 83*mm])
    t.setStyle(TableStyle([
        ('GRID', (0,0), (-1,-1), 0.4, HexColor("#aabbcc")),
        ('BACKGROUND', (0,0), (-1,0), HexColor("#dde8ff")),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [white, LIGHT_BG]),
        ('FONTSIZE', (0,0), (-1,-1), 8.5),
        ('TOPPADDING', (0,0), (-1,-1), 4),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
        ('LEFTPADDING', (0,0), (-1,-1), 6),
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
    ]))
    story.append(t)

    story.append(Spacer(1, 5))
    story.append(Paragraph("2 · Adding JavaScript to HTML", S['section']))

    story.append(Paragraph("a) In &lt;head&gt; (functions loaded before page content):", S['subsection']))
    for p in code_block("""<html>
<head>
  <script language="javascript">
    function greet() {
      alert("Hello from head!");
    }
  </script>
</head>
<body onload="greet()">
  <!-- onload calls greet() when page finishes loading -->
</body>
</html>""", "JS in head"):
        story.append(p)

    story.append(Paragraph("b) In &lt;body&gt; (writes content directly):", S['subsection']))
    for p in code_block("""<body>
  <script language="javascript">
    document.write("Written by JavaScript!");
  </script>
</body>""", "JS in body"):
        story.append(p)

    story.append(Paragraph("c) External .js file (reusable across pages):", S['subsection']))
    for p in code_block("""<script language="JavaScript" src="myScript.js"></script>
<!-- Note: the external file must NOT contain <script> tags -->""", "External JS"):
        story.append(p)

    story.append(Spacer(1, 5))
    story.append(Paragraph("3 · Variables & Data Types", S['section']))
    for p in code_block("""// var = local to function; no var = global
var name = "Ayele";        // String
var age  = 21;             // Number
var pass = true;           // Boolean
var x    = null;           // null  (also equals 0 and false)
var y;                     // undefined

// Loose typing: same variable can change type
var myVar = 33;
myVar = "Hello";           // now a string — valid in JS

// String concatenation with +
var msg = "Count: " + 10;  // "Count: 10"
var r   = 33 + "Hi";       // "33Hi" (string wins)""", "Variables & Types"):
        story.append(p)
    story.append(bullet("Variable names: start with letter or _ ; can contain digits. Case-sensitive."))
    story.append(bullet("Valid: Last_Name, status, _name, myVar2. Invalid: 2myVar, my-var."))

    story.append(Spacer(1, 5))
    story.append(Paragraph("4 · Operators", S['section']))
    for p in code_block("""// Arithmetic
+  -  *  /  %            // +  also concatenates strings
x++  x--  ++x  --x       // post/pre increment/decrement

// Examples of ++ vs pre-increment
x = 1; alert(x++); alert(x);  // shows 1, then 2
x = 1; alert(++x); alert(x);  // shows 2, then 2

// Assignment
x += y;  x -= y;  x *= y;  x /= y;

// Comparison
==  !=  <  <=  >  >=

// Logical
&&  ||  !

// Ternary (conditional)
x = (1 < 5) ? 'a' : 'b';   // x gets 'a'""", "Operators"):
        story.append(p)

    story.append(Spacer(1, 4))
    story.append(key_box("Operator Precedence (low → high): assignment → ternary ?: → || → && → == != → < > <= >= → + - → * / % → ! ++ -- → () [] ."))

    story.append(Spacer(1, 5))
    story.append(Paragraph("5 · Pop-up Boxes", S['section']))
    for p in code_block("""// ALERT – just shows a message; user clicks OK
alert("Warning: file not saved!");

// CONFIRM – returns true (OK) or false (Cancel)
if (confirm("Are you sure you want to delete?")) {
    // user clicked OK
} else {
    // user clicked Cancel
}

// PROMPT – returns the text entered, or null if cancelled
var name = prompt("Enter your name:", "Harry Potter");
if (name == null || name == "") {
    alert("Cancelled.");
} else {
    alert("Hello " + name + "!");
}

// EVAL – evaluates a string as JS code
eval("result = 5 + 5;");   // result = 10""", "Pop-up Box Examples"):
        story.append(p)

    story.append(Spacer(1, 5))
    story.append(Paragraph("6 · Control Structures", S['section']))

    story.append(Paragraph("if / if-else:", S['subsection']))
    for p in code_block("""if (age < 18) {
    alert("Not allowed to vote.");
}

if (score >= 90) {
    grade = "A";
} else if (score >= 80) {
    grade = "B";
} else {
    grade = "C";
}""", "if / if-else"):
        story.append(p)

    story.append(Paragraph("for loop:", S['subsection']))
    for p in code_block("""// for (init; condition; update)
for (var i = 0; i < 5; i++) {
    document.write("Item " + i + "<br>");
}

// Summation function using for loop
function summation(endVal) {
    var total = 0;
    for (var i = 1; i <= endVal; i++) {
        total += i;
    }
    return total;
}
document.write(summation(5));  // Output: 15""", "for Loop Examples"):
        story.append(p)

    story.append(Spacer(1, 5))
    story.append(Paragraph("7 · Functions", S['section']))
    story.append(note_box("Functions run when called by an event or another statement. Use return to send a value back."))
    for p in code_block("""// Function declaration
function add(a, b) {
    return a + b;
}

// Calling a function
var result = add(3, 4);   // result = 7
alert(result);

// Full working example with form
function compute(form) {
    form.result.value = eval(form.expr.value);
}""", "Functions"):
        story.append(p)

    for p in code_block("""<form>
  Expression: <input type="text" name="expr" size="15">
  <input type="button" value="Calculate" onclick="compute(this.form)">
  <br>Result: <input type="text" name="result" size="15">
</form>""", "Function with Form (HTML side)"):
        story.append(p)

    story.append(Spacer(1, 5))
    story.append(Paragraph("8 · Arrays", S['section']))
    for p in code_block("""// Create
var students = new Array(4);   // size optional
students[0] = "Ayele";
students[1] = "Beshatu";
students[2] = "Garuma";
students[3] = "Burte";

// Shorthand creation
var colors = ["red", "green", "blue"];

// Access (index starts at 0!)
alert("Third student: " + students[2]);   // Garuma

// Length
alert("Total: " + students.length);       // 4

// Loop through array
for (var i = 0; i < students.length; i++) {
    document.write(students[i] + "<br>");
}""", "Array Examples"):
        story.append(p)

    story.append(Spacer(1, 5))
    story.append(Paragraph("9 · Event Handling", S['section']))
    story.append(note_box("Events are user actions (click, keypress, load, etc.). Event handlers are attributes on HTML elements."))

    story.append(Paragraph("Key Event Handlers:", S['subsection']))
    ev_rows = [
        ("onclick", "User clicks element."),
        ("onload", "Page (or image) finishes loading."),
        ("onmouseover / onmouseout", "Mouse enters/leaves element."),
        ("onfocus / onblur", "Field gains/loses input focus."),
        ("onchange", "Select/text field loses focus AND value changed."),
        ("onsubmit", "Form submitted."),
        ("onreset", "Form reset."),
        ("onkeydown / onkeyup", "Key pressed / released."),
        ("ondblclick", "Double-click."),
    ]
    story.append(two_col_table(ev_rows, header=["Handler", "Triggers when…"], col_widths=[55*mm, 115*mm]))

    for p in code_block("""<script>
function adder(n1, n2) {
    document.write("Sum: " + (n1 + n2));
}
function subtractor(n1, n2) {
    document.write("Diff: " + (n1 - n2));
}
</script>

<form>
  <input type="button" value="Add"      onclick="adder(10, 30)">
  <input type="button" value="Subtract" onclick="subtractor(20, 50)">
</form>

<!-- onload: runs when page loads -->
<body onload="alert('Welcome!')">

<!-- onmouseover: changes status bar text -->
<a href="http://meu.edu/" onmouseover="window.status='MEU Site'; return true">
  Visit MEU
</a>""", "Event Handler Examples"):
        story.append(p)

    story.append(Spacer(1, 5))
    story.append(Paragraph("10 · Form Validation", S['section']))
    story.append(note_box("Validate data on the client before sending to the server. Check for empty fields, format, value ranges."))

    for p in code_block("""<script>
// Validate name is not empty
function test1(form) {
    if (form.text1.value == "") {
        alert("Please enter a name!");
    } else {
        alert("Hello " + form.text1.value + "!");
    }
}

// Validate email has @
function test2(form) {
    if (form.email.value == "" || form.email.value.indexOf('@') == -1) {
        alert("No valid e-mail address!");
    } else {
        alert("OK!");
    }
}

// Validate number in range 1-9 on submit
function checkit() {
    var val = parseInt(document.myform.mytext.value);
    if (val > 0 && val < 10) {
        return true;    // allow submit
    } else {
        alert("Out of range: " + val);
        return false;   // block submit
    }
}
</script>

<form name="first">
  Name: <input type="text" name="text1">
  <input type="button" value="Check" onclick="test1(this.form)">
  <br>
  Email: <input type="text" name="email">
  <input type="button" value="Check" onclick="test2(this.form)">
</form>

<form name="myform" onsubmit="return checkit()">
  Number 1-9: <input type="text" name="mytext">
  <input type="submit">
</form>""", "Form Validation Examples"):
        story.append(p)

    story.append(Spacer(1, 5))
    story.append(Paragraph("11 · document.write & Input/Output", S['section']))
    for p in code_block("""// Write HTML to page
document.write("<h1>Hello!</h1>");

// Concatenation
var count = 10;
document.write("<h2>Counter is " + count + "</h2>");

// Write image tag (mix quote types)
document.write("<img src='photo.jpg'>");""", "document.write"):
        story.append(p)

    story.append(Spacer(1, 5))
    story.append(Paragraph("12 · JavaScript Objects", S['section']))

    story.append(Paragraph("Math Object", S['subsection']))
    math_rows = [
        ("Math.PI", "3.14159…"),
        ("Math.abs(x)", "Absolute value"),
        ("Math.ceil(x)", "Round UP to next integer"),
        ("Math.floor(x)", "Round DOWN to next integer"),
        ("Math.round(x)", "Round to nearest (≥.5 rounds up, negative rounds toward zero)"),
        ("Math.pow(x,y)", "x to the power y"),
        ("Math.sqrt(x)", "Square root"),
        ("Math.random()", "Random number 0 ≤ n &lt; 1"),
        ("Math.max(a,b)", "Larger of a or b"),
        ("Math.min(a,b)", "Smaller of a or b"),
        ("Math.sin/cos/tan(x)", "Trig functions (argument in radians)"),
    ]
    story.append(two_col_table(math_rows, header=["Method/Property", "Returns"], col_widths=[60*mm, 110*mm]))

    for p in code_block("""Math.round(3.5);    // 4
Math.round(-3.5);   // -3  (rounds toward positive infinity)
Math.pow(5, 2);     // 25
Math.floor(1.6);    // 1
Math.ceil(1.6);     // 2
Math.random();      // e.g. 0.7341...""", "Math Examples"):
        story.append(p)

    story.append(Spacer(1, 4))
    story.append(Paragraph("String Object", S['subsection']))
    str_rows = [
        ("length", "Number of characters."),
        ("charAt(i)", "Character at index i."),
        ("indexOf(str)", "First occurrence of str, or -1."),
        ("lastIndexOf(str)", "Last occurrence of str."),
        ("concat(str)", "Joins two strings."),
        ("slice(start, end)", "Extracts part of string."),
        ("substring(start, end)", "Similar to slice."),
        ("substr(start, len)", "From start, for len chars."),
        ("toUpperCase() / toLowerCase()", "Case conversion."),
        ("split(delimiter)", "Splits into array of strings."),
        ("replace(old, new)", "Replaces first match."),
    ]
    story.append(two_col_table(str_rows, header=["Method/Property", "Effect"], col_widths=[55*mm, 115*mm]))

    for p in code_block("""var s = new String("Hello World");
// OR: var s = "Hello World";

s.length;              // 11
s.toUpperCase();       // "HELLO WORLD"
s.indexOf("World");    // 6
s.substring(0, 5);     // "Hello"
s.replace("World", "JS");  // "Hello JS"
s.split(" ");          // ["Hello", "World"]""", "String Method Examples"):
        story.append(p)

    story.append(Spacer(1, 4))
    story.append(Paragraph("Date Object", S['subsection']))
    for p in code_block("""var today = new Date();
var d = today.getDate();        // 1-31
var m = today.getMonth();       // 0-11  (January = 0!)
var y = today.getFullYear();    // e.g. 2026
var h = today.getHours();       // 0-23
var min = today.getMinutes();   // 0-59
var sec = today.getSeconds();   // 0-59
var day = today.getDay();       // 0-6  (Sunday = 0)

document.write("Today: " + d + "/" + m + "/" + y);

// Set a specific date
var bday = new Date("September 11, 2001");
bday.getDay();    // 2 = Tuesday
bday.setYear(2002);""", "Date Object Examples"):
        story.append(p)

    story.append(Spacer(1, 4))
    story.append(Paragraph("Number Object", S['subsection']))
    for p in code_block("""var n = 123.455;
n.toFixed(2);         // "123.46"   (2 decimal places, rounds)
n.toExponential(3);   // "1.235e+2"
n.toPrecision(4);     // "123.5"    (4 total significant digits)

Number.MAX_VALUE;     // largest possible number (~1.8 × 10^308)
Number.MIN_VALUE;     // smallest positive number (~5 × 10^-324)""", "Number Object Examples"):
        story.append(p)

    story.append(Spacer(1, 4))
    story.append(Paragraph("Window Object", S['subsection']))
    win_rows = [
        ("window.open(url, name, features)", "Opens a new browser window."),
        ("window.close()", "Closes current window."),
        ("window.alert(msg)", "Alert dialog."),
        ("window.confirm(msg)", "Confirm dialog (true/false)."),
        ("window.prompt(msg, default)", "Prompt dialog (string or null)."),
        ("window.setInterval(fn, ms)", "Repeatedly call fn every ms milliseconds."),
        ("window.setTimeout(fn, ms)", "Call fn once after ms milliseconds."),
        ("window.clearInterval(id)", "Stop a setInterval."),
        ("window.focus()", "Give focus to window."),
        ("window.status", "Text in browser status bar."),
    ]
    story.append(two_col_table(win_rows, header=["Method/Property", "Effect"], col_widths=[70*mm, 100*mm]))

    for p in code_block("""// Open a new small window
var win = window.open("", "New", "height=250,width=250,toolbar=no,scrollbars=yes");
win.document.write("<h1>Hello from new window!</h1>");
win.document.close();

// Digital clock using setInterval
var t = setInterval("showTime()", 1000);  // every 1 second
function showTime() {
    var dt = new Date();
    var h = dt.getHours();
    var m = dt.getMinutes();
    var s = dt.getSeconds();
    if (m < 10) m = "0" + m;
    if (s < 10) s = "0" + s;
    document.display.time.value = h + ":" + m + ":" + s;
}""", "Window Examples"):
        story.append(p)

    story.append(Spacer(1, 4))
    story.append(Paragraph("Document Object", S['subsection']))
    doc_rows = [
        ("document.write(str)", "Write HTML string to page."),
        ("document.writeln(str)", "Same + adds carriage return (only visible inside &lt;pre&gt;)."),
        ("document.bgColor", "Background color."),
        ("document.fgColor", "Foreground (text) color."),
        ("document.linkColor / alinkColor / vlinkColor", "Link / active link / visited link colors."),
        ("document.title", "Page title."),
        ("document.forms[0]", "First form on page."),
        ("document.images[]", "Array of all images on page."),
        ("document.getElementById(id)", "Get element by its id attribute."),
        ("element.innerHTML", "Get/set the HTML inside an element."),
    ]
    story.append(two_col_table(doc_rows, header=["Property/Method", "Effect"], col_widths=[70*mm, 100*mm]))

    for p in code_block("""// Change paragraph text using innerHTML
document.getElementById("demo").innerHTML = "Hello World!";

// Change link colors
document.linkColor  = "red";
document.alinkColor = "blue";
document.vlinkColor = "green";""", "Document Object Examples"):
        story.append(p)

    story.append(Spacer(1, 4))
    story.append(Paragraph("History Object", S['subsection']))
    for p in code_block("""history.back();       // go to previous page
history.forward();    // go to next page
history.go(-2);       // go back 2 pages
history.go(0);        // reload current page""", "History Object"):
        story.append(p)

    story.append(Spacer(1, 5))
    story.append(Paragraph("13 · Form Processing (Radio, Checkbox, Select)", S['section']))
    for p in code_block("""// Access form elements
var val = document.formName.fieldName.value;    // read
document.formName.fieldName.value = "new";      // write

// Radio button array (same name = array)
if (document.test.sex[0].checked) {
    sex = document.test.sex[0].value;  // e.g. "Male"
}

// Select list
var sel = document.myForm.mySelect;
var chosen = sel.options[sel.selectedIndex].text;

// Select properties
sel.length;          // number of options
sel.selectedIndex;   // index of selected option (-1 if none)
sel.options[i].text; // text label of option i
sel.options[i].value;// value of option i""", "Form Element Access"):
        story.append(p)

    for p in code_block("""<!-- Full radio button example -->
<script>
function hello() {
    var name = document.test.uname.value;
    var sex;
    if (document.test.sex[0].checked)
        sex = document.test.sex[0].value;
    else if (document.test.sex[1].checked)
        sex = document.test.sex[1].value;
    alert("Hello, " + name + "! You are " + sex);
}
</script>
<form name="test">
  Name: <input type="text" name="uname"><br>
  Sex:  <input type="radio" name="sex" value="Male">Male
        <input type="radio" name="sex" value="Female">Female<br>
  <input type="button" value="Say Hello" onclick="hello()">
</form>""", "Radio Button Form Example"):
        story.append(p)

    story.append(Spacer(1, 5))
    story.append(Paragraph("14 · Image Slideshow (setInterval)", S['section']))
    for p in code_block("""<script>
var photos = ['coffee.png', 'nature.png', 'city.jpg', 'desert.jpg'];
var current = 0;
var t = setInterval("slideshow()", 2000);  // every 2 seconds

function slideshow() {
    current++;
    if (current > photos.length - 1)
        current = 0;
    document.images.photo.src = photos[current];
}
</script>
<body>
  <img src="coffee.png" id="photo" height="80%">
</body>""", "Image Slideshow"):
        story.append(p)

    story.append(PageBreak())

    # ══════════════════════════════════════════════════════════════════════════
    # QUICK REFERENCE CHEAT SHEET
    # ══════════════════════════════════════════════════════════════════════════
    story.append(chapter_header("Quick Reference Cheat Sheet"))
    story.append(Spacer(1, 4))

    story.append(Paragraph("HTML Essential Tags", S['section']))
    hr_rows = [
        ("Document", "&lt;html&gt; &lt;head&gt; &lt;title&gt; &lt;body&gt; &lt;meta&gt;"),
        ("Headings", "&lt;h1&gt; to &lt;h6&gt;"),
        ("Text", "&lt;p&gt; &lt;br&gt; &lt;hr&gt; &lt;pre&gt; &lt;b&gt; &lt;i&gt; &lt;u&gt; &lt;strike&gt; &lt;sub&gt; &lt;sup&gt; &lt;big&gt; &lt;small&gt; &lt;center&gt; &lt;font&gt;"),
        ("Links", "&lt;a href='...'&gt; target, name, title, accesskey attributes"),
        ("Images", "&lt;img src alt width height border align hspace vspace&gt; &lt;map&gt; &lt;area&gt;"),
        ("Tables", "&lt;table border cellpadding cellspacing&gt; &lt;tr&gt; &lt;th&gt; &lt;td&gt;"),
        ("Semantic", "&lt;em&gt; &lt;strong&gt; &lt;abbr&gt; &lt;acronym&gt; &lt;code&gt; &lt;blockquote&gt;"),
        ("Comments", "&lt;!-- text --&gt;"),
    ]
    story.append(two_col_table(hr_rows, header=["Category", "Tags/Attributes"], col_widths=[35*mm, 135*mm]))

    story.append(Spacer(1, 5))
    story.append(Paragraph("CSS Most-Tested Properties", S['section']))
    css_rows = [
        ("Selectors", "tag  .class  #id  tag.class  a:link  a:hover"),
        ("Linking", "inline style=''  |  &lt;style&gt; (embedded)  |  &lt;link href=''&gt; (external)"),
        ("Priority", "Inline &gt; Internal &gt; External &gt; Browser default"),
        ("Font", "font-size  font-family  font-weight  font-style  (shorthand: font:)"),
        ("Text", "color  text-align  text-decoration  text-transform  text-indent"),
        ("Background", "background-color  background-image  background-repeat  (shorthand: background:)"),
        ("Box model", "margin  padding  border  width  height"),
        ("Border", "border: width style color  (e.g. border: 1px solid red)"),
        ("Display", "block | inline"),
    ]
    story.append(two_col_table(css_rows, header=["Area", "Key Properties"], col_widths=[30*mm, 140*mm]))

    story.append(Spacer(1, 5))
    story.append(Paragraph("JavaScript Cheat Sheet", S['section']))
    js_rows = [
        ("Input/Output", "alert()  confirm()  prompt()  document.write()  eval()"),
        ("Variables", "var name = value;  — loosely typed, case-sensitive"),
        ("Operators", "+  -  *  /  %  ++  --  +=  -=  ==  !=  &lt;  &gt;  &amp;&amp;  ||  !  ?:"),
        ("Conditionals", "if (cond) {}  else if {}  else {}"),
        ("Loops", "for (init; cond; update) {}"),
        ("Functions", "function name(p1, p2) { return val; }"),
        ("Arrays", "var a = new Array(n);  a[0]='x';  a.length"),
        ("Events", "onclick  onload  onmouseover  onchange  onsubmit  onfocus  onblur"),
        ("Math", "Math.PI  .round()  .floor()  .ceil()  .pow()  .sqrt()  .random()"),
        ("String", ".length  .indexOf()  .substring()  .toUpperCase()  .split()  .replace()"),
        ("Date", "new Date()  .getDate()  .getMonth()  .getFullYear()  .getDay()"),
        ("Number", ".toFixed(n)  .toExponential(n)  .toPrecision(n)"),
        ("Window", ".open()  .alert()  .setInterval()  .setTimeout()  .close()"),
        ("Document", ".write()  .bgColor  .linkColor  .forms[]  .images[]  .getElementById()"),
        ("History", ".back()  .forward()  .go(n)"),
    ]
    story.append(two_col_table(js_rows, header=["Topic", "Key Methods/Syntax"], col_widths=[30*mm, 140*mm]))

    story.append(Spacer(1, 5))
    story.append(Paragraph("Common Exam Traps", S['section']))
    traps = [
        "Array indexes start at <b>0</b>, not 1. Length is always one more than the highest index.",
        "Date.getMonth() returns <b>0–11</b> (January = 0, December = 11).",
        "Date.getDay() returns <b>0–6</b> (Sunday = 0, Saturday = 6).",
        "alert/confirm/prompt are <b>window</b> methods but window. prefix is optional.",
        "confirm() returns <b>true</b> for OK, <b>false</b> for Cancel.",
        "prompt() returns <b>null</b> if user clicks Cancel.",
        "onsubmit must <b>return false</b> to block form submission.",
        "Pre-increment (++x) returns the new value; post-increment (x++) returns the old value.",
        "<b>==</b> compares value; in JS, null == 0 is false but null == null is true.",
        "String + number: string wins ('5' + 3 = '53'). number + number = math (5 + 3 = 8).",
        "CSS cascading: <b>ID > class > tag</b>. Last declared rule at same specificity wins.",
        "Meta tags go in <b>&lt;head&gt;</b>, not body.",
        "Image map coords: <b>rect</b>=x1,y1,x2,y2 &nbsp; <b>circle</b>=cx,cy,radius &nbsp; <b>poly</b>=x1,y1,x2,y2,...",
    ]
    for trap in traps:
        story.append(Paragraph(f"⚠ {trap}", S['bullet']))

    story.append(Spacer(1, 6))
    story.append(HRFlowable(width="100%", thickness=1.5, color=ACCENT))
    story.append(Spacer(1, 3))
    story.append(Paragraph("Good luck on your exam! 🎯", ParagraphStyle('good', fontName='Helvetica-Bold',
                                                                          fontSize=12, textColor=ACCENT, alignment=TA_CENTER)))
    story.append(Paragraph("HTML · CSS · JavaScript — Web Programming Study Guide", ParagraphStyle('footer',
        fontName='Helvetica', fontSize=8, textColor=GRAY, alignment=TA_CENTER)))

    doc.build(story)
    print("PDF built successfully.")


build_pdf()
