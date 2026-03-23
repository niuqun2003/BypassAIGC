"""
知网 AIGC 全文报告单 PDF 解析器

颜色约定（通过逆向工程确认）：
  RGB(230,1,17)   → AI特征显著（计入AI特征字符数）
  RGB(217,158,76) → AI特征疑似（未计入AI特征字符数）
  RGB(64,64,64)   → 普通正文
  旁注格式: "13.0%(552)"  "6.8%(287)"

输出结构：
  CnkiReport
    .metadata         : 报告编号、检测时间、篇名、作者
    .summary          : 全文 AI特征值、AI特征字符数、总字符数
    .sections         : List[SectionStat]  章节级统计
    .flagged_fragments: List[FlaggedFragment]  被标记的原文片段
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional

try:
    import fitz  # pymupdf
except ImportError as e:
    raise ImportError("请安装 pymupdf: pip install pymupdf") from e


# ── 颜色常量 ────────────────────────────────────────────────────────────────

_COLOR_SIGNIFICANT = 0xE60111   # RGB(230,1,17)  AI特征显著
_COLOR_SUSPECTED   = 0xD99E4C   # RGB(217,158,76) AI特征疑似
_TOLERANCE = 8                   # 颜色容差（允许轻微的 CMYK→RGB 误差）


def _color_near(c: int, target: int, tol: int = _TOLERANCE) -> bool:
    """判断两个整数颜色是否接近（各通道差 ≤ tol）。"""
    for shift in (16, 8, 0):
        if abs(((c >> shift) & 0xFF) - ((target >> shift) & 0xFF)) > tol:
            return False
    return True


# ── 数据模型 ─────────────────────────────────────────────────────────────────

@dataclass
class ReportMetadata:
    report_no: str = ""
    detected_at: str = ""
    title: str = ""
    author: str = ""
    filename: str = ""


@dataclass
class ReportSummary:
    ai_ratio: float = 0.0       # AI特征值（0-1）
    ai_chars: int = 0            # AI特征字符数（显著）
    total_chars: int = 0         # 总字符数


@dataclass
class SectionStat:
    index: int = 0               # 序号
    name: str = ""               # 章节名称
    ai_ratio: float = 0.0        # AI特征值（0-1）
    ai_chars: int = 0            # AI特征字符数
    section_chars: int = 0       # 章节字符数


@dataclass
class FlaggedFragment:
    section_name: str = ""       # 所属章节名称
    text: str = ""               # 被标记的原文内容
    ai_ratio: float = 0.0        # 标注的 AI 比率（从旁注解析）
    char_count: int = 0          # 标注的字符数（从旁注解析）
    tier: str = "significant"    # "significant" | "suspected"


@dataclass
class CnkiReport:
    metadata: ReportMetadata = field(default_factory=ReportMetadata)
    summary: ReportSummary = field(default_factory=ReportSummary)
    sections: List[SectionStat] = field(default_factory=list)
    flagged_fragments: List[FlaggedFragment] = field(default_factory=list)

    def flagged_section_names(self) -> List[str]:
        """返回有 AI 标记的章节名称列表。"""
        return [s.name for s in self.sections if s.ai_chars > 0]

    def significant_text(self) -> str:
        """合并所有显著标记片段的文本。"""
        return "\n".join(
            f.text for f in self.flagged_fragments if f.tier == "significant"
        )


# ── 工具函数 ─────────────────────────────────────────────────────────────────

_RE_RATIO     = re.compile(r'(\d+\.?\d*)\s*%')
_RE_ANNOTATION = re.compile(r'(\d+\.?\d*)\s*%\s*\((\d+)\)')   # "13.0%(552)"
_RE_CHARS_RATIO = re.compile(r'(\d+)\s*/\s*(\d+)')             # "552 / 4230"
_RE_SECTION_HEADER = re.compile(
    r'(\d+)\.\s+(.+?)\s+AI特征值[：:]\s*(\d+\.?\d*)\s*%\s+AI特征字符数\s*/\s*章节.*?字符数[：:]\s*(\d+)\s*/\s*(\d+)'
)


def _spans_from_page(page: fitz.Page):
    """提取页面上所有 (color, text) span，过滤水印（alpha < 200）。"""
    result = []
    for block in page.get_text("dict")["blocks"]:
        if block.get("type") != 0:
            continue
        for line in block.get("lines", []):
            for span in line.get("spans", []):
                alpha = span.get("alpha", 255)
                if alpha < 200:          # 水印：alpha=31
                    continue
                text = span.get("text", "")
                if not text.strip():
                    continue
                result.append((span.get("color", 0), text))
    return result


def _clean_text(page: fitz.Page) -> str:
    """提取页面文字，剔除水印（alpha < 200），拼合成干净文本。"""
    lines: list[str] = []
    for block in page.get_text("dict")["blocks"]:
        if block.get("type") != 0:
            continue
        for line in block.get("lines", []):
            parts = []
            for span in line.get("spans", []):
                if span.get("alpha", 255) < 200:
                    continue
                t = span.get("text", "")
                if t.strip():
                    parts.append(t)
            if parts:
                lines.append("".join(parts))
    return "\n".join(lines)


# ── 解析各阶段 ───────────────────────────────────────────────────────────────

def _parse_metadata(page: fitz.Page) -> ReportMetadata:
    """从第1页解析报告元数据。"""
    meta = ReportMetadata()
    full = _clean_text(page)

    m = re.search(r'NO:\s*(CNKIAIGC\S+)', full)
    if m:
        meta.report_no = m.group(1)

    m = re.search(r'检测时间[：:]\s*(\S+\s+\S+)', full)
    if m:
        meta.detected_at = m.group(1)

    m = re.search(r'篇名[：:]\s*(.+)', full)
    if m:
        meta.title = m.group(1).strip()

    m = re.search(r'作者[：:]\s*(.+)', full)
    if m:
        meta.author = m.group(1).strip()

    m = re.search(r'文件名[：:]\s*(.+)', full)
    if m:
        meta.filename = m.group(1).strip()

    return meta


def _parse_summary_and_sections(pages: List[fitz.Page]) -> tuple[ReportSummary, List[SectionStat]]:
    """从前几页解析全文总览和分段检测结果表。"""
    summary = ReportSummary()
    sections: List[SectionStat] = []

    # 合并第1-3页的干净文本（分段检测结果表可能跨页）
    combined = "\n".join(_clean_text(p) for p in pages[:3])

    # 全文 AI特征值
    m = re.search(r'AI特征值[：:]\s*(\d+\.?\d*)\s*%', combined)
    if m:
        summary.ai_ratio = float(m.group(1)) / 100

    # AI特征字符数 / 总字符数
    m = re.search(r'AI特征字符数[：:]\s*(\d+)\s*总字符数[：:]\s*(\d+)', combined)
    if m:
        summary.ai_chars = int(m.group(1))
        summary.total_chars = int(m.group(2))

    # 分段检测结果表：每行一个字段，顺序为 序号 / 百分比 / 字符比 / 章节名
    # 用状态机逐行扫描
    RE_INDEX   = re.compile(r'^(\d+)$')
    RE_PCT     = re.compile(r'^(\d+\.?\d*)\s*%$')
    RE_CHARRAT = re.compile(r'^(\d+)\s*/\s*(\d+)$')

    lines = combined.splitlines()
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        m_idx = RE_INDEX.match(line)
        if m_idx and i + 3 < len(lines):
            idx   = int(m_idx.group(1))
            pct_l = lines[i+1].strip()
            rat_l = lines[i+2].strip()
            nam_l = lines[i+3].strip()
            mp = RE_PCT.match(pct_l)
            mr = RE_CHARRAT.match(rat_l)
            if mp and mr and nam_l:
                # 章节名可能折行（如 "析_第1部分" 跟在下一行）
                name = nam_l
                if i + 4 < len(lines):
                    next_l = lines[i+4].strip()
                    # 若下一行不是数字（新序号）也不是百分比，则拼接
                    if next_l and not RE_INDEX.match(next_l) and not RE_PCT.match(next_l):
                        name += next_l
                        i += 1   # 额外消耗一行

                # 清理章节名：去掉页码（"— N —"）和意外拼接的下一章节名
                name = re.sub(r'—\s*\d+\s*—.*', '', name).strip()
                # 若名称以 "\d+\." 结尾（下一章节 header 泄漏），截断
                name = re.sub(r'\s*\d+\.\s*\S.*$', '', name).strip()

                sections.append(SectionStat(
                    index         = idx,
                    ai_ratio      = float(mp.group(1)) / 100,
                    ai_chars      = int(mr.group(1)),
                    section_chars = int(mr.group(2)),
                    name          = name,
                ))
                i += 4
                continue
        i += 1

    return summary, sections


_RE_PURE_PERCENT = re.compile(r'^\s*\d+\.?\d*\s*%\s*$')   # "0.0%" 纯百分比行
_RE_PURE_NUMBER  = re.compile(r'^\s*\d+\s*$')              # 纯数字行
_MIN_FRAGMENT_CHARS = 10                                    # 短于此的 span 可能是表格单元


def _is_table_noise(text: str) -> bool:
    """判断一段文字是否是表格里的噪声（纯数值/百分比，不是真实正文）。"""
    t = text.strip()
    return bool(_RE_PURE_PERCENT.match(t) or _RE_PURE_NUMBER.match(t))


def _parse_flagged_fragments(
    pages: List[fitz.Page],
    sections: List[SectionStat],
) -> List[FlaggedFragment]:
    """
    遍历全文页面，按颜色提取被标记的原文片段。
    策略：
      1. 收集连续的同色（显著/疑似）span，拼合成片段
      2. 从旁注（形如 "13.0%(552)"）提取 ai_ratio 和 char_count
      3. 过滤掉表格噪声（纯百分比/纯数字）
      4. 片段至少包含一段 ≥ MIN_FRAGMENT_CHARS 的实质内容
    """
    fragments: List[FlaggedFragment] = []

    # 有 AI 标记的章节名（章节解析正常时用；若为空退化为不过滤）
    flagged_section_names = {s.name for s in sections if s.ai_chars > 0}
    section_lookup = {s.name: s for s in sections}
    current_section = ""

    buf_tier: Optional[str] = None
    buf_lines: List[str] = []
    buf_annotation: Optional[str] = None

    def flush_fragment():
        nonlocal buf_tier, buf_lines, buf_annotation
        if buf_lines and buf_tier:
            text = "".join(buf_lines).strip()
            # 过滤掉全是噪声的片段（只有 "0.0%" 等）
            if len(text) >= _MIN_FRAGMENT_CHARS and not _is_table_noise(text):
                ratio, chars = 0.0, 0
                if buf_annotation:
                    ma = _RE_ANNOTATION.search(buf_annotation)
                    if ma:
                        ratio = float(ma.group(1)) / 100
                        chars = int(ma.group(2))
                fragments.append(FlaggedFragment(
                    section_name = current_section,
                    text         = text,
                    ai_ratio     = ratio,
                    char_count   = chars,
                    tier         = buf_tier,
                ))
        buf_tier  = None
        buf_lines = []
        buf_annotation = None

    for page in pages:
        spans = _spans_from_page(page)
        page_clean = _clean_text(page)

        # 更新当前章节（扫描本页是否包含有 AI 标记的章节名）
        for sec_name in flagged_section_names:
            if sec_name in page_clean:
                current_section = sec_name

        for color, text in spans:
            is_sig = _color_near(color, _COLOR_SIGNIFICANT)
            is_sus = _color_near(color, _COLOR_SUSPECTED)

            if is_sig or is_sus:
                tier_now = "significant" if is_sig else "suspected"

                # 旁注（"13.0%(552)"）→ 记录并跳过
                if _RE_ANNOTATION.search(text):
                    buf_annotation = text
                    continue

                # 纯噪声 span（表格里的 "0.0%"、"552" 等）→ flush 并跳过
                if _is_table_noise(text):
                    flush_fragment()
                    continue

                # 切换 tier 时 flush
                if buf_tier and buf_tier != tier_now:
                    flush_fragment()

                buf_tier = tier_now
                buf_lines.append(text)
            else:
                if buf_tier:
                    flush_fragment()

    flush_fragment()

    # 后处理：合并相邻的同 tier 的跨页无旁注片段
    # 条件：前一片段有旁注（有 char_count），后续片段无旁注（ai_ratio==0, char_count==0）
    # 或者：前后都无旁注（同一块内容被页面切断）
    merged: List[FlaggedFragment] = []
    for frag in fragments:
        if (merged
                and merged[-1].tier == frag.tier
                and frag.ai_ratio == 0.0
                and frag.char_count == 0):
            merged[-1] = FlaggedFragment(
                section_name = merged[-1].section_name or frag.section_name,
                text         = merged[-1].text + frag.text,
                ai_ratio     = merged[-1].ai_ratio,
                char_count   = merged[-1].char_count,
                tier         = merged[-1].tier,
            )
        else:
            merged.append(frag)

    return merged


# ── 公开入口 ─────────────────────────────────────────────────────────────────

def parse_cnki_report(pdf_path: str | Path) -> CnkiReport:
    """
    解析知网 AIGC 全文报告单 PDF，返回结构化 CnkiReport。

    Args:
        pdf_path: PDF 文件路径

    Returns:
        CnkiReport 对象，包含元数据、总览统计、章节统计、被标记片段列表

    Raises:
        ValueError: 若文件不是有效的知网 AIGC 报告
        FileNotFoundError: 若文件不存在
    """
    pdf_path = Path(pdf_path)
    if not pdf_path.exists():
        raise FileNotFoundError(f"文件不存在: {pdf_path}")

    doc = fitz.open(str(pdf_path))
    try:
        pages = list(doc)

        if not pages:
            raise ValueError("PDF 为空")

        # 验证是知网报告
        first_text = pages[0].get_text("text")
        if "AIGC检测" not in first_text and "知网" not in first_text:
            raise ValueError("不是有效的知网 AIGC 检测报告")

        metadata = _parse_metadata(pages[0])
        summary, sections = _parse_summary_and_sections(pages)
        flagged = _parse_flagged_fragments(pages, sections)

        return CnkiReport(
            metadata          = metadata,
            summary           = summary,
            sections          = sections,
            flagged_fragments = flagged,
        )
    finally:
        doc.close()


# ── CLI 快速测试 ─────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import sys, json

    path = sys.argv[1] if len(sys.argv) > 1 else \
        "/root/Projects/BypassAIGC/参考项目/TK制药公司班组长数字化培训体系优化研究_AIGC_全文报告单.pdf"

    report = parse_cnki_report(path)

    print("=" * 60)
    print("【元数据】")
    print(f"  报告编号: {report.metadata.report_no}")
    print(f"  检测时间: {report.metadata.detected_at}")
    print(f"  篇名:     {report.metadata.title}")
    print(f"  作者:     {report.metadata.author}")

    print("\n【全文总览】")
    print(f"  AI特征值:    {report.summary.ai_ratio*100:.1f}%")
    print(f"  AI特征字符数: {report.summary.ai_chars}")
    print(f"  总字符数:     {report.summary.total_chars}")

    print("\n【分段检测结果】")
    for s in report.sections:
        flag = " ← 有AI标记" if s.ai_chars > 0 else ""
        print(f"  [{s.index:2d}] {s.ai_ratio*100:.1f}%  {s.ai_chars}/{s.section_chars}  {s.name}{flag}")

    print("\n【被标记片段】")
    for i, f in enumerate(report.flagged_fragments, 1):
        print(f"\n  --- 片段 {i} [{f.tier}] {f.ai_ratio*100:.1f}%({f.char_count}字) ---")
        print(f"  所属章节: {f.section_name}")
        print(f"  文本（前200字）: {f.text[:200]}...")
