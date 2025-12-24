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

# 2. 강력한 CSS 설정: 화면 디자인 + 인쇄 최적화
st.markdown("""
    <style>
    /* 화면 배경색 */
    .main { background-color: #f1f5f9; }

    /* 화면에서 '종이 문서'처럼 보이게 하는 스타일 */
    .paper-preview {
        background-color: white;
        padding: 40px;
        margin: 0 auto;
        width: 100%;
        max-width: 800px; /* A4 비율 느낌 */
        min-height: 1000px;
        box-shadow: 0 4px 20px rgba(0,0,0,0.1);
        border-radius: 8px;
        color: black;
    }

    /* 인쇄 시 필수 설정 */
    @media print {
        /* 스트림릿의 모든 UI 요소 숨기기 */
        header, .stSidebar, [data-testid="stHeader"], [data-testid="stToolbar"], 
        .stTabs [role="tablist"], .no-print, div.stButton, section[data-testid="stSidebar"] {
            display: none !important;
        }
        
        /* 메인 컨테이너 여백 제거 */
        .main .block-container {
            padding: 0 !important;
            margin: 0 !important;
        }

        /* 오직 paper-preview 영역만 출력 */
        .paper-preview {
            width: 100% !important;
            max-width: 100% !important;
            box-shadow: none !important;
            margin: 0 !important;
            padding: 0 !important;
            border: none !important;
        }

        /* 테이블 테두리 강화 */
        table { border-collapse: collapse !important; width: 100% !important; }
        th, td { border: 1px solid black !important; padding: 10px !important; }
        th { background-color: #f2f2f2 !important; -webkit-print-color-adjust: exact; }
    }

    /* 테이블 공통 스타일 */
    .report-table { width: 100%; border-collapse: collapse; margin-top: 20px; }
    .report-table th, .report-table td { border: 1px solid #ddd; padding: 12px; text-align: center; }
    .report-table th { background-color: #f8fafc; font-weight: bold; }
    .report-img { width: 60px; height: 60px; object-fit: cover; border-radius: 4px; }
    .empty-cell { width: 150px; background-color: #fff; }
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
                st.success("등록되었습니다.")

    st.divider()
    st.subheader("📤 엑셀 벌크 업로드")
    uploaded_file = st.file_uploader("파일 선택 (.xlsx, .csv)", type=["xlsx", "csv"])
    if uploaded_file:
        try:
            df = pd.read_excel(uploaded_file) if uploaded_file.name.endswith('xlsx') else pd.read_csv(uploaded_file)
            # 유연한 헤더 매핑
            df = df.rename(columns={'SKU':'SKU', '상품명':'상품명', '이미지 URL':'이미지URL', '초기 수량':'현재재고', '수량':'현재재고'})
            if '최근수정일' not in df.columns: df['최근수정일'] = datetime.now().strftime("%Y-%m-%d")
            st.session_state.inventory = pd.concat([st.session_state.inventory, df], ignore_index=True).drop_duplicates('SKU', keep='last')
            st.success("업로드 완료!")
        except: st.error("파일 형식을 확인해주세요.")

# --- 메인 화면 ---
st.title("🍎 스마트 재고 관리")

tab1, tab2 = st.tabs(["📊 현황 관리", "🖨️ 인쇄용 실사표"])

with tab1:
    search = st.text_input("🔍 검색", "")
    view_df = st.session_state.inventory[st.session_state.inventory['상품명'].str.contains(search, case=False, na=False)]
    
    if view_df.empty:
        st.info("사이드바(왼쪽 상단 화살표)를 열어 상품을 등록하세요.")
    else:
        for idx, row in view_df.iterrows():
            with st.container():
                c1, c2, c3 = st.columns([1, 4, 2])
                with c1: st.image(row['이미지URL'] if row['이미지URL'] else "https://via.placeholder.com/100", width=100)
                with c2:
                    st.subheader(row['상품명'])
                    st.caption(f"SKU: {row['SKU']} | 수정일: {row['최근수정일']}")
                with c3:
                    st.write(f"현재 재고: **{int(row['현재재고'])}**")
                    if st.button("삭제", key=f"del_{idx}"):
                        st.session_state.inventory = st.session_state.inventory.drop(idx)
                        st.rerun()
                st.divider()

with tab2:
    # 1. 인쇄 제어 버튼 영역
    col_btn1, col_btn2 = st.columns([1, 5])
    with col_btn1:
        if st.button("📄 즉시 인쇄하기", type="primary"):
            st.components.v1.html("<script>window.parent.focus(); window.parent.print();</script>", height=0)
    with col_btn2:
        st.caption("💡 팁: 인쇄 창에서 '배경 그래픽'을 켜주세요. 인쇄 전 아래 미리보기를 확인하세요.")

    # 2. 실사표 미리보기 (실제 종이 문서 시각화)
    st.markdown("---")
    
    # HTML로 문서 양식 렌더링 (Paper-preview 클래스 사용)
    current_date = datetime.now().strftime('%Y-%m-%d')
    
    rows_html = ""
    for _, row in st.session_state.inventory.iterrows():
        img = row['이미지URL'] if row['이미지URL'] else "https://via.placeholder.com/60"
        rows_html += f"""
            <tr>
                <td><img src="{img}" class="report-img"></td>
                <td style="text-align: left;">
                    <div style="font-weight: bold;">{row['상품명']}</div>
                    <div style="font-size: 11px; color: #666;">SKU: {row['SKU']}</div>
                </td>
                <td style="font-size: 16px;"><b>{int(row['현재재고'])}</b></td>
                <td class="empty-cell"></td>
            </tr>
        """

    report_html = f"""
    <div class="paper-preview">
        <h1 style="text-align: center; margin-bottom: 10px;">재고 실사 확인표</h1>
        <p style="text-align: right; font-size: 13px; color: #555;">출력일시: {current_date}</p>
        <table class="report-table">
            <thead>
                <tr>
                    <th style="width: 80px;">이미지</th>
                    <th>상품 정보</th>
                    <th style="width: 120px;">시스템 재고</th>
                    <th style="width: 150px;">실재고 (수기)</th>
                </tr>
            </thead>
            <tbody>
                {rows_html}
            </tbody>
        </table>
        <div style="margin-top: 50px; text-align: right; font-weight: bold;">
            실사 확인자: ____________________ (인)
        </div>
    </div>
    """
    
    st.markdown(report_html, unsafe_allow_html=True)
