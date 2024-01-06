# import ccxt
import ccxt.async_support as ccxt
from botConfig import *
import pandas as pd
import pandas_ta as ta
import numpy as np
import csv
import os
import time
import asyncio
from binance import AsyncClient
import aiohttp
import json



class ccxtBinance:
    def __init__(self):
        self.exchange = None

# class methods
    def set_sandbox_mode(self, sandbox_mode):
        # Path to your botConfig.py file
        config_path = 'botConfig.py'
        with open(config_path, 'r') as config_file:
            config_lines = config_file.readlines()

        with open(config_path, 'w') as config_file:
            for line in config_lines:
                if line.startswith('sandbox_mode'):
                    config_file.write(f'sandbox_mode = {sandbox_mode}\n')
                else:
                    config_file.write(line)

    def set_api_key_secret(self, api_key, secret_key, config_path, live_mode=False):
        with open(config_path, 'r') as config_file:
            config_lines = config_file.readlines()

        with open(config_path, 'w') as config_file:
            for line in config_lines:
                if line.startswith('sandbox_mode'):
                    if live_mode:
                        config_file.write(f'sandbox_mode = False\n')
                    else:
                        config_file.write(f'sandbox_mode = True\n')
                elif line.startswith('live_apiKey'):
                    if live_mode:
                        config_file.write(f'live_apiKey = \'{api_key}\'\n')
                    else:
                        config_file.write(f'demo_apiKey = \'{api_key}\'\n')
                elif line.startswith('live_secret'):
                    if live_mode:
                        config_file.write(f'live_secret = \'{secret_key}\'\n')
                    else:
                        config_file.write(f'demo_secret = \'{secret_key}\'\n')
                else:
                    config_file.write(line)

    def get_api_key_secret(self, config_path, live_mode=False):
        with open(config_path, 'r') as config_file:
            config_lines = config_file.readlines()
            for line in config_lines:
                if live_mode and line.startswith('live_apiKey'):
                    api_key = line.split('=')[1].strip()
                elif not live_mode and line.startswith('demo_apiKey'):
                    api_key = line.split('=')[1].strip()
                if live_mode and line.startswith('live_secret'):
                    secret_key = line.split('=')[1].strip()
                elif not live_mode and line.startswith('demo_secret'):
                    secret_key = line.split('=')[1].strip()

        return api_key, secret_key

    async def check_authentication(self, exchange):
        try:
            await exchange.load_markets()
            await exchange.fetch_balance()
            return True
        except ccxt.AuthenticationError:
            print(f"Authentication failed: Invalid API key or secret.")
            return False
        except ccxt.BaseError as e:
            print(f"Authentication failed: {e}")
            return False

    async def close_exchange(self):
        if self.exchange:
            await self.exchange.close()
            print("Exchange closed.")

    async def binanceActivate(self, mode_choice):
        try:
            # Set sandbox mode based on the selected mode
            if mode_choice == "Sandbox/Demo":
                sandbox_mode = True
            else:
                sandbox_mode = False

            # If not authenticated, perform the authentication process
            config_path = 'botConfig.py'
            live_mode = mode_choice == "Live"
            api_key, secret_key = self.get_api_key_secret(
                config_path, live_mode=live_mode)
            sandbox_mode = mode_choice == "Sandbox/Demo"

            # Configure the ccxt.binance instance for spot trading
            self.exchange = ccxt.binance({
                'apiKey': api_key.strip("'"),
                'secret': secret_key.strip("'"),
                'verbose': False,  # switch it to False if you don't want the HTTP log
                'options': {'defaultType': 'spot'}
            })

            # Enable or disable sandbox mode based on the selected mode
            self.exchange.set_sandbox_mode(sandbox_mode)

            # Check if the API key and secret are authenticated
            if await self.check_authentication(self.exchange):
                print("Authentication Successful.")
                return self.exchange
            else:
                print("Authentication failed due to invalid key or secret.")
                return None
        except Exception as e:
            print(f"Error during activation: {e}")
            return None
        finally:
            # Ensure that exchange resources are closed, even if an exception occurs
            await self.close_exchange()

    # Function to check authentication and display messages
    def check_authentication_and_display(self):
        # exchange = binanceActive(mode_choice, auth)
        success_message = None
        error_message = None

        if self.exchange:
            _message = 'Authentication Successful'
            # success_message = st.success(_message)
        else:
            _message = "Authentication failed due to invalid key or secret."
            # error_message = st.error(_message)

        time.sleep(5)
        success_message.empty() if success_message else error_message.empty()

        return self.exchange

    def servertime(self):
        time = self.exchange.fetch_time()
        time = pd.to_datetime(time, unit='ms')
        print(time)

    async def getqty(self, coin):
        try:
            balance = await self.exchange.fetch_balance()
            for item in balance['info']['balances']:
                if item['asset'] == coin:
                    qty = float(item['free'])
                    return qty
            return 0.0  # Default value if coin not found in balances
        except Exception as e:
            print(f"Error fetching balance for {coin}: {e}")
            return 0.0  # Return 0.0 in case of an error

    # Define function to place buy order

    async def place_buy_order(self, symbol, size):
        try:
            order = await self.exchange.create_market_buy_order(symbol, size)
            return order
        except Exception as e:
            print(f"Error placing buy order for {symbol}: {e}")
            return False

    async def place_sell_order(self, symbol, size):
        try:
            order = self.exchange.create_market_sell_order(symbol, size)

            # If the order is already created as a dictionary, return it
            if isinstance(order, dict):
                return order

            # If it's not a dictionary, it might be a coroutine; try awaiting it
            try:
                return await order
            except TypeError:
                # If it's not awaitable, return the order itself
                return order

        except Exception as e:
            print(f"Error placing sell order for {symbol}: {e}")
            return False

    async def calculate_order_size(self, symbol, usdt_amount):
        try:
            # Get the current market price of the coin
            ticker = await self.exchange.fetch_ticker(symbol)
            price = ticker['last']
            # Calculate the order size based on the USDT amount and the market price
            size = usdt_amount / price
            return size
        except Exception as e:
            print(f"Error calculating order size for {symbol}: {e}")
            return None

    async def in_pos(self, coin):
        # Ensure that fetch_balance is awaited
        balance_result = await self.exchange.fetch_balance()

        # Access the 'info' and 'balances' properties
        balance = balance_result['info']['balances']

        try:
            asset = float([i['free']
                          for i in balance if i['asset'] == coin][0])
            if asset > 0:
                in_position = True
            else:
                in_position = False
        except Exception as e:
            print(e)
            in_position = False
            asset = 0

        return in_position, balance, asset


class getHist_Data:
    def __init__(self):
        pass

    async def getdata(self, coin, timeframe, slow_ema_period=18):
        try:
            client = await AsyncClient.create()
            limit = slow_ema_period + 2
            ohlcv = await client.get_historical_klines(symbol=coin, interval=timeframe, limit=limit)
            df = self.process_data(ohlcv)
            await client.close_connection()
            return df
        except Exception as e:
            # Handle exceptions here
            print(f"Error fetching data for {coin}: {e}")
            await client.close_connection()
            return None

    def process_data(self, ohlcv,  fast_ema_period=9, slow_ema_period=18):
        df = pd.DataFrame(ohlcv)
        df = df[[0, 1, 2, 3, 4, 5]]
        df.columns = ['timestamp', 'Open', 'High', 'Low', 'Close', 'Volume']
        df = df.set_index('timestamp')
        # Convert the datetime index to date+hh:mm:ss format
        df.index = pd.to_datetime(df.index, unit='ms')
        df = df.astype(float)
        df['fast_ema'] = ta.ema(df['Close'], length=fast_ema_period)
        df['slow_ema'] = ta.ema(df['Close'], length=slow_ema_period)
        df['buy_signal'] = (df['fast_ema'] > df['slow_ema']) & (
            df['fast_ema'].shift(1) < df['slow_ema'].shift(1))
        df['sell_signal'] = (df['fast_ema'] < df['slow_ema']) & (
            df['fast_ema'].shift(1) > df['slow_ema'].shift(1))
        return df


async def getdata(coin, timeframe, fast_ema_period=9, slow_ema_period=18):
    client = await AsyncClient.create()
    limit = (slow_ema_period + 2)
    # start_str=start, end_str=end
    ohlcv = await client.get_historical_klines(symbol=coin, interval=timeframe, limit=limit)
    df = pd.DataFrame(ohlcv)
    df = df[[0, 1, 2, 3, 4, 5]]
    df.columns = ['timestamp', 'Open', 'High', 'Low', 'Close', 'Volume']
    df = df.set_index('timestamp')
    # Convert the datetime index to date+hh:mm:ss format
    df.index = pd.to_datetime(df.index, unit='ms')
    df = df.astype(float)
    df['fast_ema'] = ta.ema(df.Close, length=fast_ema_period)
    df['slow_ema'] = ta.ema(df.Close, length=slow_ema_period)
    buy_signal = np.where(
        ((df['fast_ema'] > df['slow_ema']) &
         (df['fast_ema'].shift(1) < df['slow_ema'].shift(1))),
        True,
        False)
    df['buy_signal'] = buy_signal
    sell_signal = np.where(
        ((df['fast_ema'] < df['slow_ema']) &
         (df['fast_ema'].shift(1) > df['slow_ema'].shift(1))),
        True,
        False)
    df['sell_signal'] = sell_signal
    await client.close_connection()
    return df


def create_file_names(coin):
    coin_lower = coin.lower()
    if not os.path.exists(coin_lower):
        os.makedirs(coin_lower)

    tradesfile = os.path.join(coin_lower, f"{coin_lower}_trades.csv")
    logfile = os.path.join(coin_lower, f"{coin_lower}_log.csv")
    posfile = os.path.join('in_pos.json')  
    qtyfile = os.path.join('qty.json')  

    # Check if files exist, if not, create them
    for filename, headers in zip([tradesfile, logfile, posfile, qtyfile], [['timestamp', 'buyprice', 'sellprice', 'profit%'],
                                                                       ['timestamp', 'Open', 'High', 'Low', 'Close', 'Volume', 'fast_ema', 'slow_ema', 'buy_signal', 'sell_signal'],
                                                                       {}, {}]):
        if not os.path.isfile(filename):
            with open(filename, mode='w') as file:
                if filename.endswith('.csv'):
                    writer = csv.writer(file)
                    writer.writerow(headers)
                elif filename.endswith('.json'):
                    json.dump({}, file)

    return tradesfile, logfile, posfile, qtyfile


def csvlog(df, filename):
    headers = ['timestamp', 'Open', 'High', 'Low', 'Close',
               'Volume', 'fast_ema', 'slow_ema', 'buy_signal', 'sell_signal']

    if not os.path.isfile(filename):
        with open(filename, mode='w') as file:
            writer = csv.writer(file)
            writer.writerow(headers)

    with open(filename, mode='a', newline='') as file:
        writer = csv.writer(file)
        timestamp = df.index[-1]
        row_to_write = [timestamp] + df.iloc[-1].tolist()
        writer.writerow(row_to_write)

# code for appending a new row to the trades CSV file


def buycsv(df, buyprice, filename):
    headers = ['timestamp', 'buyprice', 'sellprice', 'profit%']

    if not os.path.isfile(filename):
        with open(filename, mode='w') as file:
            writer = csv.writer(file)
            writer.writerow(headers)

    with open(filename, mode='a', newline='') as file:
        writer = csv.writer(file)
        buy_price = buyprice  # replace with actual buy price
        sell_price = "Position Still Open"  # replace with actual sell price
        # ((sell_price - buy_price) / buy_price) * 100
        profit_perc = "nan"
        timestamp = df.index[-1]
        writer.writerow([timestamp, buy_price, sell_price, profit_perc])


def sellcsv(df, buyprice, sellprice, filename):
    headers = ['timestamp', 'buyprice', 'sellprice', 'profit%']

    if not os.path.isfile(filename):
        with open(filename, mode='w') as file:
            writer = csv.writer(file)
            writer.writerow(headers)

    with open(filename, mode='a', newline='') as file:
        writer = csv.writer(file)
        profit_perc = ((sellprice - buyprice) / buyprice) * 100
        timestamp = df.index[-1]
        writer.writerow([timestamp, buyprice, sellprice, profit_perc])

def read_buyprice(filename):
    try:
        trades = pd.read_csv(filename)
        buyprice = trades['buyprice'].iloc[-1]
    except:
        buyprice = np.nan
    return buyprice


def read_dict_value(filename, key):
    try:
        with open(filename, 'r') as f:
            d = json.load(f)
        return d.get(key, None)
    except Exception as e:
        print(f"Error reading value for {key} from {filename}: {e}")
        return None


def update_dict_value(filename, key, value):
    with open(filename, 'r') as f:
        d = json.load(f)
    d[key] = value
    with open(filename, 'w') as f:
        json.dump(d, f)
        

def update_inpos(filename, data):
    with open(filename, 'w') as f:
        json.dump(data, f)


# Function to read or create 'running_bots.json' file
def read_running_bots(filename):
    try:
        with open(filename, 'r') as file:
            running_bots_data = json.load(file)
        return running_bots_data
    except FileNotFoundError:
        # Create the file and initialize data if it doesn't exist
        initial_data = {"count": 0, "coins": []}
        with open(filename, 'w') as file:
            json.dump(initial_data, file)
        return initial_data


# Function to update running bots count in the file
def update_running_bots(filename, running_bots_data):
    with open(filename, 'w') as file:
        json.dump(running_bots_data, file)
