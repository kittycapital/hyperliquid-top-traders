"""
Hyperliquid Top Traders Fetcher
Fetches top 10 traders by daily/weekly PnL and their open positions.
"""

import json
import requests
from datetime import datetime

LEADERBOARD_URL = "https://stats-data.hyperliquid.xyz/Mainnet/leaderboard"
INFO_URL = "https://api.hyperliquid.xyz/info"
DATA_FILE = "data.json"


def fetch_leaderboard():
    """Fetch leaderboard data from Hyperliquid"""
    print("Fetching leaderboard...")
    
    try:
        response = requests.get(LEADERBOARD_URL, timeout=30)
        response.raise_for_status()
        data = response.json()
        
        traders = data.get('leaderboardRows', [])
        print(f"Got {len(traders)} traders from leaderboard")
        return traders
    
    except Exception as e:
        print(f"Error fetching leaderboard: {e}")
        return []


def fetch_positions(address):
    """Fetch open positions for a wallet address"""
    
    try:
        payload = {
            "type": "clearinghouseState",
            "user": address
        }
        
        response = requests.post(
            INFO_URL,
            json=payload,
            headers={"Content-Type": "application/json"},
            timeout=15
        )
        response.raise_for_status()
        data = response.json()
        
        positions = []
        for asset_pos in data.get('assetPositions', []):
            pos = asset_pos.get('position', {})
            if pos:
                szi = float(pos.get('szi', 0))
                if szi != 0:  # Only include non-zero positions
                    leverage_data = pos.get('leverage', {})
                    positions.append({
                        'coin': pos.get('coin', ''),
                        'direction': 'Long' if szi > 0 else 'Short',
                        'size': abs(szi),
                        'entryPx': pos.get('entryPx', '0'),
                        'leverage': leverage_data.get('value', 0),
                        'leverageType': leverage_data.get('type', 'cross'),
                        'positionValue': pos.get('positionValue', '0'),
                        'unrealizedPnl': pos.get('unrealizedPnl', '0'),
                        'returnOnEquity': pos.get('returnOnEquity', '0'),
                        'liquidationPx': pos.get('liquidationPx', '')
                    })
        
        return positions
    
    except Exception as e:
        print(f"Error fetching positions for {address[:10]}...: {e}")
        return []


def get_pnl_data(trader, period):
    """Extract PnL data for a specific period (day/week)"""
    
    for perf in trader.get('windowPerformances', []):
        if perf[0] == period:
            return {
                'pnl': float(perf[1].get('pnl', 0)),
                'roi': float(perf[1].get('roi', 0)),
                'volume': float(perf[1].get('vlm', 0))
            }
    
    return {'pnl': 0, 'roi': 0, 'volume': 0}


def process_traders(traders, period, top_n=10):
    """Process and sort traders by PnL for a given period"""
    
    processed = []
    
    for trader in traders:
        pnl_data = get_pnl_data(trader, period)
        
        # Skip traders with zero PnL
        if pnl_data['pnl'] == 0:
            continue
        
        processed.append({
            'address': trader.get('ethAddress', ''),
            'displayName': trader.get('displayName'),
            'accountValue': float(trader.get('accountValue', 0)),
            'pnl': pnl_data['pnl'],
            'roi': pnl_data['roi'],
            'volume': pnl_data['volume']
        })
    
    # Sort by PnL (highest first)
    processed.sort(key=lambda x: x['pnl'], reverse=True)
    
    return processed[:top_n]


def main():
    print("=" * 50)
    print("Hyperliquid Top Traders Fetcher")
    print("=" * 50)
    
    # Fetch leaderboard
    traders = fetch_leaderboard()
    
    if not traders:
        print("Failed to fetch leaderboard")
        return
    
    # Process top traders for daily and weekly
    print("\nProcessing daily top 10...")
    daily_top = process_traders(traders, 'day', 10)
    
    print("Processing weekly top 10...")
    weekly_top = process_traders(traders, 'week', 10)
    
    # Fetch positions for all unique addresses
    all_addresses = set()
    for t in daily_top + weekly_top:
        all_addresses.add(t['address'])
    
    print(f"\nFetching positions for {len(all_addresses)} unique traders...")
    
    positions_map = {}
    for i, address in enumerate(all_addresses):
        print(f"  [{i+1}/{len(all_addresses)}] {address[:10]}...")
        positions = fetch_positions(address)
        positions_map[address] = positions
    
    # Attach positions to traders
    for trader in daily_top:
        trader['positions'] = positions_map.get(trader['address'], [])
    
    for trader in weekly_top:
        trader['positions'] = positions_map.get(trader['address'], [])
    
    # Print summary
    print("\n" + "=" * 50)
    print("Daily Top 3:")
    for i, t in enumerate(daily_top[:3]):
        name = t['displayName'] or t['address'][:10] + '...'
        print(f"  #{i+1} {name}: ${t['pnl']:,.0f} ({t['roi']*100:.2f}%)")
    
    print("\nWeekly Top 3:")
    for i, t in enumerate(weekly_top[:3]):
        name = t['displayName'] or t['address'][:10] + '...'
        print(f"  #{i+1} {name}: ${t['pnl']:,.0f} ({t['roi']*100:.2f}%)")
    
    # Save to JSON
    output = {
        'daily': daily_top,
        'weekly': weekly_top,
        'lastUpdated': datetime.utcnow().isoformat() + 'Z'
    }
    
    with open(DATA_FILE, 'w') as f:
        json.dump(output, f, indent=2)
    
    print(f"\nSaved to {DATA_FILE}")


if __name__ == '__main__':
    main()
