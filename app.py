import streamlit as st
import yfinance as yf
import pandas as pd

# 1. 頁面設定
st.set_page_config(page_title="股票包租公 (配息加強版)", page_icon="💰")

st.title("💰 我的股票包租公")
st.markdown("新增 **預估股利** 欄位，解決抓不到配息的問題！")

# --- 側邊欄：存檔與讀檔 ---
st.sidebar.header("📂 檔案存取")
uploaded_file = st.sidebar.file_uploader("讀取舊檔案 (CSV)", type=["csv"])

# 預設持股 (新增 '預估股利' 欄位，預設為 0 代表讓系統自動抓)
if uploaded_file is None:
    default_data = pd.DataFrame([
        {"代號": "0056", "成本": 38.0, "股數": 1000, "預估股利": 0.0},
        {"代號": "2330", "成本": 600.0, "股數": 100, "預估股利": 0.0},
        {"代號": "00919", "成本": 22.0, "股數": 2000, "預估股利": 0.0},
    ])
else:
    try:
        default_data = pd.read_csv(uploaded_file)
        default_data["代號"] = default_data["代號"].astype(str)
        # 如果舊檔案沒有股利欄位，幫它補上
        if "預估股利" not in default_data.columns:
            default_data["預估股利"] = 0.0
    except:
        st.error("檔案格式有誤。")
        default_data = pd.DataFrame([{"代號": "", "成本": 0.0, "股數": 0, "預估股利": 0.0}])

# 編輯表格說明
st.info("💡 **小撇步**：如果「預估股利」填 **0**，系統會去網路自動抓。如果抓不到，請手動填入金額 (例如 2.5)。")

# 編輯表格
edited_df = st.data_editor(
    default_data, 
    num_rows="dynamic",
    column_config={
        "代號": st.column_config.TextColumn(help="股票代號"),
        "成本": st.column_config.NumberColumn(format="$%.2f"),
        "股數": st.column_config.NumberColumn(format="%d"),
        "預估股利": st.column_config.NumberColumn(
            format="$%.2f", 
            help="填 0 代表自動抓取；若抓不到可手動輸入 (單位:元/股)",
            min_value=0.0
        ),
    },
    key="dividend_editor"
)

# 下載按鈕
csv = edited_df.to_csv(index=False).encode('utf-8')
st.sidebar.download_button(
    label="⬇️ 下載目前清單",
    data=csv,
    file_name='my_stock_portfolio.csv',
    mime='text/csv',
)

# 3. 按鈕觸發計算
if st.button("開始計算資產與配息 🚀", type="primary"):
    st.divider()
    st.subheader("2. 試算結果")
    
    total_market_value = 0
    total_cost = 0
    total_dividends = 0
    results = []
    
    progress_bar = st.progress(0)
    total_rows = len(edited_df)
    
    for index, row in edited_df.iterrows():
        # 防呆檢查
        if pd.isna(row["代號"]) or pd.isna(row["股數"]) or str(row["代號"]).strip() == "":
            continue
            
        stock_id = str(row["代號"]).strip()
        try:
            cost = float(row["成本"])
            qty = int(row["股數"])
            # 取得使用者手動輸入的股利
            manual_div = float(row.get("預估股利", 0))
        except:
            continue
            
        # 補零
        if len(stock_id) < 4: stock_id = stock_id.zfill(4)
        ticker = f"{stock_id}.TW"
        if ".TWO" in stock_id: ticker = stock_id 
        
        try:
            stock = yf.Ticker(ticker)
            
            # --- 1. 抓股價 ---
            price = None
            try:
                price = stock.fast_info['last_price']
            except:
                try:
                    hist = stock.history(period="1d")
                    if not hist.empty:
                        price = hist['Close'].iloc[-1]
                except:
                    pass
            
            # --- 2. 抓/算 配息 ---
            final_div_rate = 0
            source_msg = "自動"
            
            # 策略：如果使用者有手動填 (大於0)，就直接用使用者的
            if manual_div > 0:
                final_div_rate = manual_div
                source_msg = "手動"
            else:
                # 否則嘗試去網路抓
                try:
                    info = stock.info 
                    fetched_div = info.get('dividendRate', 0)
                    if fetched_div:
                        final_div_rate = fetched_div
                except:
                    pass

            # 抓名稱
            try:
                stock_name = stock.info.get('longName', stock_id)
            except:
                stock_name = stock_id

            # --- 3. 總結算 ---
            if price:
                m_val = price * qty
                m_cost = cost * qty
                profit = m_val - m_cost
                
                # 計算該檔股票總股息
                est_div_total = final_div_rate * qty
                
                total_market_value += m_val
                total_cost += m_cost
                total_dividends += est_div_total
                
                results.append({
                    "股票": stock_name,
                    "代號": stock_id,
                    "現價": price,
                    "損益": profit,
                    "報酬率(%)": round((profit/m_cost)*100, 2) if m_cost>0 else 0,
                    "預估股息(總額)": int(est_div_total),
                    "每股股利": f"{final_div_rate} ({source_msg})" # 顯示是自動抓還是手動的
                })
                
        except Exception:
            pass
        
        if total_rows > 0:
            progress_bar.progress((index + 1) / total_rows)

    # 看板區
    c1, c2, c3 = st.columns(3)
    c1.metric("💰 總市值", f"{int(total_market_value):,} 元")
    
    profit = total_market_value - total_cost
    c2.metric("📈 總損益", f"{int(profit):,} 元", 
              delta=f"{(profit/total_cost)*100:.1f}%" if total_cost>0 else "0%",
              delta_color="inverse")
    
    c3.metric("🧧 預估年股息", f"{int(total_dividends):,} 元", help="手動輸入優先，若為0則自動抓取")

    if results:
        st.divider()
        res_df = pd.DataFrame(results)
        def color_profit(val):
            return f'color: {"red" if val > 0 else "green"}'
        
        st.dataframe(
            res_df.style.map(color_profit, subset=['損益', '報酬率(%)'])
                     .format({"現價": "{:.2f}", "損益": "{:,.0f}", "預估股息(總額)": "{:,.0f}"}),
            use_container_width=True
        )
