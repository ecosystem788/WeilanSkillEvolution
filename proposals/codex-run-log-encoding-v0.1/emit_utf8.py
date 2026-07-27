# Emits three CJK chars as raw UTF-8 bytes on stdout, bypassing any text-layer
# encoding on the producer side. The producer is provably correct; anything the
# consumer records other than these exact bytes was introduced by the consumer.
import sys
sys.stdout.buffer.write("\u6211\u4f1a\u5148\n".encode("utf-8"))
