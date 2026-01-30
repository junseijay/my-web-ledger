import streamlit as st
import pandas as pd
import calendar
from datetime import datetime
import json
from streamlit_gsheets import GSheetsConnection

# 1. 페이지 설정
st.set_page_config(page_title="우리매장 웹 장부", layout="wide")

# 2. 구글 시트 연결 (Secrets 설정 필수)
conn = st.connection("gsheets", type=GSheetsConnection)

def load_data():
    try:
        # 데이터 읽기 (시트 이름이 'sales'인지 꼭 확인하세요)
        df = conn.read(worksheet="sales", ttl=0)
        if df is None or df.empty:
            return pd.DataFrame(columns=['날짜','홀매출','배달매출','배달건수','예상지급액','비용내역','총비용'])
        df['날짜'] = pd.to_datetime(df['날짜']).dt.date
        return df
    except Exception:
        return pd.DataFrame(columns=['날짜','홀매출','배달매출','배달건수','예상지급액','비용내역','총비용'])

def save_data(new_df):
    # 구글 시트에 업데이트 (편집자 권한 필수)
    conn.update(worksheet="sales", data=new_df)
    st.cache_data.clear()

# --- 초기 상태 설정 ---
if 'temp_costs' not in st.session_state: st.session_state.temp_costs = []

def save_and_clear_callback(input_date):
    h, d, count = st.session_state.input_h_sales, st.session_state.input_d_sales, st.session_state.input_d_count
    pay = d - (d * 0.078) - (count * 3100)
    df = load_data()
    df = df[df['날짜'] != input_date]
    new_row = pd.DataFrame({
        '날짜': [input_date], '홀매출': [h], '배달매출': [d], '배달건수': [count],
        '예상지급액': [pay], '비용내역': [json.dumps(st.session_state.temp_costs, ensure_ascii=False)],
        '총비용': [sum(c['금액'] for c in st.session_state.temp_costs)]
    })
    final_df = pd.concat([df, new_row], ignore_index=True)
    save_data(final_df)
    st.session_state.temp_costs = []
    st.toast("구글 시트에 저장되었습니다! ☁️")

# --- 화면 구성 ---
df = load_data()

with st.sidebar:
    st.header("📝 오늘의 기록")
    curr_date = st.date_input("날짜 선택", datetime.now().date())
    st.number_input("홀 매출", min_value=0, step=1000, key="input_h_sales")
    st.number_input("배달 매출(원금)", min_value=0, step=1000, key="input_d_sales")
    st.number_input("배달 건수", min_value=0, step=1, key="input_d_count")
    st.button("💾 클라우드 저장", type="primary", use_container_width=True, on_click=save_and_clear_callback, args=(curr_date,))

st.title("📅 월간 성과 분석 달력 (Web)")
# (달력 및 리포트 로직 생략 - 저장 기능 확인 후 필요시 추가)