import requests
import json 
from dotenv import load_dotenv
import os

load_dotenv("local.env")

WALLET_ADDRESS = os.getenv("GUARANTOR_WALLET")
MAINNET_API_BASE = "https://toncenter.com/api/v2/"

def detect_address(buyer_wallet):
    url = f"{MAINNET_API_BASE}detectAddress?address={buyer_wallet}"
    r = requests.get(url)
    response = json.loads(r.text)
    try:
        return response['result']['bounceable']['b64url']
    except:
        return False

def get_address_transactions():
    url = f"{MAINNET_API_BASE}getTransactions?address={WALLET_ADDRESS}&limit=30&to_lt=0&archival=true"
    r = requests.get(url)
    response = json.loads(r.text)
    return response['result']

def find_transaction(buyer_wallet, deal_comment):
    detected_address = detect_address(buyer_wallet)
    print("DETECTED:", repr(detected_address))
    print("COMMENT:", repr(deal_comment))
    
    transactions = get_address_transactions()
    for transaction in transactions:
        msg = transaction['in_msg']
        print("SOURCE:", repr(msg['source']))
        print("MESSAGE:", repr(msg['message']))

        if str(msg['source']).strip() == str(detected_address).strip() and \
           str(msg['message']).strip() == str(deal_comment).strip():
            print("✅ Transaction found!")
            print(
                f"From: {msg['source']} \nValue: {msg['value']} \nComment: {msg['message']}")
            return True
        else:
            print("⛔ No match")
    return False


if __name__ == "__main__":
    find_transaction()