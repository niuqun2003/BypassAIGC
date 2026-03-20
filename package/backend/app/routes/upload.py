from io import BytesIO

from fastapi import APIRouter, File, HTTPException, UploadFile

router = APIRouter(prefix="/upload", tags=["upload"])

ALLOWED_EXTENSIONS = {".docx", ".pdf"}
MAX_FILE_SIZE = 10 * 1024 * 1024


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
