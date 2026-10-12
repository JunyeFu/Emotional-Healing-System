"""LaTeX typography and PDF export for current task reviews."""
from pathlib import Path
import re
import subprocess
from pypdf import PdfReader

ROOT = Path(__file__).resolve().parents[2]
XELATEX = 'xelatex'


def escape(value):
    replacements = {'\\': r'\textbackslash{}', '&': r'\&', '%': r'\%',
                    '$': r'\$', '#': r'\#', '_': r'\_', '{': r'\{',
                    '}': r'\}', '~': r'\textasciitilde{}', '^': r'\textasciicircum{}'}
    text = ''.join(replacements.get(c, c) + (r'\allowbreak{}' if c in '/_-' else '') for c in str(value))
    return re.sub(r'[0-9a-fA-F]{32,}', lambda m: r'\allowbreak{}'.join(m[0][i:i+8] for i in range(0, len(m[0]), 8)), text)


PREAMBLE = r'''\documentclass[11pt,a4paper]{article}
\usepackage{fontspec}
\usepackage{xeCJK}
\setmainfont{Microsoft YaHei}[BoldFont=Microsoft YaHei Bold]
\setCJKmainfont{Microsoft YaHei}[BoldFont=Microsoft YaHei Bold]
\newfontfamily\titlelatin{SimHei}[AutoFakeBold=2]
\newCJKfontfamily\titlecjk{SimHei}[AutoFakeBold=2]
\usepackage[margin=22mm]{geometry}
\usepackage{graphicx}
\usepackage{needspace}
\usepackage[unicode,hidelinks,breaklinks]{hyperref}
\usepackage{fancyhdr}
\pagestyle{fancy}\fancyhf{}
\fancyfoot[C]{SRP 任务包审阅\quad\thepage}
\renewcommand{\headrulewidth}{0pt}
\setlength{\parindent}{0pt}
\setlength{\parskip}{7pt}
\linespread{1.28}
\emergencystretch=3em
\raggedbottom
\newcommand{\reviewtitle}[1]{\begin{center}{\titlelatin\titlecjk\bfseries\fontsize{21}{28}\selectfont #1}\end{center}\vspace{8pt}}
\newcommand{\reviewsection}[1]{\par\Needspace{5\baselineskip}\vspace{10pt}\begin{center}{\titlelatin\titlecjk\bfseries\fontsize{14}{20}\selectfont #1}\end{center}}
\newcommand{\reviewsubsection}[1]{\par\Needspace{4\baselineskip}\vspace{4pt}\begin{center}{\titlelatin\titlecjk\bfseries\fontsize{12}{18}\selectfont #1}\end{center}}
\begin{document}
'''


class Review:
    def __init__(self, title):
        self.parts = [PREAMBLE, r'\reviewtitle{' + escape(title) + '}']

    def add_paragraph(self, text):
        self.parts.append(escape(text) + '\n\n')

    def add_heading(self, text, level=1):
        command = 'reviewsection' if level == 1 else 'reviewsubsection'
        self.parts.append('\\' + command + '{' + escape(text) + '}')

    def add_picture(self, path, caption):
        self.parts.append(r'\par\begin{minipage}{\linewidth}\centering' + '\n' +
                          r'\includegraphics[width=\linewidth]{\detokenize{' + path.as_posix() + '}}\n' +
                          r'\par\small ' + escape(caption) + '\n' + r'\end{minipage}\par')

    def add_link(self, path, label):
        self.parts.append(r'\href{' + path.resolve().as_uri().replace('%', r'\%') +
                          '}{' + escape(label) + '}\n\n')

    def save(self, path):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text('\n'.join(self.parts) + '\n\\end{document}\n', encoding='utf-8')


def compile_pdf(path):
    output = ROOT / 'agent/local/artifacts/task-latex-20261008/build' / path.parent.name
    output.mkdir(parents=True, exist_ok=True)
    command = [XELATEX, '-interaction=nonstopmode', '-halt-on-error',
               '-no-shell-escape', '-output-directory=' + str(output), str(path)]
    for _ in range(2):
        result = subprocess.run(command, cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        (output / 'compile-output.txt').write_bytes(result.stdout)
        if result.returncode:
            raise RuntimeError(result.stdout.decode('utf-8', 'replace')[-5000:])
    target = path.with_suffix('.pdf')
    target.write_bytes((output / target.name).read_bytes())
    return target


def verify_review(path, summary):
    source = path.read_text(encoding='utf-8')
    expected = [summary['title'], summary['conclusion'], summary['historical_acceptance']['method']]
    expected.extend(p for section in summary['sections'] for p in section['paragraphs'])
    expected.extend(f['caption'] for f in summary.get('figures', []))
    assert all(escape(p) in source for p in expected), summary['task_id']
    assert source.count(r'\reviewsection{') == 3 and source.count(r'\reviewsubsection{') == 11
    pdf = PdfReader(path.with_suffix('.pdf'))
    assert len(pdf.pages) > 0
    normalize = lambda text: re.sub(r'\s+', '', text).replace('\u00ad', '').replace('-', '')
    pdf_text = normalize(''.join(page.extract_text() for page in pdf.pages))
    pdf_text = re.sub(r'SRP任务包审阅\d+', '', pdf_text)
    assert all(normalize(text) in pdf_text for text in expected), summary['task_id']
    images = sum(1 for page in pdf.pages for ref in page['/Resources'].get('/XObject', {}).values()
                 if ref.get_object().get('/Subtype') == '/Image')
    assert images >= len(summary.get('figures', [])), summary['task_id']
    fonts = set()
    for page in pdf.pages:
        for ref in page['/Resources']['/Font'].values():
            font = ref.get_object()
            fonts.add(str(font['/BaseFont']))
            descendant = font['/DescendantFonts'][0].get_object()
            descriptor = descendant['/FontDescriptor'].get_object()
            assert any(key in descriptor for key in ['/FontFile', '/FontFile2', '/FontFile3'])
    assert any('SimHei' in name for name in fonts), fonts
    assert any('MicrosoftYaHei' in name for name in fonts), fonts
    for link in summary.get('source_links', []):
        assert (ROOT / link['path']).exists(), link['path']
    return len(summary.get('source_links', []))
