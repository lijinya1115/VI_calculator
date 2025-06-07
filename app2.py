import streamlit as st
import rasterio
import numpy as np
import pandas as pd
from io import BytesIO

# —— 自定义 CSS：隐藏英文提示、添加中文提示 ——  
st.markdown(
    """
    <style>
    /* 隐藏默认的英文提示文字 */
    [data-testid="fileUploaderDropzone"] p {
        visibility: hidden;
    }
    /* 在拖拽区添加自定义中文提示 */
    [data-testid="fileUploaderDropzone"]::before {
        content: "将 TIF/TIFF 文件拖拽到此处，或点击右侧按钮上传 (单文件限 3 GB)";
        display: block;
        margin: 1.5em 0;
        color: #aaa;
        font-size: 0.95em;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# —— 页面设置 ——  
st.set_page_config(page_title="多光谱影像植被指数计算", layout="wide")
st.title("多光谱影像植被指数计算")

# —— 文件上传 ——  
uploaded = st.file_uploader(
    label="上传多波段 GeoTIFF",
    type=["tif", "tiff"],
    help="支持单文件最大 3 GB"
)

if uploaded:
    try:
        # 读取 GeoTIFF 波段
        with rasterio.MemoryFile(uploaded.read()) as memfile:
            with memfile.open() as src:
                bands = {
                    f"B{idx+1}": src.read(idx+1)
                    for idx in range(src.count)
                }
                profile = src.profile

        st.success(f"加载成功，共 {len(bands)} 个波段：{', '.join(bands.keys())}")
        st.write("已读取波段：", list(bands.keys()))

        # 用户输入公式
        formula = st.text_input(
            "请输入植被指数计算公式（示例 NDVI=(B4-B3)/(B4+B3)）",
            value="(B4 - B3) / (B4 + B3)"
        )

        if st.button("计算指数"):
            # 安全计算
            arr = eval(formula, {"__builtins__": {}}, bands)
            flat = arr.flatten()
            df = pd.DataFrame({"value": flat})
            df = df[np.isfinite(df)]

            # 结果展示
            st.subheader("结果预览（随机抽样 10 行）")
            st.dataframe(df.sample(10))
            st.subheader("统计信息")
            st.write(df.describe())

            # 下载 CSV
            csv_bytes = df.to_csv(index=False).encode("utf-8")
            st.download_button(
                "下载 像元值 CSV",
                data=csv_bytes,
                file_name="vi_values.csv",
                mime="text/csv"
            )

            # 导出 GeoTIFF
            out_profile = profile.copy()
            out_profile.update(dtype=rasterio.float32, count=1)
            with rasterio.MemoryFile() as mem:
                with mem.open(**out_profile) as dst:
                    dst.write(arr.astype(rasterio.float32), 1)
                geotiff_bytes = mem.read()
            st.download_button(
                "下载 植被指数 GeoTIFF",
                data=geotiff_bytes,
                file_name="vi_map.tif",
                mime="image/tiff"
            )

    except Exception as e:
        st.error(f"处理出错：{e}")
