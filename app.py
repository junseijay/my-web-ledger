import streamlit as st
import pandas as pd
import calendar
from datetime import datetime
import json
from streamlit_gsheets import GSheetsConnection

# 1. 페이지 설정 및 모바일 최적화 스타일
st.set_page_config(page_title="우리매장 웹 장부", layout="wide")

st.markdown("""
    <style>
    @media (max-width: 768px) {
        .stMetric div div { font-size: 0.8rem !important; }
        [data-testid="column"] { width: 100% !important; flex: 1 1 100% !important; }
    }
    </style>
    """, unsafe_allow_html=True)

# 2. 구글 시트 연결
try:
    conn = st.connection("gsheets", type=GSheetsConnection)
except Exception:
    st.error("Secrets 설정을 확인해주세요.")
    st.stop()

def load_data():
    try:
        df = conn.read(worksheet="sales", ttl=0)
        if df is None or df.empty:
            return pd.DataFrame(columns=['날짜','홀매출','배달매출','배달건수','예상지급액','비용내역','총비용'])
        df['날짜'] = pd.to_datetime(df['날짜']).dt.date
        return df
    except:
        return pd.DataFrame(columns=['날짜','홀매출','배달매출','배달건수','예상지급액','비용내역','총비용'])

# 세션 초기화 (에러 방지)
if 'temp_costs' not in st.session_state: st.session_state.temp_costs = []

def save_and_clear_callback(input_date):
    try:
        h = st.session_state.get('input_h_sales', 0)
        d = st.session_state.get('input_d_sales', 0)
        count = st.session_state.get('input_d_count', 0)
        
        pay = d - (d * 0.078) - (count * 3100)
        df = load_data()
        df = df[df['날짜'] != input_date]
        
        new_row = pd.DataFrame({
            '날짜': [input_date], '홀매출': [h], '배달매출': [d], '배달건수': [count],
            '예상지급액': [pay], 
            '비용내역': [json.dumps(st.session_state.temp_costs, ensure_ascii=False)],
            '총비용': [sum(c['금액'] for c in st.session_state.temp_costs)]
        })
        
        conn.update(worksheet="sales", data=pd.concat([df, new_row], ignore_index=True))
        st.cache_data.clear()
        st.session_state.temp_costs = []
        st.toast("저장 성공! 💾")
    except Exception as e:
        st.error("저장에 실패했습니다. 구글 시트의 '편집자' 권한을 확인하세요.")

# --- 메인 화면 ---
df = load_data()

with st.sidebar:
    st.header("📝 실적 기록")
    curr_date = st.date_input("날짜 선택", datetime.now().date())
    st.number_input("홀 매출", min_value=0, step=1000, key="input_h_sales")
    st.number_input("배달 매출", min_value=0, step=1000, key="input_d_sales")
    st.number_input("배달 건수", min_value=0, step=1, key="input_d_count")
    st.divider()
    # 비용 입력 (에러 수정됨)
    c_name = st.text_input("지출 항목명", value="")
    c_amt = st.number_input("지출 금액", min_value=0, step=100)
    if st.button("➕ 비용 추가", use_container_width=True):
        if c_name and c_amt > 0:
            st.session_state.temp_costs.append({"항목": c_name, "금액": c_amt})
    
    if st.session_state.temp_costs:
        for c in st.session_state.temp_costs: st.caption(f"• {c['항목']}: {c['금액']:,}원")
    
    st.button("💾 구글 시트 저장", type="primary", use_container_width=True, 
              on_click=save_and_clear_callback, args=(curr_date,))

# 달력 및 리포트 화면
st.title("📅 월간 성과 분석")
year = st.selectbox("연도", range(2024, 2030), index=datetime.now().year - 2024)
month = st.selectbox("월", range(1, 13), index=datetime.now().month - 1)

# (이하 달력 그리기 로직은 이전과 동일하게 유지)
calendar.setfirstweekday(6)
cal = calendar.monthcalendar(year, month)
days = ["일", "월", "화", "수", "목", "금", "토"]
cols = st.columns(7)
for i, d in enumerate(days):
    color = "#FF4B4B" if i == 0 else ("#1C83E1" if i == 6 else "#31333F")
    cols[i].markdown(f"<p style='text-align:center; font-weight:bold; color:{color}; font-size:12px;'>{d}</p>", unsafe_allow_html=True)

for week in cal:
    cols = st.columns(7)
    for i, day in enumerate(week):
        with cols[i]:
            if day != 0:
                date_obj = datetime(year, month, day).date()
                day_data = df[df['날짜'] == date_obj]
                with st.container(border=True):
                    st.write(f"**{day}**")
                    if not day_data.empty:
                        row = day_data.iloc[0]
                        st.markdown(f"<div style='font-size:10px; line-height:1.1;'>"
                                    f"<p style='color:#2E7D32; margin:0;'>홀:{row['홀매출']//1000}k</p>"
                                    f"<p style='color:#1C83E1; margin:0;'>배:{row['배달매출']//1000}k</p></div>", unsafe_allow_html=True)