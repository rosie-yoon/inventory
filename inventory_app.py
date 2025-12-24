import streamlit as st
import pandas as pd
from datetime import datetime
import time

try:
    from streamlit_gsheets import GSheetsConnection
except ImportError:
    GSheetsConnection = None


# ======================================================
# 1. PAGE CONFIG
# ======================================================
st.set_page_config(
    page_title="재고 관리 시스템",
    layout="wide",
    initial_sidebar_state="collapsed"
)

st.markdown("""
<style>
.main { background-color: #f8fafc; }
.sync-box {
    background:#fff; padding:24px; border-radius:14px;
    border:1px solid #e5e7eb; margin-bottom:24px;
}
.qty-text {
    text-align:center; font-size:1.6rem; font-weight:bold;
}
[data-testid="stSidebar"], section[data-testid="stSidebar"] { display:none; }
</style>
""", unsafe_allow_html=True)


# ======================================================
# 2. COLUMN DEFINITIONS
# ======================================================
COL_SKU  = "SKU"
COL_NAME = "상품명"
COL_IMG  = "이미지URL"
COL_QTY  = "현재재고"
COL_DATE = "최근수정일"

REQUIRED_COLS = [COL_SKU, COL_NAME, COL_IMG, COL_QTY, COL_DATE]


# ======================================================
# 3. SESSION STATE
# ======================================================
if "inventory" not in st.session_state:
    st.session_state.inventory = pd.DataFrame(columns=REQUIRED_COLS)


# ======================================================
# 4. GOOGLE SHEETS
# ======================================================
def get_connection():
    if not GSheetsConnection:
        return None
    try:
        return st.connection("gsheets", type=GSheetsConnection)
    except:
        return None


def normalize_for_gsheet(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    out[COL_SKU]  = out[COL_SKU].astype(str).fillna("")
    out[COL_NAME] = out[COL_NAME].astype(str).fillna("")
    out[COL_IMG]  = out[COL_IMG].astype(str).fillna("")
    out[COL_QTY]  = pd.to_numeric(out[COL_QTY], errors="coerce").fillna(0).astype(int)
    out[COL_DATE] = out[COL_DATE].astype(str).replace("nan", "").fillna("")
    return out


def fetch_data():
    conn = get_connection()
    if not conn:
        return

    with st.spinner("구글 시트에서 불러오는 중..."):
        df = conn.read(ttl=0)
        if df is None:
            return

        df = df.dropna(how="all")
        df.columns = df.columns.astype(str).str.strip()

        rename_map = {
            "SKU": COL_SKU,
            "상품명": COL_NAME,
            "이미지URL": COL_IMG,
            "이미지 URL": COL_IMG,
            "현재재고": COL_QTY,
            "현재 재고": COL_QTY,
            "최근수정일": COL_DATE,
            "최근 수정일": COL_DATE,
        }
        df = df.rename(columns=rename_map)

        for col in REQUIRED_COLS:
            if col not in df.columns:
                df[col] = 0 if col == COL_QTY else ""

        df[COL_QTY] = pd.to_numeric(df[COL_QTY], errors="coerce").fillna(0).astype(int)

        st.session_state.inventory = df[REQUIRED_COLS].copy()
        st.toast("✅ 동기화 완료")


def commit_data():
    conn = get_connection()
    if not conn:
        return

    with st.spinner("구글 시트에 저장 중..."):
        conn.update(data=normalize_for_gsheet(st.session_state.inventory))
        st.success("🚀 저장 완료")
        time.sleep(0.8)
        st.session_state.inventory = conn.read(ttl=0)
        st.rerun()


# ======================================================
# 5. HEADER
# ======================================================
st.title("🍎 스마트 재고 동기화 시스템")

c1, c2, c3 = st.columns([2, 1, 1])
with c1:
    st.subheader("🔄 실시간 동기화")
with c2:
    st.button("📥 불러오기", on_click=fetch_data, use_container_width=True)
with c3:
    st.button("💾 최종 저장", on_click=commit_data, type="primary", use_container_width=True)


# ======================================================
# 6. TABS
# ======================================================
tab_list, tab_add = st.tabs(["📊 재고 현황", "➕ 신규 등록"])


# ------------------------------------------------------
# ADD ITEM
# ------------------------------------------------------
with tab_add:
    with st.form("add_item", clear_on_submit=True):
        sku  = st.text_input("SKU")
        name = st.text_input("상품명")
        img  = st.text_input("이미지URL")
        qty  = st.number_input("현재재고", min_value=0, step=1)

        if st.form_submit_button("추가"):
            if sku and name:
                new = pd.DataFrame([[sku, name, img, int(qty), datetime.now().strftime("%Y-%m-%d")]],
                                   columns=REQUIRED_COLS)
                st.session_state.inventory = (
                    pd.concat([st.session_state.inventory, new])
                    .drop_duplicates(COL_SKU, keep="last")
                    .reset_index(drop=True)
                )
                st.success("추가됨 (저장 버튼을 눌러 반영)")


# ------------------------------------------------------
# INVENTORY LIST
# ------------------------------------------------------
with tab_list:
    search = st.text_input("🔍 검색 (상품명 / SKU)", "")
    df = st.session_state.inventory

    view = df[
        df[COL_NAME].str.contains(search, case=False, na=False) |
        df[COL_SKU].str.contains(search, case=False, na=False)
    ].reset_index(drop=True)

    if view.empty:
        st.info("데이터가 없습니다.")
    else:
        for _, row in view.iterrows():
            idx = df.index[df[COL_SKU] == row[COL_SKU]][0]

            c_img, c_info, c_ctrl = st.columns([1, 3, 2])
            with c_img:
                img = row.get(COL_IMG, "")
                img = str(img).strip()

                if not img or img.lower() == "nan":
                    img = "https://via.placeholder.com/120"

                st.image(img, width=100)


            with c_info:
                st.subheader(row[COL_NAME])
                st.caption(f"SKU: {row[COL_SKU]} | 수정일: {row[COL_DATE]}")

            with c_ctrl:
                a, b, c = st.columns([1, 1.4, 1])
                with a:
                    if st.button("➖", key=f"d_{row[COL_SKU]}"):
                        if row[COL_QTY] > 0:
                            st.session_state.inventory.at[idx, COL_QTY] -= 1
                            st.session_state.inventory.at[idx, COL_DATE] = datetime.now().strftime("%Y-%m-%d")
                            st.rerun()
                with b:
                    st.markdown(f"<div class='qty-text'>{row[COL_QTY]}</div>", unsafe_allow_html=True)
                with c:
                    if st.button("➕", key=f"u_{row[COL_SKU]}"):
                        st.session_state.inventory.at[idx, COL_QTY] += 1
                        st.session_state.inventory.at[idx, COL_DATE] = datetime.now().strftime("%Y-%m-%d")
                        st.rerun()

            st.divider()
