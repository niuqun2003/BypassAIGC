from io import BytesIO

from fastapi import APIRouter, File, HTTPException, UploadFile

router = APIRouter(prefix="/upload", tags=["upload"])

ALLOWED_EXTENSIONS = {".docx", ".pdf"}
MAX_FILE_SIZE = 10 * 1024 * 1024
MAX_REPORT_SIZE = 20 * 1024 * 1024  # CNKI 报告 PDF 可能较大


@router.post("/extract-text")
async def extract_text(file: UploadFile = File(...)):
    """从上传的 Word/PDF 文件中提取纯文本"""
    filename = file.filename or ""
    ext = ""
    if "." in filename:
        ext = "." + filename.rsplit(".", 1)[1].lower()

    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"不支持的文件类型 '{ext}'，仅支持 .docx 和 .pdf",
        )

    content = await file.read()
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=400,
            detail=f"文件过大（最大 {MAX_FILE_SIZE // 1024 // 1024}MB）",
        )

    try:
        if ext == ".docx":
            text = _extract_docx(content)
        else:
            text = _extract_pdf(content)
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=422,
            detail=f"文件解析失败：{str(exc)[:200]}",
        )

    if not text.strip():
        raise HTTPException(status_code=422, detail="未能从文件中提取到任何文本")

    return {"text": text, "filename": filename, "char_count": len(text)}


def _extract_docx(content: bytes) -> str:
    from docx import Document

    document = Document(BytesIO(content))
    paragraphs = [paragraph.text for paragraph in document.paragraphs if paragraph.text.strip()]
    return "\n\n".join(paragraphs)


def _extract_pdf(content: bytes) -> str:
    import pdfplumber

    paragraphs = []
    with pdfplumber.open(BytesIO(content)) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text()
            if page_text and page_text.strip():
                paragraphs.append(page_text.strip())
    return "\n\n".join(paragraphs)


@router.post("/cnki-report")
async def parse_cnki_report(file: UploadFile = File(...)):
    """
    解析知网 AIGC 检测报告 PDF。
    返回报告元数据、各章节风险统计、以及标色的高风险文本片段。
    """
    filename = file.filename or ""
    if not filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="仅支持 PDF 格式的知网检测报告")

    content = await file.read()
    if len(content) > MAX_REPORT_SIZE:
        raise HTTPException(
            status_code=400,
            detail=f"文件过大（最大 {MAX_REPORT_SIZE // 1024 // 1024}MB）",
        )

    try:
        from app.services.cnki_report_parser import parse_cnki_report as _parse
        report = _parse(content)
    except Exception as exc:
        raise HTTPException(
            status_code=422,
            detail=f"报告解析失败：{str(exc)[:300]}",
        )

    # 将 dataclass 转为可序列化的 dict
    sections_out = [
        {
            "index": s.index,
            "name": s.name,
            "ai_ratio": s.ai_ratio,
            "char_count": s.char_count,
        }
        for s in report.sections
    ]
    fragments_out = [
        {
            "tier": f.tier,
            "ai_ratio": f.ai_ratio,
            "char_count": f.char_count,
            "text": f.text,
            "page": f.page,
        }
        for f in report.flagged_fragments
    ]

    return {
        "metadata": {
            "report_no": report.metadata.report_no,
            "detection_time": report.metadata.detection_time,
            "title": report.metadata.title,
            "author": report.metadata.author,
        },
        "summary": {
            "total_chars": report.summary.total_chars,
            "ai_chars": report.summary.ai_chars,
            "ai_ratio": report.summary.ai_ratio,
            "significant_ratio": report.summary.significant_ratio,
            "suspected_ratio": report.summary.suspected_ratio,
        },
        "sections": sections_out,
        "flagged_fragments": fragments_out,
        "filename": filename,
    }
