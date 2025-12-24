import streamlit as st
import pandas as pd
from datetime import datetime
import time

# 구글 시트 연결 라이브러리 (배포 시 requirements.txt에 streamlit-gsheets 추가 필요)
try:
    from streamlit_gsheets import GSheetsConnection
except ImportError:
    GSheetsConnection = None

# 1. 페이지 설정
st.set_page_config(
    page_title="재고 관리 시스템", 
    layout="wide",
    initial_sidebar_state="collapsed"
)

# 2. 스타일 및 UI 설정
st.markdown("""
    <style>
    .main { background-color: #f8fafc; }
    .stNumberInput div div input { font-weight: bold; }
    .sync-box {
        background-color: #ffffff;
        padding: 20px;
        border-radius: 15px;
        border: 1px solid #e2e8f0;
        margin-bottom: 20px;
        box-shadow: 0 2px 10px rgba(0,0,0,0.05);
    }
    .status-badge {
        font-size: 11px;
        padding: 4px 12px;
        border-radius: 20px;
        font-weight: bold;
    }
    </style>
    """, unsafe_allow_html=True)

# --- 데이터 관리 로직 ---

# 세션 상태 초기화
if 'inventory' not in st.session_state:
    st.session_state.inventory = pd.DataFrame(columns=['SKU', '상품명', '이미지URL', '현재재고', '최근수정일'])

if 'conn' not in st.session_state:
    st.session_state.conn = None

# 구글 시트 연결 시도
def get_connection():
    if GSheetsConnection and "gsheets" in st.secrets:
        return st.connection("gsheets", type=GSheetsConnection)
    return None

# 데이터 불러오기 (Fetch)
def fetch_data():
    conn = get_connection()
    if conn:
        try:
            # 구글 시트의 첫 번째 워크시트를 읽어옵니다.
            df = conn.read(ttl="0") 
            st.session_state.inventory = df.copy()
            st.toast("✅ 구글 시트에서 최신 데이터를 가져왔습니다!")
        except Exception as e:
            st.error(f"데이터 불러오기 실패: {e}")
    else:
        st.warning("⚠️ 구글 시트 연결 설정(Secrets)이 필요합니다.")

# 데이터 저장하기 (Commit)
def commit_data():
    conn = get_connection()
    if conn:
        try:
            conn.update(data=st.session_state.inventory)
            st.toast("🚀 구글 시트에 모든 변경사항이 저장되었습니다!")
            st.success("동기화 완료!")
        except Exception as e:
            st.error(f"데이터 저장 실패: {e}")
    else:
        st.error("연결 정보가 없어 클라우드에 저장할 수 없습니다.")

# --- 메인 화면 ---
st.title("🍎 스마트 재고 동기화 시스템")
st.caption("구글 시트를 기반으로 모든 기기의 재고를 실시간 관리하세요.")

# 상단 동기화 제어판
with st.container():
    st.markdown('<div class="sync-box">', unsafe_allow_html=True)
    c_sync1, c_sync2, c_sync3 = st.columns([2, 1, 1])
    
    with c_sync1:
        st.subheader("🔄 데이터 동기화")
        if GSheetsConnection and "gsheets" in st.secrets:
            st.markdown('<span class="status-badge" style="background:#dcfce7; color:#166534;">연결됨: Google Sheets</span>', unsafe_allow_html=True)
        else:
            st.markdown('<span class="status-badge" style="background:#fee2e2; color:#991b1b;">연결 안 됨: 임시 모드</span>', unsafe_allow_html=True)
    
    with c_sync2:
        if st.button("📥 시트에서 불러오기", use_container_width=True):
            fetch_data()
            st.rerun()
            
    with c_sync3:
        if st.button("💾 시트에 최종 저장", type="primary", use_container_width=True):
            commit_data()
    st.markdown('</div>', unsafe_allow_html=True)

# 탭 메뉴
tab_list, tab_add = st.tabs(["📊 재고 관리", "➕ 새 상품 등록"])

with tab_add:
    st.subheader("신규 상품 추가")
    with st.form("add_form", clear_on_submit=True):
        col_f1, col_f2 = st.columns(2)
        new_sku = col_f1.text_input("SKU (코드)")
        new_name = col_f2.text_input("상품명")
        new_img = st.text_input("이미지 URL (직접 링크)")
        new_qty = st.number_input("현재 재고 수량", min_value=0, step=1)
        
        if st.form_submit_button("재고 목록에 임시 추가"):
            if new_sku and new_name:
                new_row = pd.DataFrame([[new_sku, new_name, new_img, new_qty, datetime.now().strftime("%Y-%m-%d")]], 
                                      columns=['SKU', '상품명', '이미지URL', '현재재고', '최근수정일'])
                st.session_state.inventory = pd.concat([st.session_state.inventory, new_row], ignore_index=True).drop_duplicates('SKU', keep='last')
                st.success(f"'{new_name}'이 목록에 추가되었습니다. 상단의 [시트에 최종 저장]을 눌러야 반영됩니다.")

with tab_list:
    search = st.text_input("🔍 검색 (명칭/SKU)", "")
    view_df = st.session_state.inventory[
        st.session_state.inventory['상품명'].str.contains(search, case=False, na=False) |
        st.session_state.inventory['SKU'].str.contains(search, case=False, na=False)
    ].reset_index(drop=True)

    if view_df.empty:
        st.info("데이터가 없습니다. [시트에서 불러오기]를 누르거나 새 상품을 등록하세요.")
    else:
        # 지표
        m1, m2, m3 = st.columns(3)
        m1.metric("총 품목", f"{len(view_df)}개")
        m2.metric("전체 수량", f"{int(view_df['현재재고'].sum()):,}개")
        m3.metric("재고 부족", f"{len(view_df[view_df['현재재고'] < 5])}건")
        
        st.divider()

        # 리스트 렌더링
        for idx, row in view_df.iterrows():
            real_idx = st.session_state.inventory.index[st.session_state.inventory['SKU'] == row['SKU']][0]
            with st.container():
                c_img, c_info, c_qty, c_btn = st.columns([1, 3, 2, 1])
                with c_img:
                    img_url = row['이미지URL'] if pd.notna(row['이미지URL']) and row['이미지URL'] != "" else "https://via.placeholder.com/100?text=No+Image"
                    st.image(img_url, width=100)
                with c_info:
                    st.subheader(row['상품명'])
                    st.caption(f"SKU: {row['SKU']} | 수정일: {row['최근수정일']}")
                with c_qty:
                    st.markdown(f"### {int(row['현재재고'])} 개")
                    sub_c1, sub_c2 = st.columns(2)
                    if sub_c1.button("➕", key=f"up_{row['SKU']}"):
                        st.session_state.inventory.at[real_idx, '현재재고'] += 1
                        st.session_state.inventory.at[real_idx, '최근수정일'] = datetime.now().strftime("%Y-%m-%d")
                        st.rerun()
                    if sub_c2.button("➖", key=f"down_{row['SKU']}"):
                        if row['현재재고'] > 0:
                            st.session_state.inventory.at[real_idx, '현재재고'] -= 1
                            st.session_state.inventory.at[real_idx, '최근수정일'] = datetime.now().strftime("%Y-%m-%d")
                            st.rerun()
                with c_btn:
                    if st.button("🗑️", key=f"del_{row['SKU']}"):
                        st.session_state.inventory = st.session_state.inventory.drop(real_idx)
                        st.rerun()
                st.divider()

# 사이드바 설정 도움말
with st.sidebar:
    st.header("⚙️ 연결 설정")
    st.write("구글 시트와 연결하려면 Streamlit Cloud의 Secrets 설정에 시트 URL을 등록해야 합니다.")
    if st.button("설정 가이드 보기"):
        st.info("1. 구글 시트를 만들고 '링크가 있는 모든 사용자에게 편집 허용'으로 설정하세요.\n2. 앱 설정의 Secrets 칸에 해당 URL을 입력하세요.")
