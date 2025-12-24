import streamlit as st
import pandas as pd
from datetime import datetime
import io

# 페이지 설정
st.set_page_config(page_title="재고 관리 시스템", layout="wide")

# 스타일 설정
st.markdown("""
    <style>
    .main { background-color: #f8fafc; }
    @media print { .stButton, .stFileUploader, section[data-testid="stSidebar"] { display: none !important; } }
    .stNumberInput div div input { font-weight: bold; }
    </style>
    """, unsafe_allow_html=True)

# --- 데이터 관리 로직 ---
if 'inventory' not in st.session_state:
    st.session_state.inventory = pd.DataFrame(columns=['SKU', '상품명', '이미지URL', '현재재고', '최근수정일'])

# --- 사이드바: 상품 등록 ---
with st.sidebar:
    st.header("📦 개별 상품 등록")
    with st.form("add_form", clear_on_submit=True):
        new_sku = st.text_input("SKU (코드)")
        new_name = st.text_input("상품명")
        new_img = st.text_input("이미지 URL")
        new_qty = st.number_input("초기 수량", min_value=0, step=1)
        submit = st.form_submit_button("상품 추가")
        
        if submit and new_sku and new_name:
            new_row = pd.DataFrame([[new_sku, new_name, new_img, new_qty, datetime.now().strftime("%Y-%m-%d")]], 
                                  columns=['SKU', '상품명', '이미지URL', '현재재고', '최근수정일'])
            st.session_state.inventory = pd.concat([st.session_state.inventory, new_row], ignore_index=True).drop_duplicates('SKU', keep='last')
            st.success(f"{new_name} 등록 완료!")

    st.divider()
    st.header("📤 엑셀/CSV 벌크 업로드")
    st.caption("사용자님의 양식(SKU, 상품명, 이미지 URL, 초기 수량)을 지원합니다.")
    uploaded_file = st.file_uploader("파일을 선택하세요", type=["xlsx", "csv"])
    
    if uploaded_file:
        try:
            if uploaded_file.name.endswith('xlsx'):
                # openpyxl 설치 여부에 따른 예외 처리 추가
                try:
                    df_upload = pd.read_excel(uploaded_file, engine='openpyxl')
                except ImportError:
                    st.error("❌ 엑셀(.xlsx) 파일을 읽기 위해 'openpyxl' 라이브러리가 필요합니다.")
                    st.info("💡 해결 방법: 'requirements.txt' 파일에 'openpyxl'을 추가하거나, 파일을 **CSV 형식**으로 저장하여 업로드해주세요.")
                    df_upload = None
            else:
                df_upload = pd.read_csv(uploaded_file)
            
            if df_upload is not None:
                # 사용자 양식 헤더를 프로그램 규격으로 매핑
                rename_map = {
                    'SKU': 'SKU',
                    '상품명': '상품명',
                    '이미지 URL': '이미지URL',
                    '이미지URL': '이미지URL',
                    '초기 수량': '현재재고',
                    '초기수량': '현재재고',
                    '현재재고': '현재재고',
                    '수량': '현재재고'
                }
                
                # 존재하는 컬럼만 변경
                df_upload = df_upload.rename(columns=rename_map)
                
                # 필수 컬럼 확인 및 기본값 채우기
                if '최근수정일' not in df_upload.columns:
                    df_upload['최근수정일'] = datetime.now().strftime("%Y-%m-%d")
                if '이미지URL' not in df_upload.columns:
                    df_upload['이미지URL'] = ""
                
                # 필요한 컬럼만 추출하여 합치기
                target_cols = ['SKU', '상품명', '이미지URL', '현재재고', '최근수정일']
                df_final = df_upload[df_upload.columns.intersection(target_cols)]
                
                st.session_state.inventory = pd.concat([st.session_state.inventory, df_final], ignore_index=True).drop_duplicates('SKU', keep='last')
                st.success(f"성공적으로 {len(df_final)}개의 품목을 업데이트했습니다!")
        except Exception as e:
            st.error(f"파일을 읽는 중 오류가 발생했습니다: {e}")

# --- 메인 화면 ---
st.title("🍎 클라우드 재고 관리")
st.caption("아이폰, 아이패드에서 실시간으로 확인하는 스마트 재고 현황")

# 검색 및 요약 수치
search = st.text_input("🔍 검색 (상품명 또는 SKU)", "")
filtered_df = st.session_state.inventory[
    st.session_state.inventory['상품명'].str.contains(search, case=False, na=False) | 
    st.session_state.inventory['SKU'].str.contains(search, case=False, na=False)
].reset_index(drop=True)

col_sum1, col_sum2, col_sum3 = st.columns(3)
col_sum1.metric("총 품목 수", f"{len(filtered_df)}개")
col_sum2.metric("총 재고 수량", f"{int(filtered_df['현재재고'].sum()):,}개")
col_sum3.metric("재고 부족 품목", f"{len(filtered_df[filtered_df['현재재고'] < 5])}개")

st.divider()

# 재고 리스트 레이아웃
if filtered_df.empty:
    st.info("표시할 상품이 없습니다. 상품을 등록하거나 엑셀을 업로드해주세요.")
else:
    for idx, row in filtered_df.iterrows():
        # 원본 데이터프레임에서의 실제 인덱스 찾기
        real_idx = st.session_state.inventory.index[st.session_state.inventory['SKU'] == row['SKU']][0]
        
        with st.container():
            c1, c2, c3, c4 = st.columns([1, 3, 2, 1])
            
            with c1:
                img_url = row['이미지URL'] if pd.notna(row['이미지URL']) and row['이미지URL'] != "" else "https://via.placeholder.com/150?text=No+Image"
                st.image(img_url, width=100)
            
            with c2:
                st.subheader(row['상품명'])
                st.caption(f"SKU: {row['SKU']} | 마지막 수정: {row['최근수정일']}")
            
            with c3:
                st.write("재고 관리")
                sub_c1, sub_c2, sub_c3 = st.columns([1, 1, 1])
                # 수량 직접 표시
                q_val = int(row['현재재고'])
                st.markdown(f"### {q_val} 개")
                
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
            
            with c4:
                if row['현재재고'] < 5:
                    st.warning("재고 보충 필요")
                else:
                    st.success("재고 충분")
            
            st.divider()

# 하단 엑셀 내보내기 (프린트 대용)
st.subheader("📥 데이터 내보내기")
csv_data = st.session_state.inventory.to_csv(index=False).encode('utf-8-sig')
st.download_button(
    label="현재 재고 현황 다운로드 (CSV)",
    data=csv_data,
    file_name=f"inventory_report_{datetime.now().strftime('%Y%m%d')}.csv",
    mime="text/csv",
)
