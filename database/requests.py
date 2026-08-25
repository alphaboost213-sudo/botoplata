from typing import List, Optional, Dict, Any
from sqlalchemy import select, update, delete, func
from database.engine import async_session
from database.models import User, Direction, Order, Settings

async def get_user(tg_id: int) -> Optional[User]:
    async with async_session() as session:
        return await session.scalar(select(User).where(User.tg_id == tg_id))

async def set_user(tg_id: int, username: Optional[str], referrer_id: int = None) -> User:
    async with async_session() as session:
        user = await session.scalar(select(User).where(User.tg_id == tg_id))
        if not user:
            user = User(tg_id=tg_id, username=username, referrer_id=referrer_id)
            session.add(user)
            await session.commit()
            await session.refresh(user)
        return user

async def get_referrals_count(tg_id: int) -> int:
    async with async_session() as session:
        count = await session.scalar(select(func.count(User.id)).where(User.referrer_id == tg_id))
        return count or 0

async def accept_user_tos(user_id: int):
    async with async_session() as session:
        await session.execute(update(User).where(User.tg_id == user_id).values(accepted_tos=True))
        await session.commit()

async def toggle_user_ban(tg_id: int, status: bool):
    async with async_session() as session:
        await session.execute(update(User).where(User.tg_id == tg_id).values(is_banned=status))
        await session.commit()

async def get_direction(dir_id: int) -> Optional[Direction]:
    async with async_session() as session:
        return await session.scalar(select(Direction).where(Direction.id == dir_id))

async def get_all_active_directions() -> List[Direction]:
    async with async_session() as session:
        res = await session.scalars(select(Direction).where(Direction.is_active == True))
        return list(res.all())

async def update_direction_setting(dir_id: int, key: str, value: Any):
    async with async_session() as session:
        await session.execute(update(Direction).where(Direction.id == dir_id).values({key: value}))
        await session.commit()

async def delete_direction(dir_id: int):
    """Полное удаление направления из базы данных"""
    async with async_session() as session:
        await session.execute(delete(Direction).where(Direction.id == dir_id))
        await session.commit()

async def add_new_direction(valute_from: str, type_from: str, valute_to: str, type_to: str, rate: float, min_amt: float, max_amt: float, reqs: str):
    async with async_session() as session:
        direction = Direction(
            valute_from=valute_from, type_from=type_from, 
            valute_to=valute_to, type_to=type_to, 
            rate=rate, min_amount=min_amt, max_amount=max_amt, 
            admin_requisites=reqs, is_active=True, is_auto_rate=False, margin_percent=0.0
        )
        session.add(direction)
        await session.commit()

async def get_latest_orders(limit: int = 5) -> List[Order]:
    async with async_session() as session:
        res = await session.scalars(select(Order).order_by(Order.id.desc()).limit(limit))
        return list(res.all())

async def get_order(order_id: int) -> Optional[Order]:
    async with async_session() as session:
        return await session.scalar(select(Order).where(Order.id == order_id))

async def create_order(user_id: int, dir_id: int, give: float, receive: float, rate: float, reqs: str, receipt: str) -> int:
    async with async_session() as session:
        order = Order(
            user_id=user_id, direction_id=dir_id, amount_give=give,
            amount_receive=receive, rate=rate, user_requisites=reqs, receipt_file_id=receipt, status="pending"
        )
        session.add(order)
        await session.commit()
        return order.id

async def update_order_status(order_id: int, status: str):
    async with async_session() as session:
        await session.execute(update(Order).where(Order.id == order_id).values(status=status))
        await session.commit()

async def get_project_stats() -> Dict[str, Any]:
    async with async_session() as session:
        users_count = await session.scalar(select(func.count(User.id)))
        orders_count = await session.scalar(select(func.count(Order.id)))
        volume_sum = await session.scalar(select(func.sum(Order.amount_receive)).where(Order.status == "completed")) or 0.0
        return {"users": users_count, "orders": orders_count, "volume": float(volume_sum)}

async def get_final_rate(direction_id: int) -> float:
    direction = await get_direction(direction_id)
    if not direction:
        return 0.0
        
    if direction.is_auto_rate:
        from utils.api_parser import get_actual_rate
        # Ищем криптовалюту для парсинга курса
        crypto_valute = direction.valute_from if direction.type_from == "crypto" else direction.valute_to
        base_rate = await get_actual_rate(crypto_valute)
        if base_rate > 0:
            final_rate = base_rate * (1 + (direction.margin_percent / 100))
            return round(final_rate, 2)
            
    return direction.rate

async def process_referral_reward(user_tg_id: int, order_amount: float, margin_percent: float):
    async with async_session() as session:
        user = await session.scalar(select(User).where(User.tg_id == user_tg_id))
        if user and user.referrer_id:
            ref_pct = await get_referral_percent() # Берем из БД
            reward = (order_amount * (margin_percent / 100)) * (ref_pct / 100)
            
            await session.execute(
                update(User)
                .where(User.tg_id == user.referrer_id)
                .values(balance=User.balance + reward)
            )
            await session.commit()

async def get_referral_percent() -> float:
    async with async_session() as session:
        # Пытаемся взять настройку из БД
        setting = await session.scalar(select(Settings).where(Settings.key == 'referral_percent'))
        return setting.value if setting else 10.0  # По умолчанию 10%

async def set_referral_percent(value: float):
    async with async_session() as session:
        setting = await session.scalar(select(Settings).where(Settings.key == 'referral_percent'))
        if setting:
            setting.value = value
        else:
            session.add(Settings(key='referral_percent', value=value))
        await session.commit()

async def toggle_user_kyc(tg_id: int) -> User:
    """Меняет статус is_verified на противоположный и возвращает обновленного юзера"""
    async with async_session() as session:
        user = await session.scalar(select(User).where(User.tg_id == tg_id))
        if user:
            new_status = not user.is_verified
            await session.execute(
                update(User)
                .where(User.tg_id == tg_id)
                .values(is_verified=new_status)
            )
            await session.commit()
            
            # Обновляем объект, чтобы сразу отдать его с новыми данными
            user.is_verified = new_status
            return user

def format_amount(amount: float, currency: str, currency_type: str) -> str:
    """Динамическое форматирование: фиат 2 знака, крипта до 6 знаков"""
    if currency_type == "fiat":
        return f"{amount:,.2f} {currency}"
    else:
        formatted = f"{amount:.6f}".rstrip('0').rstrip('.')
        if formatted == "": formatted = "0"
        return f"{formatted} {currency}"

async def seed_default_directions():
    pass