import ccxt
from botConfig import *
import pandas as pd
import pandas_ta as ta
import numpy as np
import csv
import os
import time
import asyncio
from binance import AsyncClient

# 
class ccxtBinance:
    def __init__(self):
        self.exchange = None

#class methods
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

    def check_authentication(self, exchange):
        try:
            balance = exchange.fetch_balance()  # Replace with an actual API request
            # If the request succeeds, the authentication is correct
            return True

        except ccxt.AuthenticationError as e:
            # st.info('Could not authenticate, Authentication error')
            return False

    def binanceActivate(self, mode_choice):
        # Set sandbox mode based on the selected mode
        if mode_choice == "Sandbox/Demo":
            sandbox_mode = True
        else:
            sandbox_mode = False
        
        # If not authenticated, perform the authentication process
        config_path = 'botConfig.py'
        live_mode = mode_choice == "Live"
        api_key, secret_key = self.get_api_key_secret(config_path, live_mode=live_mode)
        sandbox_mode = mode_choice == "Sandbox/Demo"

        # Configure the ccxt.binance instance
        self.exchange = ccxt.binance({
            'apiKey': api_key.strip("'"),
            'secret': secret_key.strip("'"),
            'verbose': False,  # switch it to False if you don't want the HTTP log
        })

        # Enable or disable sandbox mode based on the selected mode
        self.exchange.set_sandbox_mode(sandbox_mode)

        # Check if the API key and secret are authenticated
        if self.check_authentication(self.exchange):
            # authenticated = True  # Cache the authentication result
            print("Authentication Successful.")
            return self.exchange
        else:
            print("Authentication failed due to invalid key or secret.")
            return None

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
        time = pd.to_datetime(time, unit ='ms')
        print(time)


    def getqty(self, coin):
        for item in self.exchange.fetch_balance()['info']['balances']:
            if item['asset'] == coin:
                qty = float(item['free'])
        return qty

    # Define function to place buy order
    async def place_buy_order(self, symbol, size):
        try:
            buyId = await self.exchange.create_market_buy_order(symbol, size)
            return buyId
        except:
            return False
        
    # Define function to place sell order
    def place_sell_order(self, symbol, size):
        # try:
        # client = await AsyncClient.create()
        sellId = self.exchange.create_market_sell_order(symbol, size)
        return sellId
        # except:
        #     return False
        
    def calculate_order_size(self, symbol, usdt_amount):
        # Get the current market price of the coin
        ticker = self.exchange.fetch_ticker(symbol)
        price = ticker['last']
        # Calculate the order size based on the USDT amount and the market price
        size = usdt_amount / price
        return size
    
def in_pos(self, coin):
    balance = self.exchange.fetch_balance()['info']['balances']
    try:
        asset = float([i['free'] for i in balance if i['asset'] == coin][0])
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

    async def getdata(self, coin, timeframe, slow_ema_period = 18):
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

    def process_data(self, ohlcv,  fast_ema_period = 9, slow_ema_period = 18):
        df = pd.DataFrame(ohlcv)
        df = df[[0,1,2,3,4,5]]
        df.columns = ['timestamp','Open','High','Low','Close','Volume']
        df = df.set_index('timestamp')
        # Convert the datetime index to date+hh:mm:ss format
        df.index = pd.to_datetime(df.index, unit = 'ms') 
        df= df.astype(float)
        df['fast_ema'] = ta.ema(df['Close'], length=fast_ema_period)
        df['slow_ema'] = ta.ema(df['Close'], length=slow_ema_period)
        df['buy_signal'] = (df['fast_ema'] > df['slow_ema']) & (df['fast_ema'].shift(1) < df['slow_ema'].shift(1))
        df['sell_signal'] = (df['fast_ema'] < df['slow_ema']) & (df['fast_ema'].shift(1) > df['slow_ema'].shift(1))
        return df
    

async def getdata(coin, timeframe, fast_ema_period = 9, slow_ema_period = 18):
    client = await AsyncClient.create()
    limit = (slow_ema_period + 2)
    ohlcv = await client.get_historical_klines(symbol=coin, interval=timeframe, limit= limit)#start_str=start, end_str=end
    df = pd.DataFrame(ohlcv)
    df = df[[0,1,2,3,4,5]]
    df.columns = ['timestamp','Open','High','Low','Close','Volume']
    df = df.set_index('timestamp')
    # Convert the datetime index to date+hh:mm:ss format
    df.index = pd.to_datetime(df.index, unit = 'ms') 
    df= df.astype(float)
    df['fast_ema'] = ta.ema(df.Close, length = fast_ema_period)
    df['slow_ema'] = ta.ema(df.Close, length = slow_ema_period)
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
