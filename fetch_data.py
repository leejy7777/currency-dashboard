import yfinance as yf
import json
import datetime
import os
import numpy as np
import pandas as pd

def fetch_market_data():
    # Define the tickers for 1 year
    tickers = {
        "exchange_rates": {
            "USD/KRW": "USDKRW=X",
            "JPY/KRW": "JPYKRW=X",
            "CNY/KRW": "CNYKRW=X",
            "EUR/KRW": "EURKRW=X",
            "VND/KRW": "VNDKRW=X",
            "TWD/KRW": "TWDKRW=X",
            "AUD/KRW": "AUDKRW=X"
        },
        "indices": {
            "DXY (달러 인덱스)": "DX-Y.NYB"
        }
    }
    
    result = {
        "last_updated": datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=9))).strftime("%Y-%m-%d %H:%M:%S"),
        "exchange_rates": [],
        "indices": []
    }

    print("Fetching data...")

    # Fetch Exchange Rates
    for name, symbol in tickers["exchange_rates"].items():
        try:
            ticker = yf.Ticker(symbol)
            hist = ticker.history(period="5y")
            
            # Fallback for symbols with missing history (like CNYKRW=X)
            if len(hist) < 200 and symbol.endswith('KRW=X') and symbol != 'USDKRW=X':
                print(f"[*] {name} history too short ({len(hist)}). Calculating via cross rate...")
                base_currency = symbol.replace('KRW=X', '')
                base_ticker = yf.Ticker(f"{base_currency}=X")
                krw_ticker = yf.Ticker("KRW=X")
                
                base_hist = base_ticker.history(period="5y")['Close']
                krw_hist = krw_ticker.history(period="5y")['Close']
                
                # Calculate cross rate: (USD/KRW) / (USD/Base)
                hist_close = krw_hist / base_hist
                hist_close = hist_close.dropna()
                
                labels = hist_close.index.strftime('%Y-%m-%d').tolist()
                data = hist_close.tolist()
            else:
                labels = hist.index.strftime('%Y-%m-%d').tolist()
                data = hist['Close'].tolist()
            
            # Format data for chart
            
            if len(data) > 0:
                current_price = data[-1]
                prev_price = data[-2] if len(data) > 1 else current_price
                change_percent = ((current_price - prev_price) / prev_price) * 100
                
                precision = 4 if current_price < 10 else 2
                
                result["exchange_rates"].append({
                    "name": name,
                    "symbol": symbol,
                    "current": round(current_price, precision),
                    "change_percent": round(change_percent, 2),
                    "stats": {
                        "mean": round(float(np.mean(data)), precision),
                        "median": round(float(np.median(data)), precision),
                        "high": round(float(np.max(data)), precision),
                        "low": round(float(np.min(data)), precision)
                    },
                    "history": {
                        "labels": labels,
                        "data": [round(val, precision) for val in data]
                    }
                })
                print(f"[OK] Loaded {name}")
            else:
                print(f"[FAIL] No data for {name}")
        except Exception as e:
            print(f"[ERROR] Error loading {name}: {e}")

    # Fetch Indices
    for name, symbol in tickers["indices"].items():
        try:
            ticker = yf.Ticker(symbol)
            hist = ticker.history(period="5y")
            
            labels = hist.index.strftime('%Y-%m-%d').tolist()
            data = hist['Close'].tolist()
            
            if len(data) > 0:
                current_price = data[-1]
                prev_price = data[-2] if len(data) > 1 else current_price
                change_percent = ((current_price - prev_price) / prev_price) * 100
                
                result["indices"].append({
                    "name": name,
                    "symbol": symbol,
                    "current": round(current_price, 2),
                    "change_percent": round(change_percent, 2),
                    "stats": {
                        "mean": round(float(np.mean(data)), 2),
                        "median": round(float(np.median(data)), 2),
                        "high": round(float(np.max(data)), 2),
                        "low": round(float(np.min(data)), 2)
                    },
                    "history": {
                        "labels": labels,
                        "data": [round(val, 2) for val in data]
                    }
                })
                print(f"[OK] Loaded {name}")
            else:
                print(f"[FAIL] No data for {name}")
        except Exception as e:
            print(f"[ERROR] Error loading {name}: {e}")

    # Calculate Custom Indices
    print("Calculating Custom Indices...")
    try:
        # Fetch histories for 5y
        usd_series = pd.Series(1.0, index=yf.Ticker('KRW=X').history(period='5y').index)
        eur_series = yf.Ticker('EUR=X').history(period='5y')['Close']
        jpy_series = yf.Ticker('JPY=X').history(period='5y')['Close']
        cny_series = yf.Ticker('CNY=X').history(period='5y')['Close']
        krw_series = yf.Ticker('KRW=X').history(period='5y')['Close']
        vnd_series = yf.Ticker('VND=X').history(period='5y')['Close']
        twd_series = yf.Ticker('TWD=X').history(period='5y')['Close']
        aud_series = yf.Ticker('AUD=X').history(period='5y')['Close']
        
        df = pd.DataFrame({
            'USD': usd_series, 'EUR': eur_series, 'JPY': jpy_series, 
            'CNY': cny_series, 'KRW': krw_series, 'VND': vnd_series, 
            'TWD': twd_series, 'AUD': aud_series
        }).dropna()
        
        if not df.empty:
            # Value of each currency in USD (1 / rate)
            v = 1.0 / df
            # Normalize to 1-year average = 100 (approx 252 trading days)
            v_1y_mean = v.tail(252).mean()
            v_norm = v / v_1y_mean
            
            # Columns order: USD, EUR, JPY, CNY, KRW, VND, TWD, AUD
            w_v1 = [0.125, 0.125, 0.125, 0.125, 0.125, 0.125, 0.125, 0.125]
            w_v2 = [0.582, 0.205, 0.112, 0.046, 0.013, 0.001, 0.001, 0.040]
            w_v3 = [0.175, 0.110, 0.077, 0.263, 0.200, 0.099, 0.044, 0.032]
            
            geom_mean_v1 = np.exp(np.average(np.log(v_norm), weights=w_v1, axis=1))
            geom_mean_v2 = np.exp(np.average(np.log(v_norm), weights=w_v2, axis=1))
            geom_mean_v3 = np.exp(np.average(np.log(v_norm), weights=w_v3, axis=1))
            
            result["custom_indices_v1"] = []
            result["custom_indices_v2"] = []
            result["custom_indices_v3"] = []
            
            currencies_to_loop = [
                ('USD', '달러'), ('KRW', '원화'), ('JPY', '엔화'), ('EUR', '유로화'), 
                ('CNY', '위안화'), ('VND', '베트남 동'), ('TWD', '대만 달러'), ('AUD', '호주 달러')
            ]
            
            for version, geom_mean, target_list in [("v1", geom_mean_v1, result["custom_indices_v1"]), 
                                                    ("v2", geom_mean_v2, result["custom_indices_v2"]), 
                                                    ("v3", geom_mean_v3, result["custom_indices_v3"])]:
                for currency, name_kr in currencies_to_loop:
                    idx_series = (v_norm[currency] / geom_mean) * 100
                    labels = idx_series.index.strftime('%Y-%m-%d').tolist()
                    data = idx_series.tolist()
                    
                    if len(data) > 0:
                        current_price = data[-1]
                        prev_price = data[-2] if len(data) > 1 else current_price
                        change_percent = ((current_price - prev_price) / prev_price) * 100
                        
                        target_list.append({
                            "name": f"{name_kr} 인덱스 ({version.upper()})",
                            "symbol": f"CIDX-{currency}-{version}",
                            "current": round(current_price, 2),
                            "change_percent": round(change_percent, 2),
                            "stats": {
                                "mean": round(float(np.mean(data)), 2),
                                "median": round(float(np.median(data)), 2),
                                "high": round(float(np.max(data)), 2),
                                "low": round(float(np.min(data)), 2)
                            },
                            "history": {
                                "labels": labels,
                                "data": [round(val, 2) for val in data]
                            }
                        })
            print("[OK] Calculated Custom Indices V1, V2, V3")
    except Exception as e:
        print(f"[ERROR] Error calculating custom indices: {e}")

    # Save to JSON
    output_path = os.path.join(os.path.dirname(__file__), "market_data.json")
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    
    print(f"Data saved to {output_path}")

if __name__ == "__main__":
    fetch_market_data()
