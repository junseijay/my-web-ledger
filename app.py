import streamlit as st
import pandas as pd
import calendar
from datetime import datetime
import json
from streamlit_gsheets import GSheetsConnection

# 1. 페이지 설정
st.set_page_config(page_title="우리매장 통합 관리 시스템", layout="wide")

# 2. 구글 시트 연결 설정
try:
    conn = st.connection("gsheets", type=GSheetsConnection)
except Exception as e:
    st.error("Secrets 설정을 확인해주세요.")
    st.stop()

# --- 3. 데이터 로직 함수 ---
def load_data():
    try:
        # worksheet="sales" 탭에서 데이터를 가져옵니다.
        df = conn.read(worksheet="sales", ttl=0)
        if df is None or df.empty:
            return pd.DataFrame(columns=['날짜','홀매출','배달매출','배달건수','예상지급액','비용내역','총비용'])
        df['날짜'] = pd.to_datetime(df['날짜']).dt.date
        return df
    except Exception:
        return pd.DataFrame(columns=['날짜','홀매출','배달매출','배달건수','예상지급액','비용내역','총비용'])

def save_data(new_df):
    try:
        conn.update(worksheet="sales", data=new_df)
        st.cache_data.clear()
        return True
    except Exception as e:
        st.error(f"저장 실패: {e}")
        return False

# --- 4. 콜백 함수 (성공했던 코드의 로직 그대로) ---
if 'temp_costs' not in st.session_state:
    st.session_state.temp_costs = []

def add_cost_callback():
    if st.session_state.input_c_name and st.session_state.input_c_amount > 0:
        st.session_state.temp_costs.append({"항목": st.session_state.input_c_name, "금액": st.session_state.input_c_amount})
    st.session_state.input_c_name, st.session_state.input_c_amount = "", 0

def save_and_clear_callback(input_date):
    h, d, count = st.session_state.input_h_sales, st.session_state.input_d_sales, st.session_state.input_d_count
    pay = d - (d * 0.078) - (count * 3100)
    
    df = load_data()
    df = df[df['날짜'] != input_date] # 기존 데이터가 있으면 교체
    
    new_row = pd.DataFrame({
        '날짜': [input_date], 
        '홀매출': [h], 
        '배달매출': [d], 
        '배달건수': [count],
        '예상지급액': [pay], 
        '비용내역': [json.dumps(st.session_state.temp_costs, ensure_ascii=False)],
        '총비용': [sum(c['금액'] for c in st.session_state.temp_costs)]
    })
    
    final_df = pd.concat([df, new_row], ignore_index=True).sort_values('날짜')
    if save_data(final_df):
        st.session_state.input_h_sales, st.session_state.input_d_sales, st.session_state.input_d_count = 0, 0, 0
        st.session_state.temp_costs = []
        st.toast("구글 시트에 저장 완료! ☁️")

def delete_callback(date_obj):
    df = load_data()
    final_df = df[df['날짜'] != date_obj]
    if save_data(final_df):
        st.toast("삭제 완료 🗑️")

# --- 5. 메인 화면 구성 ---
df = load_data()

with st.sidebar:
    st.header("📝 오늘의 기록")
    curr_date = st.date_input("날짜 선택", datetime.now().date())
    st.number_input("홀 매출", min_value=0, step=1000, key="input_h_sales")
    st.number_input("배달 매출(원금)", min_value=0, step=1000, key="input_d_sales")
    st.number_input("배달 건수", min_value=0, step=1, key="input_d_count")
    st.divider()
    st.text_input("지출 항목명", key="input_c_name")
    st.number_input("지출 금액", min_value=0, step=100, key="input_c_amount")
    st.button("➕ 비용 추가", on_click=add_cost_callback, use_container_width=True)
    if st.session_state.temp_costs:
        for c in st.session_state.temp_costs: st.caption(f"• {c['항목']}: {c['금액']:,}원")
    st.button("💾 최종 데이터 저장", type="primary", use_container_width=True, on_click=save_and_clear_callback, args=(curr_date,))

# --- 6. 달력 UI ---
st.title("📅 월간 성과 분석 달력")
y_col, m_col = st.columns(2)
year = y_col.selectbox("연도", range(2024, 2030), index=datetime.now().year - 2024)
month = m_col.selectbox("월", range(1, 13), index=datetime.now().month - 1)

calendar.setfirstweekday(6)
cal = calendar.monthcalendar(year, month)
days = ["일", "월", "화", "수", "목", "금", "토"]
h_cols = st.columns(7)
for i, d in enumerate(days):
    color = "#FF4B4B" if i == 0 else ("#1C83E1" if i == 6 else "#31333F")
    h_cols[i].markdown(f"<p style='text-align:center; font-weight:bold; color:{color};'>{d}</p>", unsafe_allow_html=True)

for week in cal:
    cols = st.columns(7)
    for i, day in enumerate(week):
        with cols[i]:
            if day != 0:
                date_obj = datetime(year, month, day).date()
                day_data = df[df['날짜'] == date_obj]
                with st.container(border=True):
                    d_col, b_col = st.columns([3, 1])
                    d_col.write(f"**{day}**")
                    if not day_data.empty:
                        b_col.button("X", key=f"del_{date_obj}", on_click=delete_callback, args=(date_obj,))
                        row = day_data.iloc[0]
                        st.markdown(f"<p style='font-size:11px; color:#2E7D32; margin:0;'>홀:{row['홀매출']:,}</p>", unsafe_allow_html=True)
                        st.markdown(f"<p style='font-size:11px; color:#1C83E1; margin:0;'>배달:{row['배달매출']:,}</p>", unsafe_allow_html=True)
                        st.markdown(f"<p style='font-size:11px; color:#D32F2F; margin:0;'>비용:{row['총비용']:,}</p>", unsafe_allow_html=True)

# --- 7. 종합 리포트 ---
st.divider()
st.subheader(f"📊 {month}월 실적 리포트")
m_df = df[(pd.to_datetime(df['날짜']).dt.year == year) & (pd.to_datetime(df['날짜']).dt.month == month)].sort_values('날짜').copy()

if not m_df.empty:
    m_df['당일총매출'] = m_df['홀매출'] + m_df['배달매출']
    total_sales = m_df['당일총매출'].sum()
    total_profit = total_sales - m_df['총비용'].sum()
    
    r1c1, r1c2, r1c3, r1c4 = st.columns(4)
    r1c1.metric("월 총 매출액", f"{total_sales:,}원")
    r1c2.metric("월 홀 매출", f"{m_df['홀매출'].sum():,}원")
    r1c3.metric("월 배달 매출", f"{m_df['배달매출'].sum():,}원")
    r1c4.metric("월 누적 순수익", f"{total_profit:,}원")
    
    st.dataframe(m_df[['날짜', '홀매출', '배달매출', '총비용', '예상지급액']], use_container_width=True)
else:
    st.info("데이터가 없습니다.")