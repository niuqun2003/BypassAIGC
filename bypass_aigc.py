#!/usr/bin/env python3
"""
bypass_aigc.py — BypassAIGC 命令行调用工具

用法：
    # 改写文本（从文件读取）
    python bypass_aigc.py rewrite --input 原文.txt --output 改写结果.txt

    # 改写文本（从 stdin 读取，结果输出到 stdout）
    echo "需要改写的文本" | python bypass_aigc.py rewrite

    # 仅做 AIGC 检测
    python bypass_aigc.py detect --input 文章.txt

    # 先检测，再改写，再检测（完整流程）
    python bypass_aigc.py pipeline --input 原文.txt --output 改写结果.txt

环境变量（优先级高于命令行参数）：
    BYPASS_API_URL   服务地址，默认 http://localhost:8000
    BYPASS_CARD_KEY  卡密
"""

import argparse
import json
import sys
import time
import os
import textwrap
from typing import Optional

try:
    import requests
except ImportError:
    print("缺少依赖：pip install requests", file=sys.stderr)
    sys.exit(1)

# ─────────────────────────────────────────────────────────────
# 默认配置
# ─────────────────────────────────────────────────────────────
DEFAULT_API_URL = "http://localhost:8000"
DEFAULT_CARD_KEY = ""
POLL_INTERVAL = 3      # 轮询间隔（秒）
POLL_TIMEOUT = 600     # 最长等待时间（秒）


# ─────────────────────────────────────────────────────────────
# API 客户端
# ─────────────────────────────────────────────────────────────

class BypassClient:
    def __init__(self, api_url: str, card_key: str):
        self.api_url = api_url.rstrip("/")
        self.card_key = card_key
        self.session = requests.Session()

    def _url(self, path: str) -> str:
        return f"{self.api_url}{path}"

    def _params(self, extra: dict = None) -> dict:
        p = {"card_key": self.card_key}
        if extra:
            p.update(extra)
        return p

    # ── 检测 ──────────────────────────────────────────────────

    def detect(self, text: str, use_llm: bool = True, use_curvature: bool = True) -> dict:
        """调用 AIGC 检测接口，直接返回检测报告。"""
        resp = self.session.post(
            self._url("/api/detection/analyze"),
            params=self._params(),
            json={
                "text": text,
                "use_llm": use_llm,
                "use_curvature": use_curvature,
            },
            timeout=120,
        )
        resp.raise_for_status()
        return resp.json()

    # ── 改写 ──────────────────────────────────────────────────

    def start_optimization(self, text: str, mode: str = "paper_polish_enhance") -> str:
        """提交改写任务，返回 session_id。"""
        resp = self.session.post(
            self._url("/api/optimization/start"),
            params=self._params(),
            json={"original_text": text, "processing_mode": mode},
            timeout=30,
        )
        resp.raise_for_status()
        return resp.json()["session_id"]

    def poll_until_done(self, session_id: str, verbose: bool = True) -> dict:
        """轮询进度，直到完成或失败，返回最终进度对象。"""
        deadline = time.time() + POLL_TIMEOUT
        while time.time() < deadline:
            resp = self.session.get(
                self._url(f"/api/optimization/sessions/{session_id}/progress"),
                params=self._params(),
                timeout=30,
            )
            resp.raise_for_status()
            progress = resp.json()
            status = progress["status"]

            if verbose:
                pct = min(100, int(progress.get("progress", 0) * 100))
                stage = progress.get("current_stage", "")
                pos = progress.get("current_position", 0)
                total = progress.get("total_segments", 0)
                print(
                    f"\r  [{status}] {pct:3d}%  阶段:{stage}  段落:{pos}/{total}   ",
                    end="",
                    flush=True,
                    file=sys.stderr,
                )

            if status == "completed":
                if verbose:
                    print(file=sys.stderr)
                return progress
            if status in ("failed", "stopped"):
                if verbose:
                    print(file=sys.stderr)
                raise RuntimeError(
                    f"任务{status}：{progress.get('error_message', '未知错误')}"
                )

            time.sleep(POLL_INTERVAL)

        raise TimeoutError(f"等待超时（{POLL_TIMEOUT}s），session_id={session_id}")

    def get_result_text(self, session_id: str) -> str:
        """取会话详情，拼接最终改写文本。"""
        resp = self.session.get(
            self._url(f"/api/optimization/sessions/{session_id}"),
            params=self._params(),
            timeout=30,
        )
        resp.raise_for_status()
        detail = resp.json()
        segments = sorted(detail.get("segments", []), key=lambda s: s["segment_index"])
        parts = []
        for seg in segments:
            text = (
                seg.get("user_edited_text")
                or seg.get("enhanced_text")
                or seg.get("polished_text")
                or seg.get("original_text")
                or ""
            )
            parts.append(text)
        return "\n\n".join(parts)

    # ── 便捷组合 ──────────────────────────────────────────────

    def rewrite(self, text: str, mode: str = "paper_polish_enhance", verbose: bool = True) -> str:
        """提交 → 轮询 → 返回改写后文本（异步模式，阻塞直到完成）。"""
        if verbose:
            print("⏳ 提交改写任务...", file=sys.stderr)
        session_id = self.start_optimization(text, mode)
        if verbose:
            print(f"   session_id: {session_id}", file=sys.stderr)
            print("⏳ 等待处理完成...", file=sys.stderr)
        self.poll_until_done(session_id, verbose=verbose)
        result = self.get_result_text(session_id)
        if verbose:
            print("✅ 改写完成", file=sys.stderr)
        return result

    def rewrite_sync(
        self,
        text: str,
        mode: str = "paper_polish_enhance",
        timeout: int = 300,
        verbose: bool = True,
    ) -> str:
        """同步改写 — 单次 HTTP 请求，服务端阻塞直到完成再返回。

        适合文本较短或网络超时宽松的场景，比异步模式少一次轮询开销。
        """
        if verbose:
            print("⏳ 同步改写中（等待服务端完成）...", file=sys.stderr)
        resp = self.session.post(
            self._url("/api/optimization/sync"),
            params=self._params(),
            json={"original_text": text, "processing_mode": mode, "timeout": timeout},
            timeout=timeout + 30,  # HTTP 超时略大于服务端超时
        )
        resp.raise_for_status()
        data = resp.json()
        if verbose:
            ms = data.get("processing_time_ms", 0)
            segs = data.get("total_segments", 0)
            print(f"✅ 同步改写完成（{ms}ms，{segs}段）", file=sys.stderr)
        return data["text"]


# ─────────────────────────────────────────────────────────────
# 输出格式化
# ─────────────────────────────────────────────────────────────

def format_detection_report(report: dict) -> str:
    """将检测报告格式化为可读文本。"""
    lines = []
    score = report.get("document_score", "N/A")
    tier_cn = report.get("document_tier_cn", "")
    confidence = report.get("confidence", "")
    meta = report.get("report_metadata", {})

    lines.append("=" * 60)
    lines.append(f"AIGC 检测报告")
    lines.append("=" * 60)
    lines.append(f"文档风险分：{score}/100  【{tier_cn}】  置信度：{confidence}")
    lines.append(
        f"字符数：{meta.get('char_count', 0)}  "
        f"标记字符：{meta.get('flagged_char_count', 0)}  "
        f"LLM判分：{'是' if meta.get('llm_used') else '否'}  "
        f"耗时：{meta.get('processing_time_ms', 0)}ms"
    )

    sections = report.get("sections", [])
    if sections:
        lines.append("\n── 章节分布 ──")
        for s in sections:
            lines.append(
                f"  [{s.get('tier_cn',''):^6}] {s.get('score','?'):>3}分  "
                f"{s.get('title','')[:30]}  ({s.get('char_count',0)}字)"
            )

    explanations = report.get("explanations", [])
    if explanations:
        lines.append("\n── 触发信号 ──")
        for e in explanations:
            lines.append(f"  · {e.get('label','')}: {e.get('summary','')}")

    fragments = report.get("fragments", [])
    flagged = [f for f in fragments if f.get("tier") != "unmarked"]
    if flagged:
        lines.append(f"\n── 高风险片段（共 {len(flagged)} 处）──")
        for f in flagged[:5]:
            preview = f.get("text", "")[:60].replace("\n", " ")
            lines.append(f"  [{f.get('score',0):3d}分] {preview}...")
        if len(flagged) > 5:
            lines.append(f"  ... 还有 {len(flagged)-5} 处（省略）")

    lines.append("=" * 60)
    return "\n".join(lines)


# ─────────────────────────────────────────────────────────────
# CLI 入口
# ─────────────────────────────────────────────────────────────

def read_input(input_file: Optional[str]) -> str:
    if input_file:
        with open(input_file, "r", encoding="utf-8") as f:
            return f.read()
    if not sys.stdin.isatty():
        return sys.stdin.read()
    print("错误：请通过 --input 指定文件，或从 stdin 输入文本", file=sys.stderr)
    sys.exit(1)


def write_output(text: str, output_file: Optional[str]):
    if output_file:
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(text)
        print(f"📄 结果已写入：{output_file}", file=sys.stderr)
    else:
        print(text)


def build_client(args) -> BypassClient:
    api_url = os.environ.get("BYPASS_API_URL") or args.api_url
    card_key = os.environ.get("BYPASS_CARD_KEY") or args.card_key
    if not card_key:
        print("错误：请通过 --card-key 或环境变量 BYPASS_CARD_KEY 提供卡密", file=sys.stderr)
        sys.exit(1)
    return BypassClient(api_url, card_key)


def cmd_detect(args):
    client = build_client(args)
    text = read_input(args.input)
    print("⏳ 正在检测...", file=sys.stderr)
    report = client.detect(text, use_llm=not args.no_llm, use_curvature=not args.no_curvature)
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print(format_detection_report(report))


def cmd_rewrite(args):
    client = build_client(args)
    text = read_input(args.input)
    if args.sync:
        result = client.rewrite_sync(text, mode=args.mode, timeout=args.timeout, verbose=not args.quiet)
    else:
        result = client.rewrite(text, mode=args.mode, verbose=not args.quiet)
    write_output(result, args.output)


def cmd_pipeline(args):
    """检测 → 改写 → 再检测"""
    client = build_client(args)
    text = read_input(args.input)

    print("\n📊 第一步：检测原文", file=sys.stderr)
    before = client.detect(text, use_llm=not args.no_llm)
    print(format_detection_report(before), file=sys.stderr)

    print("\n✏️  第二步：改写", file=sys.stderr)
    rewritten = client.rewrite(text, mode=args.mode, verbose=True)
    write_output(rewritten, args.output)

    print("\n📊 第三步：检测改写结果", file=sys.stderr)
    after = client.detect(rewritten, use_llm=not args.no_llm)
    print(format_detection_report(after), file=sys.stderr)

    before_score = before.get("document_score", "?")
    after_score = after.get("document_score", "?")
    print(f"\n🎯 风险分变化：{before_score} → {after_score}", file=sys.stderr)


def main():
    parser = argparse.ArgumentParser(
        description="BypassAIGC 命令行工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=textwrap.dedent("""
            示例：
              python bypass_aigc.py rewrite --input 原文.txt --output 结果.txt --card-key 123
              python bypass_aigc.py detect --input 文章.txt --card-key 123
              python bypass_aigc.py pipeline --input 原文.txt --output 结果.txt --card-key 123

              # 使用测试环境
              python bypass_aigc.py rewrite --input 原文.txt --api-url http://localhost:8100 --card-key 123

              # 通过环境变量配置
              export BYPASS_API_URL=http://localhost:8000
              export BYPASS_CARD_KEY=123
              python bypass_aigc.py rewrite --input 原文.txt
        """),
    )
    parser.add_argument("--api-url", default=DEFAULT_API_URL, help="服务地址")
    parser.add_argument("--card-key", default=DEFAULT_CARD_KEY, help="卡密")

    sub = parser.add_subparsers(dest="command", required=True)

    # detect
    p_detect = sub.add_parser("detect", help="AIGC 检测")
    p_detect.add_argument("--input", "-i", help="输入文件路径（不填则读 stdin）")
    p_detect.add_argument("--no-llm", action="store_true", help="跳过 LLM 判分（更快）")
    p_detect.add_argument("--no-curvature", action="store_true", help="跳过曲率检测")
    p_detect.add_argument("--json", action="store_true", help="输出原始 JSON")
    p_detect.set_defaults(func=cmd_detect)

    # rewrite
    p_rewrite = sub.add_parser("rewrite", help="改写文本（降低 AIGC 率）")
    p_rewrite.add_argument("--input", "-i", help="输入文件路径（不填则读 stdin）")
    p_rewrite.add_argument("--output", "-o", help="输出文件路径（不填则输出到 stdout）")
    p_rewrite.add_argument(
        "--mode",
        default="paper_polish_enhance",
        choices=["paper_polish", "paper_polish_enhance", "emotion_polish"],
        help="处理模式（默认 paper_polish_enhance）",
    )
    p_rewrite.add_argument("--sync", action="store_true", help="使用同步接口（单次请求，适合短文本）")
    p_rewrite.add_argument("--timeout", type=int, default=300, help="同步模式超时秒数（默认300）")
    p_rewrite.add_argument("--quiet", "-q", action="store_true", help="不显示进度")
    p_rewrite.set_defaults(func=cmd_rewrite)

    # pipeline
    p_pipe = sub.add_parser("pipeline", help="完整流程：检测 → 改写 → 再检测")
    p_pipe.add_argument("--input", "-i", help="输入文件路径（不填则读 stdin）")
    p_pipe.add_argument("--output", "-o", help="改写结果输出路径")
    p_pipe.add_argument(
        "--mode",
        default="paper_polish_enhance",
        choices=["paper_polish", "paper_polish_enhance", "emotion_polish"],
    )
    p_pipe.add_argument("--no-llm", action="store_true", help="检测时跳过 LLM 判分")
    p_pipe.set_defaults(func=cmd_pipeline)

    args = parser.parse_args()

    try:
        args.func(args)
    except KeyboardInterrupt:
        print("\n已中断", file=sys.stderr)
        sys.exit(130)
    except requests.HTTPError as e:
        print(f"HTTP 错误：{e.response.status_code} {e.response.text}", file=sys.stderr)
        sys.exit(1)
    except (RuntimeError, TimeoutError) as e:
        print(f"错误：{e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
