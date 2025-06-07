import asyncio
from tonutils.client import ToncenterV3Client
from tonutils.wallet import WalletV5R1
import os
from dotenv import load_dotenv

load_dotenv("local.env")

IS_TESTNET = False  # True — тестнет, False — мейннет
FIXED_MNEMONIC = os.getenv("WALLET_MNEMONIC")

async def send_from_fixed_wallet(address: str, amount: float, deal_code: str) -> str:
    client = ToncenterV3Client(is_testnet=IS_TESTNET, rps=1, max_retries=1)
    wallet, _, _, _ = WalletV5R1.from_mnemonic(client, FIXED_MNEMONIC)

    comment = f"Сделка {deal_code} завершена!"

    tx_hash = await wallet.transfer(
        destination=address,
        amount=amount,
        body=comment,
    )

    print("✅ Отправлено! Tx Hash:", tx_hash)
    await client.close()
    return tx_hash

def send_ton(to_address: str, amount: float, comment: str) -> str:
    return asyncio.run(send_from_fixed_wallet(to_address, amount, comment))