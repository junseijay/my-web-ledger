import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
import json

# 1. 페이지 설정 및 제목
st.set_page_config(page_title="사장님 전용 웹 장부", layout="wide")
st.title("📱 스마트폰 연동 매출 장부")

# 2. 구글 시트 연결 시도
try:
    conn = st.connection("gsheets", type=GSheetsConnection)
except Exception as e:
    st.error("Secrets 설정에 문제가 있습니다. 설정을 다시 확인해주세요!")
    st.stop()

# 3. 데이터 로드 함수 (에러 방지형)
def load_data():
    try:
        df = conn.read(worksheet="sales", ttl=0)
        if df is None or df.empty:
            return pd.DataFrame(columns=['날짜','홀매출','배달매출','비용내역','총비용'])
        return df
    except Exception:
        st.warning("구글 시트에서 데이터를 가져올 수 없습니다. '편집자' 공유 권한을 확인하세요!")
        return pd.DataFrame(columns=['날짜','홀매출','배달매출','비용내역','총비용'])

# 4. 저장 함수
def save_entry():
    try:
        df = load_data()
        new_row = pd.DataFrame({
            '날짜': [str(st.session_state.date_in)],
            '홀매출': [st.session_state.h_in],
            '배달매출': [st.session_state.d_in],
            '비용내역': ["[]"],
            '총비용': [0]
        })
        updated_df = pd.concat([df, new_row], ignore_index=True)
        conn.update(worksheet="sales", data=updated_df)
        st.success("성공적으로 저장되었습니다! ☁️")
    except Exception as e:
        st.error(f"저장 실패! 구글 시트 공유 설정을 '편집자'로 바꿨는지 확인하세요.")

# 5. 스마트폰 최적화 입력창
with st.container(border=True):
    st.subheader("오늘의 실적 입력")
    st.date_input("날짜 선택", key="date_in")
    st.number_input("홀 매출액", min_value=0, step=1000, key="h_in")
    st.number_input("배달 매출액", min_value=0, step=1000, key="d_in")
    st.button("시트에 기록하기", type="primary", use_container_width=True, on_click=save_entry)

# 6. 데이터 보기
st.divider()
st.subheader("📊 저장된 데이터 확인")
st.dataframe(load_data(), use_container_width=True)