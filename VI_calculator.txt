import streamlit as st
import rasterio
import numpy as np
import pandas as pd
from io import BytesIO

st.title("多光谱影像植被指数计算")

# 1. 读取影像
uploaded = st.file_uploader("上传多波段 GeoTIFF", type=["tif","tiff"])
if uploaded:
    with rasterio.MemoryFile(uploaded.read()) as memfile:
        with memfile.open() as src:
            bands = {f"B{idx+1}": src.read(idx+1) for idx in range(src.count)}
            profile = src.profile

    st.success(f"加载成功，共 {len(bands)} 个波段：{', '.join(bands.keys())}")

    # 显示波段选择提示
    st.write("已读取波段：", list(bands.keys()))

    # 2. 用户输入公式
    formula = st.text_input(
        "在下方输入植被指数计算公式（使用波段变量名）",
        value="(B4 - B3) / (B4 + B3)"
    )
    st.caption("示例：归一化差异植被指数 NDVI=(B4-B3)/(B4+B3)")

    if st.button("计算指数"):
        try:
            # 用 numpy 按公式计算
            # 为安全起见，用有限域 eval
            arr = eval(formula, {"__builtins__":{}}, bands)
            # 统计
            flat = arr.flatten()
            df = pd.DataFrame({
                "value": flat
            })
            df = df[np.isfinite(df)]
            
            st.subheader("计算结果预览")
            st.dataframe(df.sample(10))

            st.subheader("统计信息")
            st.write(df.describe())

            # 3. 下载 CSV
            csv = df.to_csv(index=False).encode('utf-8')
            st.download_button(
                "下载像元值 CSV",
                data=csv,
                file_name="vi_values.csv",
                mime="text/csv"
            )

            # 4. 导出 GeoTIFF
            out_profile = profile.copy()
            out_profile.update(dtype=rasterio.float32, count=1)
            memfile = BytesIO()
            with rasterio.MemoryFile() as mem:
                with mem.open(**out_profile) as dst:
                    dst.write(arr.astype(rasterio.float32), 1)
                memfile = mem.read()
            st.download_button(
                "下载 GeoTIFF",
                data=memfile,
                file_name="vi_map.tif",
                mime="image/tiff"
            )

        except Exception as e:
            st.error(f"计算出错：{e}")
