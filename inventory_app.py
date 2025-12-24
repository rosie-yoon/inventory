import streamlit as st
import pandas as pd
from datetime import datetime
import time

# 페이지 설정
st.set_page_config(page_title="재고 관리 시스템", layout="wide")

# 스타일 설정 (프린트 최적화 및 디자인)
st.markdown("""
    <style>
    .main {
        background-color: #f8fafc;
    }
    @media print {
        .stButton, .stFileUploader, section[data-testid="stSidebar"] {
            display: none !important;
        }
    }
    .stock-card {
        background-color: white;
        padding: 1.5rem;
        border-radius: 1rem;
        border: 1px solid #e2e8f0;
        margin-bottom: 1rem;
    }
    </style>
    """, unsafe_allow_html=True)

# --- 데이터 관리 로직 ---
# 실제 상용 환경에서는 st.connection("gsheets", ...)를 사용하여 구글 시트와 연결하는 것이 좋습니다.
# 여기서는 세션 스테이트를 이용한 데모 버전을 작성합니다.

if 'inventory' not in st.session_state:
    st.session_state.inventory = pd.DataFrame(columns=['SKU', '상품명', '이미지URL', '현재재고', '최근수정일'])
    # 샘플 데이터
    sample_data = pd.DataFrame([
        ['LPT-001', '맥북 프로 M3', 'https://images.unsplash.com/photo-1517336714731-489689fd1ca8?w=200', 10, datetime.now().strftime("%Y-%m-%d")],
        ['MS-99', '로지텍 마우스', 'https://images.unsplash.com/photo-1527864550417-7fd91fc51a46?w=200', 25, datetime.now().strftime("%Y-%m-%d")]
    ], columns=['SKU', '상품명', '이미지URL', '현재재고', '최근수정일'])
    st.session_state.inventory = pd.concat([st.session_state.inventory, sample_data], ignore_index=True)

if 'history' not in st.session_state:
    st.session_state.history = []

# --- 사이드바: 상품 등록 ---
with st.sidebar:
    st.header("📦 새 상품 등록")
    with st.form("add_form", clear_on_submit=True):
        new_sku = st.text_input("SKU (코드)")
        new_name = st.text_input("상품명")
        new_img = st.text_input("이미지 URL (직접 링크)")
        new_qty = st.number_input("초기 수량", min_value=0, step=1)
        submit = st.form_submit_button("상품 추가")
        
        if submit:
            new_row = pd.DataFrame([[new_sku, new_name, new_img, new_qty, datetime.now().strftime("%Y-%m-%d")]], 
                                  columns=['SKU', '상품명', '이미지URL', '현재재고', '최근수정일'])
            st.session_state.inventory = pd.concat([st.session_state.inventory, new_row], ignore_index=True)
            st.success(f"{new_name} 등록 완료!")

    st.divider()
    st.header("📤 엑셀 벌크 업로드")
    uploaded_file = st.file_uploader("엑셀 파일을 선택하세요", type=["xlsx", "csv"])
    if uploaded_file:
        try:
            df = pd.read_excel(uploaded_file) if uploaded_file.name.endswith('xlsx') else pd.read_csv(uploaded_file)
            st.session_state.inventory = pd.concat([st.session_state.inventory, df], ignore_index=True).drop_duplicates('SKU', keep='last')
            st.success("벌크 로드 성공!")
        except Exception as e:
            st.error("파일 형식을 확인해주세요.")

# --- 메인 화면 ---
st.title("🍎 클라우드 재고 관리 시스템")
st.caption("맥북, 아이패드, 아이폰에서 실시간으로 확인하는 재고 현황")

col1, col2 = st.columns([3, 1])

with col1:
    st.subheader("📊 실시간 재고 리스트")
    
    # 검색 기능
    search = st.text_input("🔍 상품명 또는 SKU 검색", "")
    filtered_df = st.session_state.inventory[
        st.session_state.inventory['상품명'].str.contains(search, case=False) | 
        st.session_state.inventory['SKU'].str.contains(search, case=False)
    ]

    # 재고 목록 표시
    for idx, row in filtered_df.iterrows():
        with st.container():
            c1, c2, c3, c4, c5 = st.columns([1, 2, 2, 2, 1])
            
            with c1:
                st.image(row['이미지URL'], width=80)
            
            with c2:
                st.markdown(f"**{row['상품명']}**")
                st.caption(f"SKU: {row['SKU']}")
            
            with c3:
                st.markdown(f"현재 재고: **{row['현재재고']}**개")
                if row['현재재고'] < 5:
                    st.error("⚠️ 재고 부족")
            
            with c4:
                # 수량 조절
                sub_col1, sub_col2 = st.columns(2)
                if sub_col1.button("➕ 입고", key=f"in_{idx}"):
                    st.session_state.inventory.at[idx, '현재재고'] += 1
                    st.session_state.inventory.at[idx, '최근수정일'] = datetime.now().strftime("%Y-%m-%d")
                    st.rerun()
                if sub_col2.button("➖ 출고", key=f"out_{idx}"):
                    if st.session_state.inventory.at[idx, '현재재고'] > 0:
                        st.session_state.inventory.at[idx, '현재재고'] -= 1
                        st.session_state.inventory.at[idx, '최근수정일'] = datetime.now().strftime("%Y-%m-%d")
                        st.rerun()
            
            with c5:
                if st.button("🗑️", key=f"del_{idx}"):
                    st.session_state.inventory = st.session_state.inventory.drop(idx)
                    st.rerun()
            st.divider()

with col2:
    st.subheader("🖨️ 인쇄용 요약")
    st.info("브라우저의 인쇄 기능(Cmd+P)을 사용하세요.")
    
    # 인쇄용 데이터프레임
    print_df = st.session_state.inventory[['SKU', '상품명', '현재재고', '최근수정일']]
    st.dataframe(print_df, use_container_width=True, hide_index=True)
    
    # 엑셀 다운로드 버튼
    csv = print_df.to_csv(index=False).encode('utf-8-sig')
    st.download_button(
        label="📄 현재 리스트 다운로드 (CSV)",
        data=csv,
        file_name=f"inventory_{datetime.now().strftime('%Y%m%d')}.csv",
        mime="text/csv",
    )

st.sidebar.markdown("---")
st.sidebar.caption("v1.0 Streamlit Inventory Cloud")