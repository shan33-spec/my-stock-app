import streamlit as st
import yfinance as yf
import pandas as pd

# 1. 頁面設定
st.set_page_config(page_title="股票包租公試算", page_icon="💰")

st.title("💰 我的股票紀錄")
st.markdown("輸入多檔持股，一次計算 **總庫存損益** 與 **預估年領股息**。")

# 2. 建立輸入表格 (預設給您三個範例，您可以自己改)
default_data = pd.DataFrame([
    {"代號": "2330", "成本": 600.0, "股數": 1000},
    {"代號": "2891", "成本": 25.0, "股數": 5000},
    {"代號": "0056", "成本": 30.0, "股數": 2000},
])

st.subheader("1. 編輯您的持股清單")
st.info("💡 操作教學：直接點擊表格內容即可修改。按表格下方的 `+` 可以新增一列。")

# 顯示可編輯的表格
portfolio_df = st.data_editor(
    default_data, 
    num_rows="dynamic", # 允許使用者新增或刪除列
    column_config={
        "代號": st.column_config.TextColumn(help="請輸入台股代號，如 2330"),
        "成本": st.column_config.NumberColumn(format="$%.1f"),
        "股數": st.column_config.NumberColumn(format="%d"),
    }
)

# 3. 按鈕觸發計算
if st.button("開始計算資產與配息 🚀", type="primary"):
    
    st.divider()
    st.subheader("2. 試算結果")
    
    # 準備變數來存總數
    total_market_value = 0  # 總市值
    total_cost = 0          # 總成本
    total_dividends = 0     # 總預估股息
    results = []            # 存每一檔的詳細資料

    # 進度條 (因為多檔股票跑起來會比較慢)
    progress_bar = st.progress(0)
    
    # 逐一處理每一列股票
    for index, row in portfolio_df.iterrows():
        stock_id = str(row["代號"]).strip()
        cost = float(row["成本"])
        qty = int(row["股數"])
        
        if not stock_id: # 如果代號是空的就跳過
            continue
            
        # 處理代號 (加上 .TW)
        ticker = f"{stock_id}.TW"
        # 上櫃股票簡單判斷 (如果代號是4碼且開頭是6或8或5，有可能是上櫃，這裡先預設都當上市，若抓不到可手動改代碼)
        # 為了簡化，我們主要跑 .TW。若要精準，使用者可在表格輸入 '5347.TWO'
        if ".TWO" in stock_id:
             ticker = stock_id
        
        try:
            stock = yf.Ticker(ticker)
            info = stock.info
            
            # 抓現價
            price = info.get('currentPrice') or info.get('regularMarketPrice')
            
            # 抓配息 (近一年)
            dividend_rate = info.get('dividendRate', 0)
            if dividend_rate is None: dividend_rate = 0
            
            if price:
                # 計算單檔數值
                market_val = price * qty
                my_cost = cost * qty
                profit = market_val - my_cost
                est_div = dividend_rate * qty
                
                # 累加到總數
                total_market_value += market_val
                total_cost += my_cost
                total_dividends += est_div
                
                # 存入結果清單
                results.append({
                    "股票": f"{info.get('longName', stock_id)} ({stock_id})",
                    "現價": price,
                    "損益": profit,
                    "報酬率(%)": round((profit/my_cost)*100, 2) if my_cost > 0 else 0,
                    "預估股息(元)": int(est_div)
                })
        except Exception as e:
            st.error(f"代號 {stock_id} 抓取失敗，請檢查代號。")
        
        # 更新進度條
        progress_bar.progress((index + 1) / len(portfolio_df))

    # --- 顯示總資產看板 ---
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("💰 股票總市值", f"{int(total_market_value):,} 元")
    
    with col2:
        total_profit = total_market_value - total_cost
        color = "inverse" # 台股紅賺綠賠
        st.metric("📈 總未實現損益", f"{int(total_profit):,} 元", delta=f"{(total_profit/total_cost)*100:.1f}%" if total_cost>0 else "0%", delta_color=color)

    with col3:
        st.metric("🧧 預估年領股息", f"{int(total_dividends):,} 元", help="根據最近一年配息金額估算")

    st.divider()
    
    # --- 顯示詳細表格 ---
    if results:
        st.write("📋 **持股詳細清單**")
        result_df = pd.DataFrame(results)
        
        # 格式化顯示 (讓損益有顏色)
        def color_profit(val):
            color = 'red' if val > 0 else 'green' if val < 0 else 'black'
            return f'color: {color}'

        # 顯示漂亮的表格
        st.dataframe(
            result_df.style.map(color_profit, subset=['損益', '報酬率(%)'])
                     .format({"現價": "{:.2f}", "損益": "{:,.0f}", "預估股息(元)": "{:,.0f}"}),
            use_container_width=True
        )
    else:
        st.warning("沒有抓到任何資料，請檢查代號是否正確。")