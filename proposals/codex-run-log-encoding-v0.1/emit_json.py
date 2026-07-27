# Emits one well-formed JSONL row whose only non-ASCII content is CJK text,
# as raw UTF-8 bytes. Any parse failure downstream is the recorder's doing.
import sys
row = '{"type":"item.completed","item":{"id":"item_0","type":"agent_message","text":"\u6211\u4f1a\u5148"}}\n'
sys.stdout.buffer.write(row.encode("utf-8"))
