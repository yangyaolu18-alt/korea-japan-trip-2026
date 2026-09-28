"""Consistent, assumed-rate RMB annotations for HTML and portable text."""
import html
import math
import re
from html.parser import HTMLParser

RATES = {'KRW': 0.005, 'JPY': 0.048}
NUMBER = r'\d[\d,]*(?:\.\d+)?'
AMOUNT = re.compile(r'(?<![\w¥₩])(?P<symbol>JP¥|₩|¥)\s*(?P<low>' + NUMBER + r')'
                    r'(?:\s*[–—~～-]\s*(?:JP¥|₩|¥)?\s*(?P<high>' + NUMBER + r'))?')

def cny_value(n):
    # Same half-up whole-yuan display as JavaScript Math.round.
    return f'{math.floor(n + 0.5):,}'

def annotate(text, rich=False):
    def replace(match):
        cur = 'KRW' if match['symbol'] == '₩' else 'JPY'
        low = float(match['low'].replace(',', ''))
        high = float((match['high'] or match['low']).replace(',', ''))
        a, b = cny_value(low * RATES[cur]), cny_value(high * RATES[cur])
        equivalent = '（约人民币 ' + (a if a == b else a + '–' + b) + ' 元）'
        raw = match[0]
        if not rich:
            return raw + equivalent
        return (f'<span class="foreign-money" data-currency="{cur}" data-low="{low:g}" data-high="{high:g}">'
                f'{html.escape(raw)}<span class="cny-equivalent">{equivalent}</span></span>')
    return AMOUNT.sub(replace, text)

class MoneyHTML(HTMLParser):
    """Transform text nodes only; preserve scripts, URLs, entities and controls."""
    def __init__(self):
        super().__init__(convert_charrefs=False)
        self.output = []
        self.skip = 0
    def handle_starttag(self, tag, attrs):
        self.output.append(self.get_starttag_text())
        if tag in ('script', 'style', 'label'): self.skip += 1
    def handle_startendtag(self, tag, attrs): self.output.append(self.get_starttag_text())
    def handle_endtag(self, tag):
        self.output.append(f'</{tag}>')
        if tag in ('script', 'style', 'label'): self.skip -= 1
    def handle_data(self, data): self.output.append(data if self.skip else annotate(data, rich=True))
    def handle_entityref(self, name): self.output.append('&' + name + ';')
    def handle_charref(self, name): self.output.append('&#' + name + ';')
    def handle_decl(self, decl): self.output.append('<!' + decl + '>')
    def handle_comment(self, data): self.output.append('<!--' + data + '-->')

def annotate_html(text):
    parser = MoneyHTML()
    parser.feed(text)
    parser.close()
    return ''.join(parser.output)
