import streamlit as st
import pandas as pd
from datetime import datetime
import io

# 1. 페이지 설정 (사이드바 기본 접힘)
st.set_page_config(
    page_title="재고 관리 시스템", 
    layout="wide",
    initial_sidebar_state="collapsed"
)

# 2. 스타일 설정 (대시보드 디자인 최적화)
st.markdown("""
    <style>
    /* 화면 배경색 */
    .main { background-color: #f8fafc; }
    
    /* 카드형 컨테이너 스타일 */
    .inventory-card {
        background-color: white;
        padding: 20px;
        border-radius: 12px;
        border: 1px solid #e2e8f0;
        margin-bottom: 10px;
    }
    
    .stNumberInput div div input { font-weight: bold; }
    
    /* 버튼 스타일 조정 */
    .stButton>button {
        border-radius: 8px;
    }
    </style>
    """, unsafe_allow_html=True)

# --- 데이터 관리 로직 ---
if 'inventory' not in st.session_state:
    st.session_state.inventory = pd.DataFrame(columns=['SKU', '상품명', '이미지URL', '현재재고', '최근수정일'])

# --- 사이드바: 상품 관리 ---
with st.sidebar:
    st.header("📦 상품 관리")
    with st.form("add_form", clear_on_submit=True):
        st.subheader("새 상품 등록")
        new_sku = st.text_input("SKU (코드)")
        new_name = st.text_input("상품명")
        new_img = st.text_input("이미지 URL")
        new_qty = st.number_input("현재 재고", min_value=0, step=1)
        if st.form_submit_button("등록"):
            if new_sku and new_name:
                new_row = pd.DataFrame([[new_sku, new_name, new_img, new_qty, datetime.now().strftime("%Y-%m-%d")]], 
                                      columns=['SKU', '상품명', '이미지URL', '현재재고', '최근수정일'])
                st.session_state.inventory = pd.concat([st.session_state.inventory, new_row], ignore_index=True).drop_duplicates('SKU', keep='last')
                st.success(f"'{new_name}' 상품이 등록되었습니다.")

    st.divider()
    st.subheader("📤 엑셀 벌크 업로드")
    uploaded_file = st.file_uploader("파일 선택 (.xlsx, .csv)", type=["xlsx", "csv"])
    if uploaded_file:
        try:
            if uploaded_file.name.endswith('xlsx'):
                df = pd.read_excel(uploaded_file, engine='openpyxl')
            else:
                df = pd.read_csv(uploaded_file)
            
            # 유연한 헤더 매핑
            df = df.rename(columns={
                'SKU': 'SKU', 
                '상품명': '상품명', 
                '이미지 URL': '이미지URL', 
                '이미지URL': '이미지URL',
                '초기 수량': '현재재고', 
                '수량': '현재재고'
            })
            
            if '최근수정일' not in df.columns: 
                df['최근수정일'] = datetime.now().strftime("%Y-%m-%d")
            if '이미지URL' not in df.columns:
                df['이미지URL'] = ""
                
            # 필수 컬럼만 추출
            target_cols = ['SKU', '상품명', '이미지URL', '현재재고', '최근수정일']
            df_final = df[df.columns.intersection(target_cols)]
            
            st.session_state.inventory = pd.concat([st.session_state.inventory, df_final], ignore_index=True).drop_duplicates('SKU', keep='last')
            st.success(f"{len(df_final)}개 품목 업로드 완료!")
        except Exception as e:
            st.error(f"파일을 읽는 중 오류가 발생했습니다: {e}")

# --- 메인 화면 ---
st.title("🍎 스마트 재고 관리 대시보드")
st.caption("실시간으로 재고를 파악하고 관리하세요.")

# 검색창
search = st.text_input("🔍 상품명 또는 SKU로 검색", "")
view_df = st.session_state.inventory[
    st.session_state.inventory['상품명'].str.contains(search, case=False, na=False) |
    st.session_state.inventory['SKU'].str.contains(search, case=False, na=False)
].reset_index(drop=True)

# 요약 지표
c_metric1, c_metric2, c_metric3 = st.columns(3)
c_metric1.metric("총 품목", f"{len(view_df)}개")
c_metric2.metric("총 재고 수량", f"{int(view_df['현재재고'].sum()):,}개")
c_metric3.metric("재고 부족 (5개 미만)", f"{len(view_df[view_df['현재재고'] < 5])}개")

st.divider()

if view_df.empty:
    st.info("표시할 상품이 없습니다. 왼쪽 상단 화살표(>)를 눌러 사이드바에서 상품을 등록하거나 엑셀을 업로드하세요.")
else:
    for idx, row in view_df.iterrows():
        # 원본 데이터프레임의 인덱스 찾기
        real_idx = st.session_state.inventory.index[st.session_state.inventory['SKU'] == row['SKU']][0]
        
        with st.container():
            col_img, col_txt, col_ctrl, col_status = st.columns([1, 3, 2, 1])
            
            with col_img:
                img_path = row['이미지URL'] if pd.notna(row['이미지URL']) and row['이미지URL'] != "" else "https://via.placeholder.com/150?text=No+Image"
                st.image(img_path, width=100)
            
            with col_txt:
                st.subheader(row['상품명'])
                st.caption(f"SKU: {row['SKU']} | 마지막 수정: {row['최근수정일']}")
            
            with col_ctrl:
                st.write("재고 수량 조절")
                sub_c1, sub_c2, sub_c3 = st.columns(3)
                st.markdown(f"### {int(row['현재재고'])} 개")
                
                if sub_c1.button("➕", key=f"in_{row['SKU']}"):
                    st.session_state.inventory.at[real_idx, '현재재고'] += 1
                    st.session_state.inventory.at[real_idx, '최근수정일'] = datetime.now().strftime("%Y-%m-%d")
                    st.rerun()
                if sub_c2.button("➖", key=f"out_{row['SKU']}"):
                    if st.session_state.inventory.at[real_idx, '현재재고'] > 0:
                        st.session_state.inventory.at[real_idx, '현재재고'] -= 1
                        st.session_state.inventory.at[real_idx, '최근수정일'] = datetime.now().strftime("%Y-%m-%d")
                        st.rerun()
                if sub_c3.button("🗑️", key=f"del_{row['SKU']}"):
                    st.session_state.inventory = st.session_state.inventory.drop(real_idx)
                    st.rerun()
            
            with col_status:
                if row['현재재고'] < 5:
                    st.error("재고 부족")
                else:
                    st.success("상태 양호")
            
            st.divider()

# 데이터 내보내기 (백업용)
st.sidebar.divider()
st.sidebar.subheader("📥 데이터 백업")
csv_data = st.session_state.inventory.to_csv(index=False).encode('utf-8-sig')
st.sidebar.download_button(
    label="전체 재고 데이터 다운로드 (CSV)",
    data=csv_data,
    file_name=f"inventory_backup_{datetime.now().strftime('%Y%m%d')}.csv",
    mime="text/csv",
)
