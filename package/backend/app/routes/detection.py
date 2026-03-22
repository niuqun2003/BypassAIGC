from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
from typing import Optional

from app.database import get_db
from app.models.models import User
from app.services.detection_service import detect_text
from datetime import datetime

router = APIRouter(prefix="/detection", tags=["detection"])


def get_current_user(card_key: str, db: Session = Depends(get_db)) -> User:
    user = db.query(User).filter(
        User.card_key == card_key,
        User.is_active.is_(True)
    ).first()
    if not user:
        raise HTTPException(status_code=401, detail="无效的卡密")
    user.last_used = datetime.utcnow()
    db.commit()
    return user


class DetectionRequest(BaseModel):
    text: str = Field(..., min_length=20, description="待检测文本，至少20字")
    use_llm: bool = Field(True, description="是否调用LLM打分（更准确，消耗少量API额度）")
    detect_model: Optional[str] = Field(None, description="覆盖检测用模型名")
    detect_api_key: Optional[str] = Field(None, description="覆盖检测用API Key")
    detect_base_url: Optional[str] = Field(None, description="覆盖检测用Base URL")


@router.post("/analyze")
async def analyze_aigc(
    card_key: str,
    data: DetectionRequest,
    db: Session = Depends(get_db),
):
    """
    AIGC 风险检测。

    - **Layer 1**：文体特征（突发度、词汇多样性、连接词密度、句式单一性、段落长度方差）
    - **Layer 2**：LLM 判分（Fast-DetectGPT 简化版，默认使用与润色相同的 API）

    返回文档级风险分、段落级分布、特征明细。
    """
    get_current_user(card_key, db)

    if len(data.text) < 20:
        raise HTTPException(status_code=400, detail="文本太短，无法检测（需至少20字）")

    result = await detect_text(
        text=data.text,
        use_llm=data.use_llm,
        detect_model=data.detect_model,
        detect_api_key=data.detect_api_key,
        detect_base_url=data.detect_base_url,
    )
    return result
