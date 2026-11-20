# MULTI1Dvisual user manuals · 用户手册

[English manual](manual_EN/multi1dvisual_manual_en.pdf) · [中文手册](manual_CN/multi1dvisual_manual_zh.pdf) · [Practice data / 练习数据](examples/quickstart.zip)

The two editions share the layout and sample data. Each has its own chapter sources and screenshots of the corresponding interface language.

## Build the PDFs

Use XeLaTeX with xeCJK, TikZ, the TeX Gyre and Latin Modern fonts, and the packages listed in [the shared preamble](manual_shared/layout.tex). The Chinese font setup uses SimSun and Microsoft YaHei on Windows when available, and TeX's Fandol fonts on other installations. From each edition's directory run the corresponding command twice to resolve the contents and page references.

```sh
# In docs/manual_EN
xelatex -halt-on-error multi1dvisual_manual_en.tex

# In docs/manual_CN
xelatex -halt-on-error multi1dvisual_manual_zh.tex
```

To regenerate the practice archive, run `python docs/examples/make_quickstart.py` from the project root. It only requires the Python standard library.
