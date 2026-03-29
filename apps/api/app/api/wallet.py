from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models import WalletLedger
from app.schemas.wallet import WalletLedgerResponse, WalletResponse
from app.services.wallet import get_wallet_account

router = APIRouter()


@router.get("", response_model=WalletResponse)
def get_wallet(current_user=Depends(get_current_user), db: Session = Depends(get_db)):
    wallet = get_wallet_account(current_user.id, db)
    return WalletResponse(
        balance=wallet.balance,
        reserved_balance=wallet.reserved_balance,
        available_balance=wallet.balance - wallet.reserved_balance,
        currency=wallet.currency,
    )


@router.get("/ledger", response_model=list[WalletLedgerResponse])
def get_wallet_ledger(current_user=Depends(get_current_user), db: Session = Depends(get_db)):
    rows = (
        db.query(WalletLedger)
        .filter(WalletLedger.user_id == current_user.id)
        .order_by(WalletLedger.created_at.desc())
        .all()
    )
    return rows
