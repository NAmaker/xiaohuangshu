import os
import random

import aiofiles
import aiohttp
import asyncio
from lxml import etree

headers = {
    'User-Agent': "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    'Referer': 'https://img.xchina.biz/photos2/'

}
headers2 = {
    'User-Agent': "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    'Referer': 'https://img.xchina.biz/photos2/{}',
    'Cookie': 'cf_chl_rc_m=1; cf_chl_3=48a88baf12d2fc2; cf_clearance=rHSUJQtIFZIijs2l1TKkNml4_fHojZBKKFMIGusxuuA-1708497770-1.0-Aev6OOZQ3R6I/+iBE+W+MIkqX7zJjaH+DIRPboQ3xINr4KcGMYedxTFT09OvqI5fYwa5fYLgmAHehjL6s8rcLCA='


}
asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())  # 加上这一行解决ssl问题


async def download(session, src, dir_name, main_dir_name, headers):
    if not os.path.exists(f'{main_dir_name}/{dir_name}'):
        os.makedirs(f'./{main_dir_name}/{dir_name}')
    file_name = src.split('/')[-1]
    for _ in range(5):
        try:
            async with session.get(src, headers=headers) as response:
                if 200 <= response.status < 300:
                    async with aiofiles.open(f'{main_dir_name}/{dir_name}/' + file_name, mode='wb') as fp:
                        while True:
                            chunk = await response.content.read()
                            if not chunk:
                                break
                            await fp.write(chunk)
                # print('下载完成', dir_name)
                    break
                else:
                    continue
        except Exception as e:
            # print('download出错', e)
            continue


async def video_download(detail_src, semaphore, dir_name, main_dir_name):
    id = detail_src.split('/')[-1].split('.')[0]
    video_id = id.split('-')[-1]
    video_src = f'https://img.xchina.biz/photos2/{video_id}/0001.mp4'
    headers2['Referer'] = f'https://img.xchina.biz/photos2/{video_id}/0001.mp4'
    for _ in range(5):
        try:
            conn = aiohttp.TCPConnector(ssl=False)  # 防止ssl报错
            async with aiohttp.ClientSession(connector=conn, trust_env=True) as session:
                async with semaphore:
                    await download(session, video_src, dir_name, main_dir_name, headers=headers2)
                    print(dir_name + 'ok')
            break
        except Exception as e:
            print(f'get_detail_src()出错\n{e}')
            continue


async def fetch_with_retry(session, url, headers=headers, retries=5, retry_delay=10):
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
            print('请求出错', e)
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


async def main():
    semaphore = asyncio.Semaphore(5)  # 限制并发请求的数量
    tasks = []
    for i in range(1, 2):
        # url = f'https://xchina.co/photos/album-8/{i}.html' # cos
        # url = f"https://xchina.co/photos/album-8/{i}.html" # baihu
        # url = f"https://xchina.co/photos/album-4/{i}.html" # luchu
        # url = f'https://xchina.co/photos/album-9/{i}.html' # nvtong
        url = f'https://xchina.co/photos/album-11/{i}.html' # video
        tasks.append(asyncio.create_task(main_source(url, semaphore=semaphore)))
    main_dir_name = './baihu_video'
    if not os.path.exists(main_dir_name):
        os.makedirs(main_dir_name)
    res = await asyncio.gather(*tasks)
    print(res)
    await get_download(res, main_dir_name)


async def get_download(res, main_dir_name):
    semaphore = asyncio.Semaphore(20)  # 限制并发请求的数量
    tasks = []
    for lis in res:
        if lis is not None:
            for tp in lis:
                task_video = asyncio.create_task(video_download(detail_src=tp[0], semaphore=semaphore, main_dir_name=main_dir_name, dir_name=tp[1]))
                tasks.append(task_video)
    await asyncio.gather(*tasks)


if __name__ == '__main__':
    asyncio.run(main())
