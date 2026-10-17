"""Orders. The mock provider is the default; Razorpay test mode lands on Day 3.

Download gating itself lives in routers/projects.py and reads the `paid` status
written here. No real money moves through this app.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, select

import auth
import schemas
from db import get_session
from models import Order, Project, User
from services import payments

router = APIRouter(prefix="/orders", tags=["orders"])


def _provider():
    try:
        return payments.get_provider()
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


def to_read(order: Order, project_title: str) -> schemas.OrderRead:
    return schemas.OrderRead(
        **order.model_dump(),
        project_title=project_title,
    )


def _title_for(session: Session, project_id: int) -> str:
    project = session.get(Project, project_id)
    return project.title if project else ""


@router.post("", response_model=schemas.OrderRead, status_code=status.HTTP_201_CREATED)
def create_order(
    payload: schemas.OrderCreate,
    user: User = Depends(auth.get_current_user),
    session: Session = Depends(get_session),
) -> schemas.OrderRead:
    project = session.get(Project, payload.project_id)
    if project is None or project.status != "published":
        raise HTTPException(status_code=404, detail="project not found")
    if project.seller_id == user.id:
        raise HTTPException(status_code=400, detail="this is your own project")

    already = session.exec(
        select(Order).where(
            Order.project_id == project.id,
            Order.buyer_id == user.id,
            Order.status == "paid",
        )
    ).first()
    if already is not None:
        raise HTTPException(status_code=400, detail="you already bought this project")

    provider = _provider()
    order = Order(
        project_id=project.id,
        buyer_id=user.id,
        amount_inr=project.price_inr,
        provider=provider.name,
        status="pending",
    )
    session.add(order)
    session.commit()
    session.refresh(order)

    result = provider.create_payment(order_id=order.id, amount_inr=order.amount_inr)
    if result.status == "failed":
        order.status = "failed"
    order.provider_ref = result.provider_ref
    session.add(order)
    session.commit()
    session.refresh(order)
    return to_read(order, project.title)


@router.post("/{order_id}/confirm", response_model=schemas.OrderRead)
def confirm_order(
    order_id: int,
    user: User = Depends(auth.get_current_user),
    session: Session = Depends(get_session),
) -> schemas.OrderRead:
    order = session.get(Order, order_id)
    if order is None:
        raise HTTPException(status_code=404, detail="order not found")
    if order.buyer_id != user.id:
        raise HTTPException(status_code=403, detail="this order belongs to another buyer")
    if order.status == "paid":
        return to_read(order, _title_for(session, order.project_id))

    result = _provider().confirm_payment(provider_ref=order.provider_ref or "")
    order.status = result.status
    order.provider_ref = result.provider_ref
    session.add(order)
    session.commit()
    session.refresh(order)
    return to_read(order, _title_for(session, order.project_id))


@router.get("/me", response_model=list[schemas.OrderRead])
def my_orders(
    user: User = Depends(auth.get_current_user),
    session: Session = Depends(get_session),
) -> list[schemas.OrderRead]:
    orders = session.exec(
        select(Order).where(Order.buyer_id == user.id).order_by(Order.created_at.desc())
    ).all()
    return [to_read(order, _title_for(session, order.project_id)) for order in orders]
