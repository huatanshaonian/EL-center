#include <ctype.h>
#include <string.h>
#include "vfd_font.h"

//            a=0x01 b=0x02 c=0x04 d=0x08 e=0x10 f=0x20 g=0x40
static const uint8_t DIGITS[10] = {0x3F, 0x06, 0x5B, 0x4F, 0x66, 0x6D, 0x7D, 0x07, 0x7F, 0x6F};

int vfd_glyph(char c)
{
    if (c >= '0' && c <= '9') return DIGITS[c - '0'];
    switch (c) {
    case ' ': return 0x00;
    case '-': return 0x40;
    case '_': return 0x08;
    case '=': return 0x48;
    case '\'': return 0x02;
    case '"': return 0x22;
    case '*': return 0x63;   // 度数符号 °
    // 有大小写两种字形的字母
    case 'C': return 0x39; case 'c': return 0x58;
    case 'H': return 0x76; case 'h': return 0x74;
    case 'O': return 0x3F; case 'o': return 0x5C;
    case 'U': return 0x3E; case 'u': return 0x1C;
    case 'I': return 0x30; case 'i': return 0x04;
    default: break;
    }
    // 只有一种字形的字母：大小写同形
    switch (toupper((unsigned char)c)) {
    case 'A': return 0x77;
    case 'B': return 0x7C;   // b
    case 'D': return 0x5E;   // d
    case 'E': return 0x79;
    case 'F': return 0x71;
    case 'G': return 0x3D;
    case 'J': return 0x1E;
    case 'L': return 0x38;
    case 'N': return 0x54;   // n
    case 'P': return 0x73;
    case 'Q': return 0x67;   // q
    case 'R': return 0x50;   // r
    case 'S': return 0x6D;
    case 'T': return 0x78;   // t
    case 'Y': return 0x6E;   // y
    default: return -1;      // K M V W X Z 等七段表示不了
    }
}

// 文本 → 8 位字形；"." 并到前一位的 dp
int vfd_text_to_segs(const char *t, uint8_t out[8])
{
    int n = 0;
    memset(out, 0, 8);
    for (const char *p = t; *p; p++) {
        if (*p == '.') {
            if (n == 0) { if (n >= 8) return -1; out[n++] = SEG_DP; }   // 开头的点：独占一位
            else if (out[n - 1] & SEG_DP) { if (n >= 8) return -1; out[n++] = SEG_DP; }
            else out[n - 1] |= SEG_DP;
            continue;
        }
        int g = vfd_glyph(*p);
        if (g < 0 || n >= 8) return -1;
        out[n++] = (uint8_t)g;
    }
    return 0;
}

int vfd_visual_len(const char *t)
{
    int n = 0;
    for (const char *p = t; *p; p++) if (*p != '.') n++;
    return n;
}
