import streamlit as st
from myUtils import *
import importlib
import pandas as pd
import pandas_ta as ta
import numpy as np
from datetime import datetime, timedelta
import time
import myUtils
from botConfig import *


importlib.reload(myUtils)

# Initialize cb as a global variable
cb = None
in_position = None

# Read coin list from CSV
coins = pd.read_csv('spot_coins_list.csv')['0'].tolist()


def create_bot_params_file(params):
    with open('bot_params.json', 'w') as file:
        json.dump(params, file)

# Function to fetch current running bots from the file


def fetch_running_bots(filename):
    try:
        with open(filename, 'r') as file:
            running_bots_data = json.load(file)
        return running_bots_data["coins"]
    except FileNotFoundError:
        return []

# Function to display trades for a specific coin


def display_trades(coin):
    st.subheader(f"Trades for {coin}")
    trade_file_path = f"{coin.lower()}/{coin.lower()}_trades.csv"
    try:
        trade_data = pd.read_csv(trade_file_path)
        st.write(trade_data)
    except FileNotFoundError:
        st.warning(f"No trade file found for {coin}")

# Function to display trades for a specific coin


def display_all_trades(coin):
    # st.subheader(f"Trades for {coin}")
    trade_file_path = f"{coin.lower()}/{coin.lower()}_trades.csv"
    try:
        trade_data = pd.read_csv(trade_file_path)

        # Add coin symbol as a new column
        trade_data.insert(0, 'Coin Symbol', coin)

        # Display the trade data
        st.write(trade_data)
    except FileNotFoundError:
        st.warning(f"No trade file found for {coin}")


# Sidebar with user inputs
st.sidebar.title("Trading Bot Configuration")
timeframe = st.sidebar.selectbox(
    "Select Timeframe", ["1h", "4h", "6h", "12h", "1d"], index=0)
fast_ema_period = st.sidebar.slider("Fast EMA Period", 1, 50, 9)
slow_ema_period = st.sidebar.slider("Slow EMA Period", 1, 50, 18)
usdt_amount = st.sidebar.number_input("USDT Amount", min_value=1.0, value=10.0)
tp_perc = st.sidebar.number_input(
    "Take Profit Percentage", min_value=1, max_value=100, value=10)
max_running_bots = st.sidebar.number_input(
    "Max Running Bots", min_value=1, value=10)

# Button to save parameters
if st.button("Save Bot Parameters"):
    params = {
        "timeframe": timeframe,
        "fast_ema_period": fast_ema_period,
        "slow_ema_period": slow_ema_period,
        "usdt_amount": usdt_amount,
        "tp_perc": tp_perc,
        "max_running_bots": max_running_bots,
    }

    # Create bot_params.json file
    create_bot_params_file(params)

    st.success("Bot parameters saved successfully!")

# Display general information
st.title("Trading Bot Dashboard")
st.write("Current Bot Configuration:")
st.write(f"Timeframe: {timeframe}")
st.write(f"Fast EMA Period: {fast_ema_period}")
st.write(f"Slow EMA Period: {slow_ema_period}")
st.write(f"USDT Amount: {usdt_amount}")
st.write(f"Take Profit Percentage: {tp_perc}%")
st.write(f"Max Running Bots: {max_running_bots}")

# Generic in_position file in the working directory
posfile = os.path.join('in_pos.json')
# update_inpos(posfile, in_position)

# Load the previous in_position state
if os.path.isfile(posfile):
    with open(posfile, 'r') as file:
        in_position = json.load(file)

coins = in_position.keys()  # Replace with your data
# Display trade files for running coins
running_coins = [coin for coin, status in in_position.items() if status]

# Button to fetch and display trades for all running coins
if st.button("View Trades for all Run Coins"):
    # Fetch all available folders (coins) ending with 'usdt'
    all_folders = [folder for folder in os.listdir() if os.path.isdir(
        folder) and folder.lower().endswith('usdt')]

    # Display trades for all available folders
    if all_folders:
        st.header("All Running Coins and Their Trades")
        for coin_folder in all_folders:
            coin = coin_folder.upper()
            display_all_trades(coin)
    else:
        st.info("No running coins to display.")



# Button to fetch and display trades for running bots
if st.button("Fetch Trades for Running Bots"):
    running_bots_file = 'running_bots.json'
    running_coins = fetch_running_bots(running_bots_file)

    if running_coins:
        st.header("Running Bots and Their Trades")
        for coin in running_coins:
            display_trades(coin)
    else:
        st.warning("No running bots found.")
