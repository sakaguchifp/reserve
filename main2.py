import pandas as pd
import requests
import altair as alt
import io
import datetime
import numpy as np
import sympy

from ToushinReader.core import Fund

from datetime import datetime, date, timedelta
from dateutil.relativedelta import relativedelta



import streamlit as st

st.title('積立投資の効果')

st.sidebar.write("""
# PFP推奨銘柄積立シミュレーション
こちらは積立シミュレーションツールです。以下のオプションから積立月数を指定できます。
""")

st.sidebar.write("""
## 積立月数選択
""")

# 積立期間(何ヶ月間）
funding_period = st.sidebar.slider('月数', 1, 360, 12)


st.write(f"""
## 過去 **{funding_period}ヶ月間** の積立結果
""")
# 積立額(毎月何円)
amount = 10000
# 積立日(毎月　何日）
funding_date = 1

today = date.today()
day = today - timedelta(days=0)
day = np.datetime64(day)

this_month = today - timedelta(days=today.day-1)
start_month = this_month - relativedelta(months=funding_period)

isin_codes = {
    '投資のソムリエ': 'JP90C0008Q33',
    'ピクテ・マルチアセット・アロケーション・ファンド': 'JP90C0009WH1', 
    'ひふみプラス': 'JP90C0008CH5',
    '三井住友・中小型株ファンド': 'JP90C00009J8',
    'ＪＰＭアジア株・アクティブ・オープン': 'JP90C0001HV0',
    'キャピタル世界株式ファンド': 'JP90C00052C3',
    'ｎｅｔＷＩＮ　ＧＳテクノロジー株式ファンドＢコース（為替ヘッジなし）': 'JP90C0000Y15',
    'ベイリー・ギフォード世界長期成長株ファンド': 'JP90C000GZX0'
}





@st.cache
def get_data(isin_codes):
    df = pd.DataFrame()
    for itrust in isin_codes.keys():
        myFund = Fund(isin_codes[itrust])
        url = myFund.historical_data_url
        res = requests.get(url)
        df1 = pd.read_csv(io.BytesIO(res.content), encoding='shift-jis', sep=",")
        df1['年月日'] = pd.to_datetime(df1['年月日'], format='%Y年%m月%d日')  
        df1['ファンド名'] = itrust
        df = pd.concat([df , df1])
    return df

def get_reserve(funding_period, df):
    df_reserve = pd.DataFrame()
    day = start_month
    for itrust in isin_codes.keys():
        for i in range(funding_period):
            day = day + relativedelta(months=1)
            dt = np.datetime64(day)

            while (df['年月日'] == dt).sum() == 0:
                if dt >= np.datetime64(day + relativedelta(months=1)):
                    #print(day)
                    break
                dt =dt +  np.timedelta64(1,'D')
            df_reserve = df_reserve.append(df[df['年月日'] == dt])
    return df_reserve

# rを求めるプログラム
def rimawari_month(a, b):
    x = sympy.Symbol('x')
    num = len(a)
    expr = sum([a[i] * (1 + x) ** (num - i) for i in range(0, num)]) - b
    # 多項式展開
    expr_ex = sympy.expand(expr)
    # 多項式の係数取得
    d = [expr_ex.coeff(x, i) for i in range(num, -1, -1)]
    # 計算
    a = np.roots(d)
    # 虚数解計を除外する
    b = (list(filter(lambda y: y.imag == 0.j, a)))
    # 運用総額と評価額の比較
    # 評価額の方が高い場合は
    if sum(c) < V:
        # 正の解を出力する
        result = list(filter(lambda z: z > 0, b))
    # 評価額の方が低い場合は
    else:
        # 負の解を出力する
        result = list(filter(lambda z: z < 0, b))
    return result

try:
    df = get_data(isin_codes)

    itrusts = st.multiselect(
        'ファンド名を選択してください',
        list(df['ファンド名'].unique()),
        ['投資のソムリエ','ひふみプラス','キャピタル世界株式ファンド']
    )

    

    if not itrusts:
        st.error('少なくとも1つのファンドは選んでください。')
    else:
        df_select = df[df['ファンド名'].isin(itrusts)]
        df_reserve = get_reserve(funding_period, df_select)
        df_reserve = df_reserve[['年月日','基準価額(円)','ファンド名']]
        df_reserve = df_reserve.reset_index(drop=True)

        df_reserve['購入口数'] = round(amount / df_reserve['基準価額(円)'] *10000)
        df_reserve['口数'] = None
        df_reserve['評価額'] = None
        df_reserve['投資額'] = None
        df_reserve['投資総額'] = None
        df_reserve['損益'] = None
        df_reserve['損益率'] = None

        for itrust in isin_codes.keys():
            old = 0
            old2 = 0
            for i in range(len(df_reserve)):
                if df_reserve['ファンド名'].values[i] == itrust:
                    df_reserve['口数'].values[i] = old + df_reserve['購入口数'].values[i]
                    df_reserve['評価額'].values[i] = round(df_reserve['口数'].values[i]* df_reserve['基準価額(円)'].values[i] / 10000)
                    old = df_reserve['口数'].values[i] 

                    df_reserve['投資額'].values[i] = amount
                    df_reserve['投資総額'].values[i] = old2 + df_reserve['投資額'].values[i]
                    old2 = df_reserve['投資総額'].values[i]
        df_reserve['損益'] = df_reserve['評価額'] - df_reserve['投資総額']
        df_reserve['損益率'] = df_reserve['損益'] / df_reserve['投資総額'] * 100

        df_reserve['年月日'] = df_reserve['年月日'].dt.date
        
        st.write("### 評価額(円)",df_reserve.sort_index())       

        df_total = df_reserve.groupby('年月日').agg({'投資額':'sum','評価額':'sum'})
        df_total = df_total.reset_index()
        st.write("### 評価額(円)",df_total.sort_index())       

        c = df_total['投資額'].values
        V = df_total['評価額'].values[-1]
        
        # Rを計算
        r = rimawari_month(c, V)[0]
        R = (1+r)**12-1
        R = np.round(R*100, decimals=2)
        R1 = str(R)
        st.write(f"""
        ## 年利は **{R1}%** です。
        """)

        ymin = 0
        ymax= df_total['評価額'].values[-1]*1.1
        chart1 = (
            alt.Chart(df_reserve)
            .mark_area(opacity=0.8, clip=True)
            .encode(
                x="年月日:T",
                y=alt.Y("評価額:Q", stack='zero', scale=alt.Scale(domain=[ymin,ymax])),
                color='ファンド名:N'
            )
        )

        chart2 = (
            alt.Chart(df_reserve)
            .mark_line(opacity=0.8, clip=True)
            .encode(
                x="年月日:T",
                y=alt.Y("投資総額:Q", stack='zero', scale=alt.Scale(domain=[ymin,ymax])),
                color='ファンド名:N'
            )
        )
        st.altair_chart(chart1 + chart2, use_container_width=True)
        
        

except:
    st.error(
        "おっと！何かエラーが起きているようです。"
    )