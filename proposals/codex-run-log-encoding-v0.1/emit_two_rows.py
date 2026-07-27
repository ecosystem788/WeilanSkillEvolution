# Adversarial line-boundary test. Row A's CJK run is ODD-length in UTF-8 bytes
# (3 chars = 9 bytes), so the unpaired lead byte swallows the ASCII char that
# follows it -- the case that actually breaks JSON. Row B is the pure-ASCII
# liveness proof. Question: does the damage stop at the line boundary, or does
# it eat the newline and take B down with A?
import sys
rows = []
for n in (1, 2, 3, 4):                       # 3n bytes: both parities covered
    text = "\u6211\u4f1a\u5148\u6d4b"[:n]
    rows.append('{"type":"item.completed","item":{"id":"i%d","type":"agent_message","text":"%s"}}' % (n, text))
rows.append('{"type":"turn.completed","usage":{"input_tokens":1}}')
sys.stdout.buffer.write(("\n".join(rows) + "\n").encode("utf-8"))
