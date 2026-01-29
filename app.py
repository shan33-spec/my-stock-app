import streamlit as st
import yfinance as yf
import pandas as pd

# 1. 頁面設定
st.set_page_config(page_title="股票包租公 (防擋版)", page_icon="🛡️")

st.title("🛡️ 我的股票包租公")
st.markdown("已升級 **強力抓取模式**，解決 ETF 讀取失敗問題。")

# --- 側邊欄：存檔與讀檔 ---
st.sidebar.header("📂 檔案存取")
uploaded_file = st.sidebar.file_uploader("讀取舊檔案 (CSV)", type=["csv"])

# 預設持股 (這裡可以改成您的庫存)
if uploaded_file is None:
    default_data = pd.DataFrame([
        {"代號": "0056", "成本": 30.0, "股數": 1000},
        {"代號": "00878", "成本": 18.0, "股數": 2000},
        {"代號": "00919", "成本": 22.0, "股數": 1000},
        {"代號": "2330", "成本": 600.0, "股數": 100},
    ])
else:
    try:
        default_data = pd.read_csv(uploaded_file)
        default_data["代號"] = default_data["代號"].astype(str)
    except:
        st.error("檔案格式有誤，請使用標準 CSV。")

# 編輯表格
edited_df = st.data_editor(
    default_data, 
    num_rows="dynamic",
    column_config={
        "代號": st.column_config.TextColumn(help="股票代號"),
        "成本": st.column_config.NumberColumn(format="$%.1f"),
        "股數": st.column_config.NumberColumn(format="%d"),
    }
)

# 下載按鈕
csv = edited_df.to_csv(index=False).encode('utf-8')
st.sidebar.download_button(
    label="⬇️ 下載目前清單",
    data=csv,
    file_name='my_stock_portfolio.csv',
    mime='text/csv',
)

# 3. 按鈕觸發計算 (強力模式)
if st.button("開始計算資產與配息 🚀", type="primary"):
    st.divider()
    st.subheader("2. 試算結果")
    
    total_market_value = 0
    total_cost = 0
    total_dividends = 0
    results = []
    
    progress_bar = st.progress(0)
    
    for index, row in edited_df.iterrows():
        stock_id = str(row["代號"]).strip()
        # 補零處理 (例如 56 -> 0056)
        if len(stock_id) < 4: stock_id = stock_id.zfill(4)
        
        cost = float(row["成本"])
        qty = int(row["股數"])
        
        # 處理代號
        ticker = f"{stock_id}.TW"
        if ".TWO" in stock_id: ticker = stock_id 
        
        try:
            stock = yf.Ticker(ticker)
            
            # --- 強力抓取邏輯 (避開阻擋) ---
            price = None
            stock_name = stock_id # 預設名稱先用代號
            
            # 方法 A: 嘗試使用 fast_info (較快且不易被擋)
            try:
                price = stock.fast_info['last_price']
            except:
                pass
            
            # 方法 B: 如果 A 失敗，嘗試抓歷史資料
            if price is None:
                try:
                    hist = stock.history(period="1d")
                    if not hist.empty:
                        price = hist['Close'].iloc[-1]
                except:
                    pass

            # 嘗試抓取名稱 (如果失敗就跳過，不影響計算)
            try:
                # 這裡最容易被擋，所以用 try 包起來
                info = stock.info 
                stock_name = info.get('longName', stock_id)
                div_rate = info.get('dividendRate', 0)
            except:
                div_rate = 0 # 抓不到就先當作 0
                
            # 計算區
            if price:
                m_val = price * qty
                m_cost = cost * qty
                profit = m_val - m_cost
                est_div = div_rate * qty if div_rate else 0
                
                total_market_value += m_val
                total_cost += m_cost
                total_dividends += est_div
                
                results.append({
                    "股票": stock_name,
                    "代號": stock_id,
                    "現價": price,
                    "損益": profit,
                    "報酬率(%)": round((profit/m_cost)*100, 2) if m_cost>0 else 0,
                    "預估股息": int(est_div)
                })
            else:
                st.warning(f"⚠️ 代號 {stock_id} 暫時無法連線，請稍後再試。")
                
        except Exception as e:
            st.error(f"代號 {stock_id} 發生未知錯誤：{e}")
        
        progress_bar.progress((index + 1) / len(edited_df))

    # 看板區
    c1, c2, c3 = st.columns(3)
    c1.metric("💰 總市值", f"{int(total_market_value):,} 元")
    
    profit = total_market_value - total_cost
    c2.metric("📈 總損益", f"{int(profit):,} 元", 
              delta=f"{(profit/total_cost)*100:.1f}%" if total_cost>0 else "0%",
              delta_color="inverse")
    
    c3.metric("🧧 預估年股息", f"{int(total_dividends):,} 元", help="若顯示為 0 代表 Yahoo 暫時擋住配息資料")

    if results:
        st.divider()
        res_df = pd.DataFrame(results)
        def color_profit(val):
            return f'color: {"red" if val > 0 else "green"}'
        
        st.dataframe(
            res_df.style.map(color_profit, subset=['損益', '報酬率(%)'])
                     .format({"現價": "{:.2f}", "損益": "{:,.0f}", "預估股息": "{:,.0f}"}),
            use_container_width=True
        )
