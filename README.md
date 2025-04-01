# Depercated, please look at my Pancakeswap v3 <a href="https://github.com/RetributionByRevenue/pancakeswapV3_simple_swap/tree/main">example</a>



Swap BUSD &lt;-> CAKE working example

Features:
1) Fetch Gas Programmatically
2) Fee is hardcoded to be 0.25%. Pancakeswap v2 is hard coded to always use 0.25% fee. Does not support custom fee tiers like v3.

Considerations:
Sometimes the quote is you get is good, other times it is really bad as the liquidity in CAKE/USDT does not have enough liquidity to be market accurate. It will be off by multiple %, so please add a check in your code to determine if it is a fair value swap. I recon you should add custom logic to notify you that the fee is not good, and that you should use trust wallet to place the swap, as trust wallet queries multiple liquidity providers like 1inch and 0x. Trust wallet is same swap fee tier as pancake swap. 

Console Output:
<pre>
Enter slippage tolerance percentage (default 0.5%): 0.5
Using slippage tolerance: 0.500%
Current BUSD balance: 31.778055146451408066
Current CAKE balance: 0
Enter amount of BUSD to swap (max 31.778055146451408066): 10
Starting swap from BUSD to CAKE...
Using slippage tolerance: 0.500%
Checking approval for BUSD to PancakeSwap...
Approving BUSD for trading on PancakeSwap...
Current gas price: 1.00 Gwei
Estimated gas cost: 0.000047 BNB
Transaction sent: 0xfb9fc5e564410122e422c9781f16ab30cb5516e2ab0e1fb07562e76f873a67e3
Transaction confirmed: Block #47562470
Approval confirmed for BUSD.
Using PancakeSwap router at 0x10ED43C718714eb63d5aA57B78B54704E256024E
Swap path: BUSD -> CAKE
Input amount: 10 BUSD (10000000000000000000 wei)
Expected output: 4.033760220067199022 CAKE
Minimum output after slippage: 4.003507018416695029 CAKE
Transaction deadline: 2025-03-17 23:42:58

Confirm swap 10 BUSD for ~4.033760220067199022 CAKE? (yes/no): yes
Sending transaction...
Current gas price: 1.00 Gwei
Estimated gas cost: 0.000130 BNB
Transaction sent: 0xe22d49821fa710e39ffde9d822a44e581bcadb98259865de093db204dd483e9e
Transaction confirmed: Block #47562476
</pre>
