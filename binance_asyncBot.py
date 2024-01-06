from myUtils import *
import importlib
import pandas as pd
import pandas_ta as ta
import numpy as np
from datetime import datetime, timedelta
import asyncio
from binance import AsyncClient
import time
import myUtils
from botConfig import *
import nest_asyncio
nest_asyncio.apply()

importlib.reload(myUtils)

# Initialize cb as a global variable
cb = None
in_position = None

# Async function to initialize Binance and activate mode


async def initialize_binance():
    # Instantiate ccxtBinance class
    cb = ccxtBinance()
    # Activate Binance mode
    await cb.binanceActivate(mode)
    return cb

# Read coin list from CSV
coins = pd.read_csv('spot_coins_list.csv')['0'].tolist()

# Function to read bot parameters from JSON file


def read_bot_params(file_path='bot_params.json'):
    try:
        with open(file_path, 'r') as file:
            params = json.load(file)
        return params
    except FileNotFoundError:
        print(f"File '{file_path}' not found.")
        return None


# Fetch bot parameters
params = read_bot_params()

# Check if parameters are successfully fetched
if params:
    # Dynamically create variables using globals()
    for key, value in params.items():
        globals()[key] = value
        print(f"{key}: {value}")
else:
    print("Error: Bot parameters could not be loaded.")
    exit()

# Initialize trades_dict
trades_dict = {'buy_order_data': [], 'sell_order_data': []}

# Async function to fetch OHLCV data for a coin


async def fetch_ohlcv(coin):
    try:
        data = await getdata(coin, timeframe)
        print(coin, data)
        return coin, data.buy_signal.iloc[-2], data.sell_signal.iloc[-2]
    except Exception as e:
        print(coin, e)
        return coin, None, None

# Async function to fetch OHLCV data for all coins


async def fetch_all_ohlcv(coins):
    tasks = [fetch_ohlcv(coin) for coin in coins]
    results = await asyncio.gather(*tasks)
    return results

# Async function to update positions


async def update_positions(posfile):
    global in_position
    balances = await cb.in_pos('BTC')
    for coin in coins:
        coin = coin[:-4]
        try:
            asset = float([i['free']
                          for i in balances[1] if i['asset'] == coin][0])
            in_position[coin + 'USDT'] = asset > 0
        except:
            in_position[coin + 'USDT'] = False

# Async function to buy a coin


async def buyCoin(coin, qtyfile):
    try:
        orderSize = await cb.calculate_order_size(coin, usdt_amount)
        print(coin, orderSize)

        if orderSize is None or orderSize <= 0:
            print(f"Invalid order size for {coin}. Skipping buy order.")
            return None

        order = await cb.place_buy_order(coin, orderSize)

        if order is None:
            print(
                f"Error placing buy order for {coin}. Order response is None.")
            return None

        print(order)

        # Update qty.json file with the new order size
        update_dict_value(qtyfile, coin, orderSize)

        # Append buy order information to trades_dict
        trades_dict['buy_order_data'].append(
            {'coin': coin, 'order': order, 'order_size': orderSize})

        return order
    except Exception as e:
        print(f"Error processing buy order for {coin}: {e}")
        return None


# Async function to sell a coin


async def sellCoin(coin, qtyfile):
    try:
        # Fetch the quantity for the coin from qty.json
        qty = read_dict_value(qtyfile, coin)

        if qty is not None:
            print(f"Quantity for {coin}: {qty}")
        # orderSize = await cb.getqty(coin[:-4])
        # print(f'Order size for {coin}: {orderSize}')
        
        order = await cb.place_sell_order(coin, qty)
        print(order)
        orderSize = 0

        # Update qty.json file with the new order size (square off)
        update_dict_value(qtyfile, coin, orderSize)
        # Append sell order information to trades_dict
        trades_dict['sell_order_data'].append(
            {'coin': coin, 'order': order, 'order_size': qty})

        return order
    except Exception as e:
        print(coin, e)
        return None


# Main async function
async def main_logic():
    global cb, in_position  # Declare cb as a global variable
    running_bots_file = 'running_bots.json'
    try:
        # Initialize Binance
        cb = await initialize_binance()

        # # Initialize bot parameters
        # max_running_bots = 10

        # Read running bots information
        running_bots_data = read_running_bots(running_bots_file)
        running_bots = running_bots_data["count"]

        # Initialize in_position dictionary
        in_position = {coin: False for coin in coins}
        print("in_position initialized", in_position)

        # Generic in_position file in the working directory
        posfile = os.path.join('in_pos.json')
        # update_inpos(posfile, in_position)

        # Load the previous in_position state
        if os.path.isfile(posfile):
            with open(posfile, 'r') as file:
                in_position = json.load(file)

        print("in_position", in_position)

        # Get quantity for USDT
        starting = time.time()
        qty = await cb.getqty('USDT')
        # Generic qty file in the working directory
        qtyfile = os.path.join('qty.json')

        # Load the previous qty state
        if os.path.isfile(qtyfile):
            with open(qtyfile, 'r') as file:
                qty = json.load(file)

        print(qty)

        signals_dict = {'coins': [], 'buy_signals': [], 'sell_signals': []}
        ohlcv_data = await fetch_all_ohlcv(coins)

        for coin, buy_signal, sell_signal in ohlcv_data:
            if buy_signal is not None:
                signals_dict['coins'].append(coin)
                signals_dict['buy_signals'].append(buy_signal)
                signals_dict['sell_signals'].append(sell_signal)

        # Create DataFrame from signals_dict
        signals_df = pd.DataFrame(signals_dict).set_index('coins')
        print("Signals df", signals_df)

        # Extract buy and sell signals
        buysignals = signals_df[signals_df['buy_signals']].index.to_list()
        sellsignals = signals_df[signals_df['sell_signals']].index.to_list()
        print("buysignals", buysignals, "sellsignals", sellsignals)

        # Buy based on signals
        if len(buysignals) > 0:
            for coin in buysignals:
                print(coin)
                if running_bots <= max_running_bots and not in_position[coin]:
                    print('buy please')
                    # Use 'await' for asynchronous function
                    order = await buyCoin(coin, qtyfile)
                    # Check if order is None before accessing its properties
                    if order is not None:
                        buy_price = float(order['info']['fills'][0]['price'])
                        
                        # running_bots += 1
                        running_bots_data["count"] += 1
                        running_bots_data["coins"].append(coin)
                        # Update running bots information
                        update_running_bots(running_bots_file, running_bots_data)
                        # Update in_position in the JSON file
                        update_dict_value(posfile, coin, True)

                        # Get OHLCV data for the specific coin
                        ohlcv_data_coin = await getdata(coin, timeframe)
                        # Append buy trade to the trades CSV file
                        file_paths = create_file_names(coin)

                        print("ohlcv_data_coin:", ohlcv_data_coin)
                        print("buy_price:", buy_price)
                        print("file_paths[0]:", file_paths[0])

                        print("Before buycsv function")
                        buycsv(ohlcv_data_coin, buy_price, file_paths[0])
                        print("After buycsv function")
                        csvlog(ohlcv_data_coin, file_paths[1])

        # Sell based on signals
        if len(sellsignals) > 0:
            for coin in sellsignals:
                if in_position[coin]:
                    print('Sell please!')
                    
                    # Use 'await' for asynchronous function
                    order = await sellCoin(coin, qtyfile)

                    # running_bots += 1
                    running_bots_data["count"] -= 1
                    if coin in running_bots_data["coins"]:
                        running_bots_data["coins"].remove(coin)
                    # Update running bots information
                    update_running_bots(running_bots_file, running_bots_data)
                    # Update in_position in the JSON file
                    update_dict_value(posfile, coin, False)
                    # Get OHLCV data for the specific coin
                    ohlcv_data_coin = await getdata(coin, timeframe)
                    # Append buy trade to the trades CSV file
                    file_paths = create_file_names(coin)
                    buyprice = read_buyprice(file_paths[0])
                    # replace with actual sell price
                    sell_price = float(order['info']['fills'][0]['price'])
                    sellcsv(ohlcv_data_coin, buyprice,
                            sell_price, file_paths[0])
                    csvlog(ohlcv_data_coin, file_paths[1])
        running_bots = running_bots_data["count"]
        print("Total Running Bots:", running_bots)
    except Exception as e:
        print(e)
    finally:
        # Update positions
        await update_positions(posfile)
        # Ensure you close the exchange instance to release resources
        if cb is not None:
            await cb.close_exchange()

# Run the event loop
try:
    asyncio.run(main_logic())
except Exception as e:
    print(e)
