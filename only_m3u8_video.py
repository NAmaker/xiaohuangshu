import asyncio
import binascii
import os
import random
import re

import aiofiles
import aiohttp
import requests
from Crypto.Cipher import AES
from lxml import etree

headers_detail = {
    'User-Agent': "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    'Referer': 'https://xchina.co/photo'
}
headers2 = {
    'User-Agent': "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    'Referer': 'https://img.xchina.biz/photos2/{}',
    'Cookie': 'cf_chl_rc_m=1; cf_chl_3=48a88baf12d2fc2; cf_clearance=rHSUJQtIFZIijs2l1TKkNml4_fHojZBKKFMIGusxuuA-1708497770-1.0-Aev6OOZQ3R6I/+iBE+W+MIkqX7zJjaH+DIRPboQ3xINr4KcGMYedxTFT09OvqI5fYwa5fYLgmAHehjL6s8rcLCA='
}


async def m3u8_download(session, m3u8_url, m3u8_dir_name, main_dir_name, headers):
    if not os.path.exists(f'{main_dir_name}/{m3u8_dir_name}'):
        os.makedirs(f'{main_dir_name}/{m3u8_dir_name}')
    try:
        response = await fetch_with_retry(session=session,url=m3u8_url,headers=headers)
        async with aiofiles.open(f'{main_dir_name}/{m3u8_dir_name}/{m3u8_dir_name}.txt', 'w', encoding='utf-8') as f:
            await f.write(response)

    except Exception as e:
        print(e, '位于m3u8_download函数')


async def on_page_m3u8_download(res, main_dir_name, semaphore):
    for j in res:
        await get_m3u8(detail_src=j[0], semaphore=semaphore, m3u8_dir_name=j[1], main_dir_name=main_dir_name)


# 在这要判断了

async def get_m3u8(detail_src, semaphore, m3u8_dir_name, main_dir_name): # 有些detail_src是直接mp4
    id = detail_src.split('/')[-1]
    headers2['Referer'] = f'https://xchina.co/photo/{id}'
    try:
        conn = aiohttp.TCPConnector(ssl=False)  # 防止ssl报错
        async with aiohttp.ClientSession(connector=conn, trust_env=True) as session:
            async with semaphore:
                resp = await fetch_with_retry(session, url=detail_src)
                tree = etree.HTML(resp)
                m3 = tree.xpath('//div[@class="container"]/script[2]/text()')[0]
                pattern = r'video\.src\s*=\s*"([^"]+)"'
                # 使用正则表达式进行匹配
                matches = re.findall(pattern, m3)
                if matches:
                    # 如果找到匹配项，则输出结果
                    m3u8_src = matches[0]
                    await m3u8_download(session=session, m3u8_url=m3u8_src, m3u8_dir_name=m3u8_dir_name, main_dir_name=main_dir_name, headers=headers2)
    except Exception as e:
        print(f'get_m3u8出错\n{e}')


async def fetch_with_retry(session, url, headers=headers_detail, retries=5, retry_delay=10):
    for _ in range(retries):
        try:
            async with session.get(url, headers=headers) as response:
                if response.status == 429:
                    print("Received 429 status code. Retrying after delay.")
                    await asyncio.sleep(retry_delay + random.random() * 5)  # 添加随机延迟
                    continue
                elif 200 <= response.status < 300:
                    return await response.text()
                else:
                    continue
        except Exception as e:
            print('fetch_with_retry请求出错', e)
            await asyncio.sleep(retry_delay)
    return None


async def main_source(url, semaphore):
    resd = []
    conn = aiohttp.TCPConnector(ssl=False)  # 防止ssl报错
    async with aiohttp.ClientSession(connector=conn,
                                     trust_env=True) as session:  # 加上这一行解决ssl问题connector=conn, trust_env=True
        async with semaphore:
            resp_text = await fetch_with_retry(session, url)
            if resp_text:
                tree = etree.HTML(resp_text)
                all_div = tree.xpath("//div[@class='list']/div")
                for div in all_div:
                    try:
                        detail_src = 'https://xchina.co/' + div.xpath('./a/@href')[0]
                        img_src = div.xpath('./a/img/@src')[0]  # 首页封面图
                        img_name = div.xpath('./a/img/@alt')[0]
                        resd.append((detail_src, img_name))
                    except Exception as e:
                        continue
    return resd


async def download(src, main_dir_name, m3u8_dir, headers):
    if not os.path.exists(f'{main_dir_name}/{m3u8_dir}'):
        os.makedirs(f'./{main_dir_name}/{m3u8_dir}')
    file_name = src.split('/')[-1]
    print(m3u8_dir)
    for _ in range(5):
        try:
            conn = aiohttp.TCPConnector(ssl=False)  # 防止ssl报错
            async with aiohttp.ClientSession(connector=conn, trust_env=True) as session:
                async with session.get(src, headers=headers) as response:
                    if 200 <= response.status < 300:
                        async with aiofiles.open(f'{main_dir_name}/{m3u8_dir}/' + file_name, mode='wb') as fp:
                            while True:
                                chunk = await response.content.read()
                                if not chunk:
                                    break
                                await fp.write(chunk)
                        # # print('下载完成', dir_name)
                        #     break
                    else:
                        print(response.status)
                        continue
        except Exception as e:
            # print('download出错', e)
            continue


async def on_m3u8_ts_download(m3u8_name, main_dir_name):
    m3u8_name_file = os.path.join(main_dir_name, m3u8_name.split('.')[0], m3u8_name)
    async with aiofiles.open(m3u8_name_file, 'r', encoding='utf-8') as f:
        content = await f.readlines()
        for j in content:
            if not j.startswith('#'):
                src = j.strip('\n')
                await download(src=src, main_dir_name=main_dir_name, m3u8_dir=m3u8_name.split('.')[0],
                               headers=headers_detail)
                print(f'{m3u8_name}的{src}\nts文件正在下载')


async def descry_download(main_dir_name, m3u8_dir_name):
    key = b'U\xa7l\xad\x8e\xf1\x884\x94\xedh\xcf\xe3\xac:D'
    iv_hex = '067209a194b6ab5482af9c937c264eaa'
    iv = binascii.unhexlify(iv_hex)

    aes = AES.new(key=key, IV=iv, mode=AES.MODE_CBC)
    des_dir = os.path.join(main_dir_name, m3u8_dir_name, 'des')
    if not os.path.exists(des_dir):
        os.makedirs(des_dir)

    current_dir = os.path.join(main_dir_name, m3u8_dir_name)

    tasks = []
    for ts_name in os.listdir(current_dir):
        if ts_name.endswith('.ts'):
            ts_path = os.path.join(current_dir, ts_name)
            des_ts_path = os.path.join(des_dir, ts_name)
            tasks.append(des_ts(ts_path, des_ts_path, aes))

    await asyncio.gather(*tasks)


async def des_ts(ts_path, des_ts_path, aes):
    try:
        async with aiofiles.open(ts_path, mode='rb') as f1:
            content = await f1.read()
            des_mes = aes.decrypt(content)
            async with aiofiles.open(des_ts_path, mode='wb') as f2:
                await f2.write(des_mes)
    except Exception as e:
        print(f"Error processing file {ts_path}: {e}")


async def main():
    semaphore = asyncio.Semaphore(5)  # 限制并发请求的数量
    main_dir_name = './w'

    # 首页封面
    tasks_detail = []
    for i in range(2, 3):
        # url = f'https://xchina.co/photos/album-8/{i}.html' # cos
        # url = f"https://xchina.co/photos/album-8/{i}.html" # baihu
        # url = f"https://xchina.co/photos/album-4/{i}.html" # luchu
        # url = f'https://xchina.co/photos/album-9/{i}.html' # nvtong
        url = f'https://xchina.co/photos/album-11/{i}.html'  # video
        tasks_detail.append(asyncio.create_task(main_source(url, semaphore=semaphore)))
    if not os.path.exists(main_dir_name):
        os.makedirs(main_dir_name)
    res = await asyncio.gather(*tasks_detail)
    print(res)

    semaphore_m3u = asyncio.Semaphore(100)  # 限制并发请求的数量

    # 下载了所有的m3u8
    tasks_m3u8 = []
    for m3u in res:
        tasks_m3u8.append(on_page_m3u8_download(m3u, main_dir_name, semaphore_m3u))

    # 并发执行 on_page_m3u8_download() 任务
    await asyncio.gather(*tasks_m3u8)

    # 所有的ts下载

    tasks_ts_download = []
    for m3u8_dir in os.listdir(main_dir_name):
        for m3u8_name in os.listdir(os.path.join(main_dir_name, m3u8_dir)):
            if m3u8_name.endswith('txt'):
                tasks_ts_download.append(asyncio.create_task(on_m3u8_ts_download(m3u8_name, main_dir_name)))

    await asyncio.gather(*tasks_ts_download)

    # 本地所有的ts解密

    tasks_ts_des = []
    for m3u8_dir_name in os.listdir(main_dir_name):
        tasks_ts_des.append(descry_download(main_dir_name, m3u8_dir_name))
    await asyncio.gather(*tasks_ts_des)


if __name__ == '__main__':
    asyncio.run(main())

