from __future__ import annotations

from fastapi import APIRouter, Depends, Request, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.limiter import limiter
from app.models import ContactSubmission
from app.schemas import ContactRequest, ContactResponse

router = APIRouter(prefix="/api/contact", tags=["contact"])


@router.post(
    "",
    response_model=ContactResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Submit a contact enquiry",
)
@limiter.limit("5/hour")
def submit_contact(
    request: Request,
    payload: ContactRequest,
    db: Session = Depends(get_db),
):
    submission = ContactSubmission(
        first_name=payload.first_name,
        last_name=payload.last_name,
        email=payload.email,
        subject=payload.subject,
        message=payload.message,
        ip_address=request.client.host if request.client else None,
    )
    db.add(submission)
    db.commit()
    return ContactResponse(message="Thanks for reaching out! We'll be in touch within one business day.")
