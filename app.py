import io
import os
import time
from datetime import date, datetime
from typing import Iterator

import requests
import pandas as pd
import numpy as np
from slack import WebhookClient


class Calculator:
    def __init__(self) -> None:
        self.m_df = self._download()
        self.slack_client = WebhookClient(os.environ['SLACK_WEBHOOK_URL'])

    def _download(self) -> pd.DataFrame:
        targets = [
            # 401k
            {'code': '89313135', 'name': 'EXEi_G_STOCK'},
            {'code': '89315135', 'name': 'EXEi_G_REIT'},
            {'code': '89311025', 'name': 'SBI_JP_TOPIX100'},
            {'code': '04312004', 'name': 'DAIWA_JP_BOUND'},
            {'code': '97311174', 'name': 'YJAM_LIGHT'},
            {'code': '04313004', 'name': 'DAIWA_G_BOUND'},
            {'code': '4731304C', 'name': 'MHAM_JP_REIT'},
            {'code': '89311077', 'name': 'SBI_IV'},
        ]

        df_list = list()

        for target in targets:
            time.sleep(1)
            code = target['code']
            url = f'http://apl.morningstar.co.jp/webasp/yahoo-fund/fund/download.aspx?type=1&fnc={code}'
            print(url)
            res = requests.get(url)
            df = pd.read_csv(io.BytesIO(res.content), encoding='shift_jis', sep=',')
            df['date'] = pd.to_datetime(df['日付'].astype(str), format="%Y%m%d")
            df = df.set_index(['date']).drop(['日付'], axis=1).resample("M").ffill()
            df.columns = [target['name']]

            df_list.append(df)

        df = pd.concat(df_list, axis=1)
        return df

    def run(self) -> pd.DataFrame:
        m_df = self.m_df
        ret_df = pd.concat([
            m_df.iloc[-1] / m_df.iloc[-4],
            m_df.iloc[-1] / m_df.iloc[-7],
            m_df.iloc[-1] / m_df.iloc[-13]
        ], axis=1)
        ret_df.columns = ['ret_3m', 'ret_6m', 'ret_12m']
        ret_df['mean'] = (ret_df['ret_3m'] + ret_df['ret_6m'] + ret_df['ret_12m']) / 3
        ret_df['rank'] = ret_df['mean'].rank(ascending=False)
        ret_df['value'] = m_df.iloc[-1] 
        ret_df['value_12ma'] = m_df.rolling(window=12).mean().iloc[-1]
        ret_df['buy'] = ret_df['value'] > ret_df['value_12ma']

        out_df = ret_df.sort_values('rank')

        print(out_df)
        self.slack_client.send(
            text=f'fallback',
            blocks=[
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"レラティブストレングス投資のシグナル"
                    }
                },
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"```{out_df.to_string(float_format=lambda x: '{:.2f}'.format(x))}```"
                    }
                },
            ]
        )


if __name__ == '__main__':
    Calculator().run()
