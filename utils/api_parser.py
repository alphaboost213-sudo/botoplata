import aiohttp
import logging
import asyncio
import time

CG_MAPPING = {
    "BTC": "bitcoin", "ETH": "ethereum", "USDT": "tether", "TON": "the-open-network",
    "SOL": "solana", "BNB": "binancecoin", "XRP": "ripple", "DOGE": "dogecoin",
    "ADA": "cardano", "TRX": "tron", "AVAX": "avalanche-2", "DOT": "polkadot",
    "LINK": "chainlink", "MATIC": "matic-network", "LTC": "litecoin", "BCH": "bitcoin-cash",
    "SHIB": "shiba-inu", "UNI": "uniswap", "ATOM": "cosmos", "XLM": "stellar",
    "DAI": "dai", "ETC": "ethereum-classic", "NEAR": "near", "FIL": "filecoin",
    "ARB": "arbitrum", "APT": "aptos", "LDO": "lido-dao", "PEPE": "pepe",
    "SUI": "sui", "XMR": "monero"
}

# Кэш для цен
_price_cache = {ticker: 0.0 for ticker in CG_MAPPING.keys()}
_last_update = 0

async def update_all_prices():
    """Обновляет все цены разом, чтобы не слать запросы на каждую монету отдельно."""
    global _price_cache, _last_update
    
    ids = ",".join(CG_MAPPING.values())
    url = f"https://api.coingecko.com/api/v3/simple/price?ids={ids}&vs_currencies=rub"
    
    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        async with aiohttp.ClientSession(headers=headers) as session:
            async with session.get(url, timeout=15) as response:
                if response.status == 200:
                    data = await response.json()
                    for ticker, coin_id in CG_MAPPING.items():
                        price = data.get(coin_id, {}).get("rub", 0.0)
                        if price > 0:
                            _price_cache[ticker] = float(price)
                    _last_update = time.time()
                    return True
    except Exception as e:
        logging.error(f"Ошибка массового обновления цен: {e}")
    return False

async def get_price_in_rub(crypto: str) -> float:
    global _last_update
    ticker = crypto.upper().strip()
    
    # Обновляем кэш, если прошло больше 5 минут (300 сек)
    if time.time() - _last_update > 300 or _price_cache.get(ticker, 0) == 0:
        await update_all_prices()
        
    return _price_cache.get(ticker, 0.0)

async def get_exchange_rate(valute_from: str, valute_to: str) -> float:
    price_from = await get_price_in_rub(valute_from)
    price_to = await get_price_in_rub(valute_to)
    
    if price_from <= 0 or price_to <= 0:
        logging.error(f"Не удалось получить курс: {valute_from}={price_from}, {valute_to}={price_to}")
        return 0.0
    
    return price_from / price_to

get_actual_rate = get_price_in_rub