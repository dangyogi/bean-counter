# pdf_test.py

from pathlib import Path

from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import landscape, portrait, letter, inch


def hello(c):
    x = 20
    y = 770
    for i in range(6):  # 0 comes out as thin gray
        c.drawString(x, y - 20*i, str(i))
        c.setLineWidth(i)
        c.line(x + 50, y - 20*i, x + 150, y - 20*i)
    y -= 100
    c.setFont("Helvetica", 100)
    y -= 100
    c.setLineWidth(0)
    test_str = "Hfglpy_|;'\",/\\"
    width = c.stringWidth(test_str)        # 530.8 (~38% of size/char) for "Hfglpy_|;'\",/\\" at size 100
    print(f"{len(test_str)=}, {width=}")
    c.drawString(x, y, test_str)
    c.line(x - 10, y, 600, y)              # underneath (bottom of chars, not counting decenders, just below y)
                                           #   20% of size for decenders, below y
    c.line(x - 10, y + 100, 600, y + 100)  # on top (well above highest char),
                                           # highest char about 71% of size above y
    c.line(x, y - 50, x, y + 100)          # left (str starts 1/2 space between letters from x)
    c.setLineWidth(5)
    c.line(x + 200, y - 9.95, x + 272, y - 9.95)  # matches underscore char:
                                                  #   5% of font size for line width,
                                                  #   9.95% of font size below y pos of text

    y -= 150
    c.setLineWidth(5)                      # doesn't affect normal drawString (next line)
    c.drawString(x, y, test_str)
    c.setLineWidth(0)
    c.line(x - 10, y, 600, y)              # underneath (bottom of chars, not counting decenders, just below y)
    c.line(x - 10, y + 100, 600, y + 100)  # on top (well above highest char)
    c.line(x, y - 50, x, y + 100)          # left (str starts 1/2 space between letters from x)

def run():
    pagesize = portrait(letter)  # in points (1/72"), portrait is 612 x 792
    print(f"{pagesize=}")

    #pagesize = landscape(letter)

    width, height = pagesize

    path = Path("~/storage/downloads/test.pdf")
    c = canvas.Canvas(str(path.expanduser()), pagesize=pagesize)

    hello(c)

    # clears all settings (colors, fonts, etc).  These must be re-established.
    c.showPage()

    c.save()


if __name__ == "__main__":
    run()
