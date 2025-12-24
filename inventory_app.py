import streamlit as st
import pandas as pd
from datetime import datetime
import io

# 페이지 설정 (사이드바를 기본적으로 접힌 상태로 설정)
st.set_page_config(
    page_title="재고 관리 시스템", 
    layout="wide",
    initial_sidebar_state="collapsed"
)

# 스타일 설정 (화면 디자인 및 인쇄 최적화)
st.markdown("""
    <style>
    .main { background-color: #f8fafc; }
    
    /* 화면용 스타일 */
    .no-print { display: block; }
    
    /* 인쇄 전용 스타일 (강력한 화이트리스트 방식) */
    @media print {
        /* 1. 일단 모든 스트림릿 기본 요소를 숨김 */
        header, .stSidebar, [data-testid="stHeader"], [data-testid="stToolbar"], .stTabs [role="tablist"], .no-print, .stButton {
            display: none !important;
        }
        
        /* 2. 전체 페이지 배경 및 여백 초기화 */
        [data-testid="stAppViewContainer"] {
            background-color: white !important;
        }
        .main .block-container {
            padding: 0 !important;
            margin: 0 !important;
        }

        /* 3. 인쇄 영역만 강제로 노출 */
        .print-area {
            display: block !important;
            visibility: visible !important;
            position: absolute;
            left: 0;
            top: 0;
            width: 100%;
        }

        /* 4. 테이블 디자인 보강 */
        .print-table {
            width: 100%;
            border-collapse: collapse;
            font-size: 13px;
            margin-top: 10px;
        }
        .print-table th, .print-table td {
            border: 1px solid #000 !important;
            padding: 10px 5px;
            text-align: center;
            vertical-align: middle;
            color: black !important;
        }
        .print-table th {
            background-color: #f2f2f2 !important;
            -webkit-print-color-adjust: exact;
        }
        .print-img {
            width: 60px;
            height: 60px;
            object-fit: cover;
            border-radius: 4px;
        }
        .physical-stock-cell {
            width: 140px;
            height: 50px;
        }
    }
    
    .stNumberInput div div input { font-weight: bold; }
    </style>
    """, unsafe_allow_html=True)

# --- 데이터 관리 로직 ---
if 'inventory' not in st.session_state:
    st.session_state.inventory = pd.DataFrame(columns=['SKU', '상품명', '이미지URL', '현재재고', '최근수정일'])

# --- 사이드바: 상품 등록 (화살표를 눌러 열고 닫을 수 있음) ---
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
    uploaded_file = st.file_uploader("파일을 선택하세요", type=["xlsx", "csv"])
    
    if uploaded_file:
        try:
            if uploaded_file.name.endswith('xlsx'):
                df_upload = pd.read_excel(uploaded_file, engine='openpyxl')
            else:
                df_upload = pd.read_csv(uploaded_file)
            
            if df_upload is not None:
                rename_map = {
                    'SKU': 'SKU', '상품명': '상품명', '이미지 URL': '이미지URL',
                    '이미지URL': '이미지URL', '초기 수량': '현재재고', '수량': '현재재고'
                }
                df_upload = df_upload.rename(columns=rename_map)
                if '최근수정일' not in df_upload.columns:
                    df_upload['최근수정일'] = datetime.now().strftime("%Y-%m-%d")
                
                target_cols = ['SKU', '상품명', '이미지URL', '현재재고', '최근수정일']
                df_final = df_upload[df_upload.columns.intersection(target_cols)]
                st.session_state.inventory = pd.concat([st.session_state.inventory, df_final], ignore_index=True).drop_duplicates('SKU', keep='last')
                st.success(f"{len(df_final)}개 품목 업데이트 완료!")
        except Exception as e:
            st.error(f"오류 발생: {e}")

# --- 메인 화면 ---
st.title("🍎 클라우드 재고 관리")

# 탭 구성
tab_manage, tab_print = st.tabs(["📊 재고 관리", "🖨️ 재고 실사표 (인쇄용)"])

with tab_manage:
    search = st.text_input("🔍 검색 (상품명 또는 SKU)", "", key="search_main")
    filtered_df = st.session_state.inventory[
        st.session_state.inventory['상품명'].str.contains(search, case=False, na=False) | 
        st.session_state.inventory['SKU'].str.contains(search, case=False, na=False)
    ].reset_index(drop=True)

    if filtered_df.empty:
        st.info("표시할 상품이 없습니다. 왼쪽 사이드바를 열어 상품을 등록해주세요.")
    else:
        for idx, row in filtered_df.iterrows():
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
                    sc1, sc2, sc3 = st.columns(3)
                    st.markdown(f"### {int(row['현재재고'])} 개")
                    if sc1.button("➕", key=f"in_{row['SKU']}"):
                        st.session_state.inventory.at[real_idx, '현재재고'] += 1
                        st.rerun()
                    if sc2.button("➖", key=f"out_{row['SKU']}"):
                        if st.session_state.inventory.at[real_idx, '현재재고'] > 0:
                            st.session_state.inventory.at[real_idx, '현재재고'] -= 1
                            st.rerun()
                    if sc3.button("🗑️", key=f"del_{row['SKU']}"):
                        st.session_state.inventory = st.session_state.inventory.drop(real_idx)
                        st.rerun()
                with c4:
                    if row['현재재고'] < 5: st.warning("부족")
                    else: st.success("정상")
                st.divider()

with tab_print:
    st.subheader("🖨️ 재고 실사용 리포트")
    st.write("이미지와 시스템 재고가 포함된 리스트입니다. 인쇄 후 실재고를 수기로 기입하세요.")
    
    # 인쇄 버튼 (JS 개선)
    if st.button("📄 실사표 즉시 인쇄", key="print_btn"):
        st.components.v1.html("""
            <script>
                setTimeout(function() {
                    window.parent.focus();
                    window.parent.print();
                }, 500);
            </script>
        """, height=0)

    # 인쇄용 HTML 테이블 생성 (print-area 클래스 부여)
    html_content = f"""
    <div class="print-area">
        <h2 style="text-align: center; margin-bottom: 20px;">재고 실사 확인표 ({datetime.now().strftime('%Y-%m-%d')})</h2>
        <table class="print-table">
            <thead>
                <tr>
                    <th style="width: 80px;">이미지</th>
                    <th>상품명 / SKU</th>
                    <th style="width: 120px;">시스템 재고</th>
                    <th style="width: 150px;">실재고 (수기기입)</th>
                </tr>
            </thead>
            <tbody>
    """
    
    for _, row in st.session_state.inventory.iterrows():
        img_src = row['이미지URL'] if pd.notna(row['이미지URL']) and row['이미지URL'] != "" else "https://via.placeholder.com/60"
        html_content += f"""
                <tr>
                    <td><img src="{img_src}" class="print-img"></td>
                    <td style="text-align: left; padding-left: 15px;">
                        <div style="font-weight: bold;">{row['상품명']}</div>
                        <div style="font-size: 11px; color: #666;">SKU: {row['SKU']}</div>
                    </td>
                    <td style="font-size: 16px;"><b>{int(row['현재재고'])}</b></td>
                    <td class="physical-stock-cell"></td>
                </tr>
        """
    
    html_content += """
            </tbody>
        </table>
        <div style="margin-top: 20px; text-align: right; font-size: 12px; font-weight: bold;">
            확인자: ____________________ (인)
        </div>
    </div>
    """
    
    st.markdown(html_content, unsafe_allow_html=True)

# 하단 데이터 백업 (사이드바 내부)
st.sidebar.divider()
st.sidebar.subheader("📥 데이터 백업")
csv_data = st.session_state.inventory.to_csv(index=False).encode('utf-8-sig')
st.sidebar.download_button(label="전체 데이터 CSV 다운로드", data=csv_data, file_name=f"inventory_{datetime.now().strftime('%Y%m%d')}.csv", mime="text/csv")
