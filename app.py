import streamlit as st
import pandas as pd
import calendar
from datetime import datetime
import json
from streamlit_gsheets import GSheetsConnection

# 1. 페이지 설정
st.set_page_config(page_title="우리매장 웹 장부", layout="wide")

# 2. 구글 스프레드시트 연결 설정
# 웹 배포 시 .streamlit/secrets.toml 또는 대시보드 설정을 통해 연결 정보를 입력해야 합니다.
conn = st.connection("gsheets", type=GSheetsConnection)

def load_data():
    try:
        # 'sales' 시트에서 데이터를 읽어옴
        df = conn.read(worksheet="sales")
        df['날짜'] = pd.to_datetime(df['날짜']).dt.date
        return df
    except:
        return pd.DataFrame(columns=['날짜','홀매출','배달매출','배달건수','예상지급액','비용내역','총비용'])

def save_data(new_df):
    # 전체 데이터를 구글 시트에 다시 씀 (업데이트)
    conn.update(worksheet="sales", data=new_df)
    st.cache_data.clear()

# --- 세션 상태 초기화 ---
for key in ['temp_costs', 'input_h_sales', 'input_d_sales', 'input_d_count', 'input_c_name', 'input_c_amount']:
    if key not in st.session_state:
        st.session_state[key] = [] if key == 'temp_costs' else (0 if 'sales' in key or 'count' in key or 'amount' in key else "")

# --- 비즈니스 로직 ---
def add_cost_callback():
    if st.session_state.input_c_name and st.session_state.input_c_amount > 0:
        st.session_state.temp_costs.append({"항목": st.session_state.input_c_name, "금액": st.session_state.input_c_amount})
    st.session_state.input_c_name, st.session_state.input_c_amount = "", 0

def save_and_clear_callback(input_date):
    h, d, count = st.session_state.input_h_sales, st.session_state.input_d_sales, st.session_state.input_d_count
    pay = d - (d * 0.078) - (count * 3100)
    
    df = load_data()
    # 동일 날짜 데이터가 있으면 삭제 후 재삽입 (수정 기능)
    df = df[df['날짜'] != input_date]
    
    new_row = pd.DataFrame({
        '날짜': [input_date], '홀매출': [h], '배달매출': [d], '배달건수': [count],
        '예상지급액': [pay], '비용내역': [json.dumps(st.session_state.temp_costs, ensure_ascii=False)],
        '총비용': [sum(c['금액'] for c in st.session_state.temp_costs)]
    })
    
    final_df = pd.concat([df, new_row], ignore_index=True)
    save_data(final_df)
    
    st.session_state.input_h_sales, st.session_state.input_d_sales, st.session_state.input_d_count, st.session_state.temp_costs = 0, 0, 0, []
    st.toast("구글 시트에 저장되었습니다! ☁️")

def delete_callback(date_obj):
    df = load_data()
    final_df = df[df['날짜'] != date_obj]
    save_data(final_df)
    st.toast("삭제 완료")

# --- 메인 화면 구성 (기존 UI 유지) ---
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
    st.button("☁️ 웹 서버 저장", type="primary", use_container_width=True, on_click=save_and_clear_callback, args=(curr_date,))

# (이후 달력 및 리포트 UI 코드는 이전과 동일하게 유지됩니다)
st.title("📅 월간 성과 분석 달력 (Web)")
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

# 리포트 섹션 (생략, 이전 로직과 동일)
st.divider()
st.info("웹 버전에서는 데이터가 구글 스프레드시트와 실시간 연동됩니다.")