from __future__ import annotations
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Subscriber, User
from app.routers.auth import get_current_user
from app.schemas import (
    SubscribeRequest,
    SubscribeResponse,
    SubscriberRecord,
    UnsubscribeRequest,
)

router = APIRouter(prefix="/api/newsletter", tags=["newsletter"])


@router.post(
    "/subscribe",
    response_model=SubscribeResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Subscribe to the newsletter",
)
def subscribe(payload: SubscribeRequest, request: Request, db: Session = Depends(get_db)):
    """
    Add a new subscriber. Returns 409 if the email is already active.
    Re-activates the subscription if the email previously unsubscribed.
    """
    existing = db.query(Subscriber).filter(Subscriber.email == payload.email).first()

    if existing:
        if existing.is_active:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="This email is already subscribed.",
            )
        # Re-subscribe if they had previously unsubscribed.
        existing.is_active = True
        existing.first_name = payload.first_name
        existing.last_name = payload.last_name
        existing.role = payload.role
        existing.interests = payload.interests
        db.commit()
        return SubscribeResponse(message="Welcome back! You've been re-subscribed.", email=existing.email)

    subscriber = Subscriber(
        email=payload.email,
        first_name=payload.first_name,
        last_name=payload.last_name,
        role=payload.role,
        interests=payload.interests,
        ip_address=request.client.host if request.client else None,
    )

    try:
        db.add(subscriber)
        db.commit()
        db.refresh(subscriber)
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This email is already subscribed.",
        )

    return SubscribeResponse(message="Thanks for subscribing!", email=subscriber.email)


@router.post(
    "/unsubscribe",
    response_model=SubscribeResponse,
    summary="Unsubscribe from the newsletter",
)
def unsubscribe(payload: UnsubscribeRequest, db: Session = Depends(get_db)):
    """Soft-delete: marks the subscriber inactive rather than deleting the row."""
    subscriber = db.query(Subscriber).filter(Subscriber.email == payload.email).first()

    if not subscriber or not subscriber.is_active:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No active subscription found for this email.",
        )

    subscriber.is_active = False
    db.commit()

    return SubscribeResponse(message="You've been unsubscribed successfully.", email=subscriber.email)


@router.get(
    "/subscribers",
    response_model=list[SubscriberRecord],
    summary="List all active subscribers (admin use)",
)
def list_subscribers(active_only: bool = True, db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    """
    Returns subscriber records. Intended for internal/admin use only.
    Secure this endpoint with authentication before exposing it publicly.
    """
    query = db.query(Subscriber)
    if active_only:
        query = query.filter(Subscriber.is_active == True)  # noqa: E712
    return query.order_by(Subscriber.subscribed_at.desc()).all()
