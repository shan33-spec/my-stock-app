import streamlit as st
import yfinance as yf
import pandas as pd

# 1. 頁面設定
st.set_page_config(page_title="股票包租公 (防呆版)", page_icon="🛡️")

st.title("🛡️ 我的股票包租公")
st.markdown("已修復 **空行崩潰** 問題，輸入更順暢！")

# --- 側邊欄：存檔與讀檔 ---
st.sidebar.header("📂 檔案存取")
uploaded_file = st.sidebar.file_uploader("讀取舊檔案 (CSV)", type=["csv"])

# 預設持股
if uploaded_file is None:
    # 這裡的數字只是範例，您可以改成全是 0 或空字串
    default_data = pd.DataFrame([
        {"代號": "0056", "成本": 30.0, "股數": 1000},
        {"代號": "00878", "成本": 18.0, "股數": 2000},
        {"代號": "00919", "成本": 22.0, "股數": 1000},
    ])
else:
    try:
        default_data = pd.read_csv(uploaded_file)
        default_data["代號"] = default_data["代號"].astype(str)
    except:
        st.error("檔案格式有誤。")
        default_data = pd.DataFrame([{"代號": "", "成本": 0.0, "股數": 0}])

# 編輯表格
st.info("👇 請在此輸入您的持股。若有「空行」請直接忽略，系統會自動跳過。")
edited_df = st.data_editor(
    default_data, 
    num_rows="dynamic", # 允許新增刪除
    column_config={
        "代號": st.column_config.TextColumn(help="股票代號"),
        "成本": st.column_config.NumberColumn(format="$%.2f"), # 顯示兩位小數
        "股數": st.column_config.NumberColumn(format="%d"),
    },
    key="my_editor" # 設定 key 避免輸入時一直重整
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
    
    # 進度條
    progress_bar = st.progress(0)
    
    # 準備迭代 (總行數)
    total_rows = len(edited_df)
    
    for index, row in edited_df.iterrows():
        # --- [關鍵修正] 防呆檢查區 ---
        # 1. 檢查是否為空值 (None) 或 空字串
        if pd.isna(row["代號"]) or pd.isna(row["股數"]) or str(row["代號"]).strip() == "":
            continue # 如果這行是空的，直接跳過，不執行下面程式
            
        stock_id = str(row["代號"]).strip()
        
        # 2. 嘗試把數字轉成格式，如果失敗(例如使用者輸入中文)也跳過
        try:
            cost = float(row["成本"])
            qty = int(row["股數"])
        except:
            continue
            
        # 3. 補零處理 (例如 56 -> 0056)
        if len(stock_id) < 4: stock_id = stock_id.zfill(4)
        
        # 處理代號
        ticker = f"{stock_id}.TW"
        if ".TWO" in stock_id: ticker = stock_id 
        
        try:
            stock = yf.Ticker(ticker)
            
            # 強力抓取邏輯
            price = None
            stock_name = stock_id
            
            # 方法 A: fast_info
            try:
                price = stock.fast_info['last_price']
            except:
                pass
            
            # 方法 B: history
            if price is None:
                try:
                    hist = stock.history(period="1d")
                    if not hist.empty:
                        price = hist['Close'].iloc[-1]
                except:
                    pass

            # 抓名稱與配息
            try:
                info = stock.info 
                stock_name = info.get('longName', stock_id)
                div_rate = info.get('dividendRate', 0)
            except:
                div_rate = 0 
                
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
                
        except Exception as e:
            pass # 這一行失敗就算了，繼續下一行
        
        # 更新進度條
        if total_rows > 0:
            progress_bar.progress((index + 1) / total_rows)

    # 看板區
    c1, c2, c3 = st.columns(3)
    c1.metric("💰 總市值", f"{int(total_market_value):,} 元")
    
    profit = total_market_value - total_cost
    c2.metric("📈 總損益", f"{int(profit):,} 元", 
              delta=f"{(profit/total_cost)*100:.1f}%" if total_cost>0 else "0%",
              delta_color="inverse")
    
    c3.metric("🧧 預估年股息", f"{int(total_dividends):,} 元")

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
