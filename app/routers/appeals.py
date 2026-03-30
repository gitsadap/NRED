from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.models import Appeal
from app.schemas import AppealCreate

router = APIRouter(prefix="/api/appeals", tags=["appeals"])

@router.post("/submit")
async def submit_appeal(appeal_data: AppealCreate, db: AsyncSession = Depends(get_db)):
    if not appeal_data.is_anonymous:
        if not appeal_data.sender_name or not appeal_data.email:
            raise HTTPException(status_code=400, detail="Name and Email are required unless anonymous.")
    
    new_appeal = Appeal(
        topic=appeal_data.topic,
        message=appeal_data.message,
        is_anonymous=1 if appeal_data.is_anonymous else 0, # SQLite uses 0/1 for bool
        sender_name=appeal_data.sender_name if not appeal_data.is_anonymous else None,
        email=appeal_data.email if not appeal_data.is_anonymous else None,
        status="pending"
    )
    
    db.add(new_appeal)
    await db.commit()
    await db.refresh(new_appeal)
    
    return {"success": True, "id": new_appeal.id}
