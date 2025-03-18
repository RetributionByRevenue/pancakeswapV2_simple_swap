import time
import web3
from web3 import Web3
from web3.middleware import geth_poa_middleware

from decimal import Decimal
import requests
from typing import Dict, List, Optional
from datetime import datetime, timedelta
import os
from dataclasses import dataclass

@dataclass
class Contract:
    symbol: str
    address: str
    decimals: int

    def __init__(self, symbol: str, address: str, decimals: int):
        self.symbol = symbol
        self.address = Web3.to_checksum_address(address)
        self.decimals = decimals


class Pancake:
    abi_cache: Dict[str, Dict] = {}

    def __init__(self, address_wallet: str, private_key: str, base_token: Contract, desired_token: Contract, slippage: Decimal = Decimal("0.005")):
        """
        Initialize Pancakeswap trading interface
        
        Args:
            address_wallet: Your wallet address
            private_key: Your private key
            base_token: Token to swap from
            desired_token: Token to swap to
            slippage: Allowed slippage as a decimal (default 0.005 = 0.5%)
        """
        self.wallet: str = Web3.to_checksum_address(address_wallet)
        self.private_key = private_key
        self.client = web3.Web3(web3.HTTPProvider("https://bsc-dataseed1.binance.org"))
        self.client.middleware_onion.inject(geth_poa_middleware, layer=0)
        self.base_token = base_token
        self.desired_token = desired_token
        self.pancakeswap = Contract("Routerv2", "0x10ED43C718714eb63d5aA57B78B54704E256024E", 18)
        self.slippage = slippage  # User-defined slippage tolerance

    def fetch_abi(self, address: str):
        address = Web3.to_checksum_address(address)
        if address not in Pancake.abi_cache:
            url = "https://api.bscscan.com/api"
            params = {
                "module": "contract",
                "action": "getabi",
                "address": address,
                "apikey": "6HQZV977GIY8FNT36XN1JJSE12IP2IYVTQ",
            }
            resp = requests.get(url, params=params).json()
            Pancake.abi_cache[address] = resp["result"]
        return Pancake.abi_cache[address]

    def get_contract(self, contract: Contract):
        abi_contract = self.fetch_abi(contract.address)
        return self.client.eth.contract(address=contract.address, abi=abi_contract)

    def bep20_balance(self, token: Contract) -> Decimal:
        contract = self.get_contract(token)
        balance = contract.functions.balanceOf(self.wallet).call()
        return Decimal(balance) / (10 ** token.decimals)

    def send_transaction(self, txn):
        # Get current gas price
        gas_price = self.client.eth.gas_price
        gas_price_gwei = self.client.from_wei(gas_price, 'gwei')
        print(f"Current gas price: {gas_price_gwei:.2f} Gwei")
        
        # Build transaction with standard parameters
        txn = txn.build_transaction({
            "chainId": self.client.eth.chain_id,
            "from": self.wallet,
            "nonce": self.client.eth.get_transaction_count(self.wallet),
            "gasPrice": gas_price
        })
        
        # Display estimated gas cost
        gas_cost_wei = txn.get('gas', 500000) * gas_price
        gas_cost_bnb = self.client.from_wei(gas_cost_wei, 'ether')
        print(f"Estimated gas cost: {gas_cost_bnb:.6f} BNB")
        
        # Sign and send transaction
        signed_txn = self.client.eth.account.sign_transaction(txn, self.private_key)
        txn_hash = self.client.eth.send_raw_transaction(signed_txn.raw_transaction)
        txn_hash_hex = self.client.to_hex(txn_hash)
        print(f"Transaction sent: {txn_hash_hex}")
        
        txn_receipt = self.client.eth.wait_for_transaction_receipt(txn_hash)
        print(f"Transaction confirmed: Block #{txn_receipt['blockNumber']}")
        return txn_receipt

    def approve_token(self, token: Contract):
        contract = self.get_contract(token)
        approve_amount = 2 ** 256 - 1
        amount = contract.functions.allowance(self.wallet, self.pancakeswap.address).call()
        if amount >= approve_amount / 2:
            print(f"{token.symbol} already approved.")
            return None
            
        print(f"Approving {token.symbol} for trading on PancakeSwap...")
        txn = contract.functions.approve(self.pancakeswap.address, approve_amount)
        return self.send_transaction(txn)

    def swap_token(self, amount_in: Decimal):
        """
        Swap from base token to desired token using the amount specified
        with custom slippage tolerance
        
        Args:
            amount_in: Amount of base token to swap
        """
        base_token = self.base_token
        desired_token = self.desired_token
        
        print(f"Starting swap from {base_token.symbol} to {desired_token.symbol}...")
        print(f"Using slippage tolerance: {self.slippage * 100}%")

        # Approve base token if not already approved
        print(f"Checking approval for {base_token.symbol} to PancakeSwap...")
        self.approve_token(base_token)
        print(f"Approval confirmed for {base_token.symbol}.")

        contract = self.get_contract(self.pancakeswap)
        print(f"Using PancakeSwap router at {self.pancakeswap.address}")

        path = [base_token.address, desired_token.address]
        print(f"Swap path: {base_token.symbol} -> {desired_token.symbol}")

        amount_in_wei = int(amount_in * 10 ** base_token.decimals)
        print(f"Input amount: {amount_in} {base_token.symbol} ({amount_in_wei} wei)")

        # Get expected output amount
        amounts_out = contract.functions.getAmountsOut(amount_in_wei, path).call()
        expected_out = Decimal(amounts_out[1]) / (10 ** desired_token.decimals)
        print(f"Expected output: {expected_out} {desired_token.symbol}")

        # Calculate minimum output with slippage
        pancake_fee = Decimal("0.0025")  # 0.25% PancakeSwap fee
        minimum_out = int(amounts_out[1] * (1 - self.slippage - pancake_fee))
        expected_min_out = Decimal(minimum_out) / (10 ** desired_token.decimals)
        print(f"Minimum output after slippage: {expected_min_out} {desired_token.symbol}")

        deadline = datetime.now() + timedelta(minutes=5)
        print(f"Transaction deadline: {deadline.strftime('%Y-%m-%d %H:%M:%S')}")

        # Ask for confirmation
        confirm = input(f"\nConfirm swap {amount_in} {base_token.symbol} for ~{expected_out} {desired_token.symbol}? (yes/no): ")
        if confirm.lower() != "yes":
            print("Swap cancelled.")
            return None

        # Create swap transaction
        txn = contract.functions.swapExactTokensForTokens(
            amount_in_wei, minimum_out, path, self.wallet, int(deadline.timestamp())
        )
        
        print("Sending transaction...")
        txn_receipt = self.send_transaction(txn)
        
        # Calculate actual received amount after swap
        new_balance = self.bep20_balance(desired_token)
        remaining_balance = self.bep20_balance(base_token)
        print(f"\nSwap completed!")
        print(f"New {desired_token.symbol} balance: {new_balance}")
        print(f"Remaining {base_token.symbol} balance: {remaining_balance}")
        
        return txn_receipt


def main():
    address_wallet = "put in your public key"
    private_key = "put in your private key"
    

    # Define tokens
    '''
    Contract("BUSD", "0xe9e7CEA3DedcA5984780Bafc599bD69ADd087D56", 18)
    Contract("CAKE", "0x0E09FaBB73Bd3Ade0a17ECC321fD13a19e81cE82", 18)
    '''
    BASE_TOKEN = Contract("BUSD", "0xe9e7CEA3DedcA5984780Bafc599bD69ADd087D56", 18)
    DESIRED_TOKEN = Contract("CAKE", "0x0E09FaBB73Bd3Ade0a17ECC321fD13a19e81cE82", 18)

    # Get custom slippage from user input
    try:
        slippage_input = input("Enter slippage tolerance percentage (default 0.5%): ")
        if slippage_input.strip():
            custom_slippage = Decimal(slippage_input) / 100
        else:
            custom_slippage = Decimal("0.005")  # Default to 0.5%
        
        print(f"Using slippage tolerance: {custom_slippage * 100}%")
    except:
        print("Invalid input, using default slippage of 0.5%")
        custom_slippage = Decimal("0.005")
    
    # Initialize Pancake with custom slippage
    pancake = Pancake(address_wallet, private_key, BASE_TOKEN, DESIRED_TOKEN, slippage=custom_slippage)
    
    # Check balances
    base_balance = pancake.bep20_balance(BASE_TOKEN)
    desired_balance = pancake.bep20_balance(DESIRED_TOKEN)
    print(f"Current {BASE_TOKEN.symbol} balance: {base_balance}")
    print(f"Current {DESIRED_TOKEN.symbol} balance: {desired_balance}")
    
    # Get swap amount from user
    try:
        amount_input = input(f"Enter amount of {BASE_TOKEN.symbol} to swap (max {base_balance}): ")
        amount_buy = Decimal(amount_input)
        if amount_buy > base_balance:
            print(f"Amount exceeds balance. Setting to maximum: {base_balance}")
            amount_buy = base_balance
    except:
        amount_buy = Decimal("10")
        print(f"Using default amount: {amount_buy} {BASE_TOKEN.symbol}")
    
    # Execute swap
    pancake.swap_token(amount_buy)


if __name__ == '__main__':
    main()
