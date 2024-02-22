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

asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())  # 加上这一行解决ssl问题


async def download(session, src, dir_name, main_dir_name):
    if not os.path.exists(f'{main_dir_name}/{dir_name}'):
        os.makedirs(f'{main_dir_name}/{dir_name}')
    file_name = src.split('/')[-1]
    for j in range(5):
        try:
            async with session.get(src, headers=headers) as response:
                async with aiofiles.open(f'{main_dir_name}/{dir_name}/' + file_name, mode='wb') as fp:
                    while True:
                        chunk = await response.content.read()
                        if not chunk:
                            break
                        await fp.write(chunk)
            # print('下载完成', dir_name)
            break
        except Exception as e:
            print('download出错', e)
            continue


async def get_detail_page(session, detail_src):
    async with session.get(detail_src, headers=headers) as response:
        resp_text = await response.text()
        tree = etree.HTML(resp_text)
        pages = tree.xpath("//div[@class='pager'][1]/div/a")[-2].text
        return int(pages)


async def get_detail_one_src(detail_src, dir_name, page, semaphore, main_dir_name):   # 限制并发请求的数量):
    id = detail_src.split('/')[-1].split('.')[0]
    detail_url = f'https://xchina.co/photo/{id}/{page}.html'
    video_src = f'https://img.xchina.biz/photos2/{id}/0001.mp4'
    for j in range(5):
        try:
            conn = aiohttp.TCPConnector(ssl=False)  # 防止ssl报错
            async with aiohttp.ClientSession(connector=conn, trust_env=True) as session:
                async with semaphore:
                    resp_text = await fetch_with_retry(session, detail_url)
                    tree = etree.HTML(resp_text)
                    pic_target = tree.xpath('//div[@class="photos"]/a')
                    for pic in pic_target:
                        src = pic.xpath('./figure/img/@src')[0]  # 每张图片
                        await download(session, src, dir_name, main_dir_name)
                        print(dir_name + 'ok')
                    break
        except Exception as e:
            print(f'get_detail_src()出错\n{e}')


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
                        pages = await get_detail_page(session, detail_src)
                        resd.append((detail_src, pages, img_name))
                    except Exception as e:
                        print('首页函数出错', e)
                        continue
    return resd


async def main():
    semaphore = asyncio.Semaphore(5)  # 限制并发请求的数量
    tasks = []
    for i in range(1, 11):
        # url = f'https://xchina.co/photos/album-8/{i}.html' # cos
        url = f"https://xchina.co/photos/album-8/{i}.html" # baihu
        url = f"https://xchina.co/photos/album-4/{i}.html" # luchu
        url = f'https://xchina.co/photos/album-9/{i}.html' # nvtong
        # url = f'https://xchina.co/photos/album-11/{i}.html' # video

        tasks.append(asyncio.create_task(main_source(url, semaphore=semaphore)))
    main_dir_name = './nvtong'
    if not os.path.exists(main_dir_name):
        os.makedirs(main_dir_name)
    res = await asyncio.gather(*tasks)
    print(res)
    await get_download(res, main_dir_name)


async def get_download(res, main_dir_name):
    semaphore = asyncio.Semaphore(30)  # 限制并发请求的数量
    tasks = []
    for lis in res:
        if lis is not None:
            for tp in lis:
                for page in range(1, tp[1] + 1):
                    task = asyncio.create_task(get_detail_one_src(tp[0], dir_name=tp[2], page=page, semaphore=semaphore, main_dir_name=main_dir_name))
                    tasks.append(task)
    await asyncio.gather(*tasks)


if __name__ == '__main__':
    asyncio.run(main())
